"""Job: creazione + piano di esecuzione, run asincrono, stato, retry falliti (PRD §3.5)."""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import AppSetting, FormatProfile, Job, OutputItem, SourceImage, TemplateProfile
from ..imaging.routing import calcola_piano
from ..imaging.saliency import mappa_saliency
from ..processing import componi, elabora
from ..photoshop.registry import get_provider
from ..photoshop.base import TemplateSpec
from ..schemas import JobCreate, JobOut, JobPiano, PianoVoce
from ..storage import get_storage

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])


def _tolleranza(db: Session) -> float:
    s = db.get(AppSetting, 1)
    return s.tolleranza_crop if s else 0.35


def _template_costa_ai(template: TemplateProfile) -> tuple[bool, float]:
    """Ritorna (is_ai, costo_stimato) per un template, in base al motore effettivo."""
    s = get_settings()
    usa_ai = (
        (template.engine == "stability" and s.stability_configured)
        or (template.engine == "photoshop" and s.adobe_configured)
    )
    if usa_ai:
        try:
            return True, get_provider(template.engine).estimate_cost(
                TemplateSpec(template.nome, template.larghezza_px, template.altezza_px)
            )
        except Exception:  # noqa: BLE001
            return True, s.costo_per_operazione_ai
    return False, 0.0  # stub locale: nessun costo AI


def _elimina_job_completo(db: Session, job: Job, storage) -> None:
    """Cancella un job, i suoi output, le immagini master e i relativi file di storage.

    La configurazione (formati/template/impostazioni) non viene toccata.
    """
    for it in list(job.outputs):
        if it.storage_path:
            try:
                storage.delete(it.storage_path)
            except Exception:  # noqa: BLE001
                pass
    srcs = db.scalars(
        select(SourceImage).where(SourceImage.id.in_(job.source_image_ids or []))
    ).all()
    for s in srcs:
        if s.storage_path:
            try:
                storage.delete(s.storage_path)
            except Exception:  # noqa: BLE001
                pass
        db.delete(s)
    db.delete(job)  # cascade -> output_items
    db.commit()


