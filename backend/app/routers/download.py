"""Download singolo e zip del batch con naming/struttura/formato configurabili (PRD RF-20/21)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..db import get_db
from ..imaging.export import CONTENT_TYPE, FORMATI_OUTPUT, riconverti
from ..imaging.naming import nome_output
from ..imaging.packaging import VoceZip, costruisci_zip
from ..models import AppSetting, FormatProfile, Job, OutputItem, SourceImage, TemplateProfile
from ..storage import get_storage

router = APIRouter(tags=["download"], dependencies=[Depends(require_auth)])


def _settings(db: Session) -> AppSetting:
    s = db.get(AppSetting, 1)
    return s or AppSetting(id=1)


def _profilo(db: Session, item: OutputItem):
    if item.kind == "compose":
        return db.get(TemplateProfile, item.template_profile_id)
    return db.get(FormatProfile, item.format_profile_id)


def _nome_file(db: Session, item: OutputItem, st: AppSetting, ext: str) -> tuple[str, str, str]:
    """(nome_file, label_formato, nome_originale) — ext è il formato effettivo di output."""
    src = db.get(SourceImage, item.source_image_id)
    p = _profilo(db, item)
    nome = nome_output(
        st.naming_pattern,
        src.original_filename if src else "master",
        p.suffisso_naming if p else "",
        p.nome if p else "formato",
        p.larghezza_px if p else 0,
        p.altezza_px if p else 0,
        ext,
    )
    return nome, (p.nome if p else "formato"), (src.original_filename if src else "master")


def _ext_e_bytes(db: Session, item: OutputItem, data: bytes, fmt: Optional[str]) -> tuple[str, bytes]:
    """Determina l'estensione finale e i byte, ri-codificando se è richiesto un formato diverso."""
    p = _profilo(db, item)
    orig_ext = (p.formato_file if p else "jpg").lower()
    if not fmt or fmt.lower() not in FORMATI_OUTPUT or fmt.lower() == orig_ext:
        return orig_ext, data
    qual = getattr(p, "qualita", 92) or 92
    return fmt.lower(), riconverti(data, fmt.lower(), qual)


@router.get("/outputs/{oid}/download")
def scarica_singolo(oid: str, fmt: Optional[str] = None, db: Session = Depends(get_db)):
    item = db.get(OutputItem, oid)
    if not item or not item.storage_path:
        raise HTTPException(404, "Output non disponibile")
    st = _settings(db)
    data = get_storage().get(item.storage_path)
    ext, data = _ext_e_bytes(db, item, data, fmt)
    nome, _, _ = _nome_file(db, item, st, ext)
    return Response(
        content=data,
        media_type=CONTENT_TYPE.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/jobs/{job_id}/download.zip")
def scarica_zip(
    job_id: str, solo_approvati: bool = True, fmt: Optional[str] = None, db: Session = Depends(get_db)
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job non trovato")
    st = _settings(db)
    stati = ["approved"] if solo_approvati else ["approved", "done"]
    items = db.scalars(
        select(OutputItem).where(OutputItem.job_id == job_id, OutputItem.stato.in_(stati))
    ).all()
    if not items:
        raise HTTPException(
            409,
            "Nessun output da scaricare (approva almeno un output, "
            "oppure usa solo_approvati=false per includere tutti i completati).",
        )
    storage = get_storage()
    voci: list[VoceZip] = []
    for it in items:
        if not it.storage_path:
            continue
        ext, data = _ext_e_bytes(db, it, storage.get(it.storage_path), fmt)
        nome, label, originale = _nome_file(db, it, st, ext)
        voci.append(VoceZip(nome, label, originale, data))
    zip_bytes = costruisci_zip(voci, struttura=st.zip_structure)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="batch-{job_id[:8]}.zip"'},
    )