def _pulizia_vecchi(db: Session, storage, ore: int = 24) -> None:
    """Sweep: rimuove i batch (e i loro file) più vecchi di `ore`. Best-effort."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ore)
    vecchi = db.scalars(select(Job).where(Job.created_at < cutoff)).all()
    for j in vecchi:
        try:
            _elimina_job_completo(db, j, storage)
        except Exception:  # noqa: BLE001
            db.rollback()


@router.delete("/{job_id}", status_code=204)
def elimina_job(job_id: str, db: Session = Depends(get_db)):
    """Elimina un batch e tutti i suoi file (master + output). Usato a 'Nuovo batch'/'Esci'."""
    job = db.get(Job, job_id)
    if job:
        _elimina_job_completo(db, job, get_storage())


@router.post("", response_model=JobPiano, status_code=201)
def crea_job(payload: JobCreate, db: Session = Depends(get_db)):
    """Crea il job e calcola il PIANO per ogni coppia immagine×(formato o template) — RF-13.

    Conta le operazioni AI reali e il costo stimato (NFR-4): conferma esplicita lato UI prima del run.
    """
    # Sweep dei batch abbandonati (>24h) ad ogni nuovo job — "pulizia giornaliera" senza scheduler.
    try:
        _pulizia_vecchi(db, get_storage())
    except Exception:  # noqa: BLE001
        db.rollback()

    sources = db.scalars(select(SourceImage).where(SourceImage.id.in_(payload.source_image_ids))).all()
    formats = db.scalars(select(FormatProfile).where(FormatProfile.id.in_(payload.format_ids))).all()
    templates = db.scalars(
        select(TemplateProfile).where(TemplateProfile.id.in_(payload.template_ids))
    ).all()
    if not sources:
        raise HTTPException(422, "Nessuna immagine sorgente valida")
    if not formats and not templates:
        raise HTTPException(422, "Seleziona almeno un formato o un template")

    tol = _tolleranza(db)
    job = Job(
        source_image_ids=payload.source_image_ids,
        format_ids=payload.format_ids,
        template_ids=payload.template_ids,
    )
    db.add(job)
    db.flush()  # serve job.id

    voci: list[PianoVoce] = []
    n_ai = 0
    costo_totale = 0.0
    for src in sources:
        # --- Formati Fase 1 (crop deterministico) ---
        for fmt in formats:
            piano = calcola_piano(src.width, src.height, fmt.larghezza_px, fmt.altezza_px, tol)
            db.add(OutputItem(
                job_id=job.id, source_image_id=src.id, kind="crop",
                format_profile_id=fmt.id, strategia_applicata=piano.strategia.value,
                needs_outpaint=piano.needs_outpaint, stato="queued",
            ))
            voci.append(PianoVoce(
                source_image_id=src.id, source_filename=src.original_filename, kind="crop",
                format_profile_id=fmt.id, format_label=fmt.nome,
                strategia=piano.strategia.value, scarto=round(piano.scarto, 4),
                needs_outpaint=piano.needs_outpaint, upscaling=piano.upscaling, nota=piano.nota,
            ))
        # --- Template Fase 2 (composizione su PSD) ---
        for tpl in templates:
            is_ai, costo = _template_costa_ai(tpl)
            if is_ai:
                n_ai += 1
                costo_totale += costo
            db.add(OutputItem(
                job_id=job.id, source_image_id=src.id, kind="compose",
                template_profile_id=tpl.id, strategia_applicata="compose", stato="queued",
            ))
            voci.append(PianoVoce(
                source_image_id=src.id, source_filename=src.original_filename, kind="compose",
                template_profile_id=tpl.id, format_label=tpl.nome,
                strategia="compose", is_ai=is_ai, costo=costo,
                nota=("Composizione AI sul template PSD (sfondo generato)." if is_ai
                      else "Composizione stub locale (nessun costo AI)."),
            ))
    job.cost_estimate = costo_totale
    db.commit()
    return JobPiano(job_id=job.id, voci=voci, operazioni_ai_previste=n_ai, costo_stimato=round(costo_totale, 4))


@router.post("/{job_id}/run", response_model=JobOut)
def avvia(job_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job non trovato")
    job.stato = "running"
    db.commit()
    background.add_task(_esegui_job, job_id)
    db.refresh(job)
    return job


@router.post("/{job_id}/retry-failed", response_model=JobOut)
def riprova_falliti(job_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job non trovato")
    falliti = db.scalars(
        select(OutputItem).where(OutputItem.job_id == job_id, OutputItem.stato == "error")
    ).all()
    for it in falliti:
        it.stato = "queued"
        it.error_msg = None
    job.stato = "running"
    db.commit()
    background.add_task(_esegui_job, job_id)
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
def lista(db: Session = Depends(get_db)):
    return db.scalars(select(Job).order_by(Job.created_at.desc())).all()


@router.get("/{job_id}", response_model=JobOut)
def stato(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job non trovato")
    return job


def _esegui_job(job_id: str) -> None:
    """Esecuzione in background. Sessione DB propria. Resilienza per-item (NFR-3)."""
    db = SessionLocal()
    storage = get_storage()
    try:
        tol = _tolleranza(db)
        items = db.scalars(
            select(OutputItem).where(OutputItem.job_id == job_id, OutputItem.stato == "queued")
        ).all()
        src_cache: dict[str, bytes] = {}
        sal_cache: dict[str, object] = {}  # mappa salienza per master (riuso tra formati)

        for item in items:
            item.stato = "processing"
            db.commit()
            try:
                src = db.get(SourceImage, item.source_image_id)
                if not src:
                    raise ValueError("Immagine sorgente mancante")
                if src.id not in src_cache:
                    src_cache[src.id] = storage.get(src.storage_path)

                if item.kind == "compose":
                    # --- Fase 2: composizione su template PSD ---
                    tpl = db.get(TemplateProfile, item.template_profile_id)
                    if not tpl:
                        raise ValueError("Template mancante")
                    res = componi(src_cache[src.id], tpl)
                    out_path = f"outputs/{job_id}/{item.id}.{tpl.formato_file}"
                    storage.put(out_path, res.image, res.content_type)
                    item.storage_path = out_path
                    item.strategia_applicata = res.engine
                    item.is_ai = res.is_ai
                    item.engine_used = res.engine
                    item.costo_effettivo = res.cost
                    item.prompt_usato = tpl.prompt_default or None
                    item.stato = "done"
                    item.error_msg = None
                else:
                    # --- Fase 1: crop deterministico ---
                    fmt = db.get(FormatProfile, item.format_profile_id)
                    if not fmt:
                        raise ValueError("Formato mancante")
                    if src.id not in sal_cache:
                        with Image.open(io.BytesIO(src_cache[src.id])) as _im:
                            _im.load()
                            sal_cache[src.id] = mappa_saliency(_im)
                    res = elabora(src_cache[src.id], fmt, tol, sal_map=sal_cache[src.id])
                    out_path = f"outputs/{job_id}/{item.id}.{fmt.formato_file}"
                    storage.put(out_path, res.data, res.content_type)
                    item.storage_path = out_path
                    item.crop_box = res.box.as_dict()
                    item.strategia_applicata = res.strategia
                    item.needs_outpaint = res.needs_outpaint
                    item.stato = "done"
                    item.error_msg = None
            except Exception as e:  # noqa: BLE001 — un errore non blocca il batch
                item.stato = "error"
                item.error_msg = str(e)[:500]
            db.commit()

        job = db.get(Job, job_id)
        if job:
            n_err = db.scalar(
                select(func.count()).select_from(OutputItem).where(
                    OutputItem.job_id == job_id, OutputItem.stato == "error"
                )
            )
            job.stato = "error" if n_err else "done"
            db.commit()
    finally:
        db.close()
