"""Output: anteprima box, recrop manuale, approva/scarta (PRD RF-7/18/19)."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from typing import Optional

from pydantic import BaseModel

from ..auth import require_auth
from ..db import get_db
from ..models import AppSetting, FormatProfile, OutputItem, SourceImage, TemplateProfile
from ..imaging.crop import box_da_strategia
from ..imaging.routing import calcola_piano
from ..processing import componi, elabora
from ..schemas import OutputItemOut, RecropRequest
from ..storage import get_storage


class RegenRequest(BaseModel):
    prompt: Optional[str] = None

router = APIRouter(prefix="/outputs", tags=["outputs"], dependencies=[Depends(require_auth)])


def _get(db: Session, oid: str) -> OutputItem:
    obj = db.get(OutputItem, oid)
    if not obj:
        raise HTTPException(404, "Output non trovato")
    return obj


def _tolleranza(db: Session) -> float:
    s = db.get(AppSetting, 1)
    return s.tolleranza_crop if s else 0.35


@router.post("/{oid}/regenerate", response_model=OutputItemOut)
def rigenera(oid: str, payload: RegenRequest, db: Session = Depends(get_db)):
    """Rigenera un output composito (template) con un eventuale prompt modificato (RF-19)."""
    item = _get(db, oid)
    if item.kind != "compose":
        raise HTTPException(400, "La rigenerazione con prompt è disponibile solo per gli output AI/template")
    src = db.get(SourceImage, item.source_image_id)
    tpl = db.get(TemplateProfile, item.template_profile_id)
    if not src or not tpl:
        raise HTTPException(404, "Sorgente o template mancante")
    storage = get_storage()
    res = componi(storage.get(src.storage_path), tpl, prompt=payload.prompt)
    out_path = item.storage_path or f"outputs/{item.job_id}/{item.id}.{tpl.formato_file}"
    storage.put(out_path, res.image, res.content_type)
    item.storage_path = out_path
    item.is_ai = res.is_ai
    item.engine_used = res.engine
    item.costo_effettivo = res.cost
    item.prompt_usato = payload.prompt or tpl.prompt_default or None
    item.stato = "done"
    item.error_msg = None
    db.commit()
    db.refresh(item)
    return item


@router.post("/{oid}/preview")
def preview(oid: str, db: Session = Depends(get_db)):
    """Ricalcola il box di crop senza esportare. Restituisce box + dimensioni master per l'overlay."""
    item = _get(db, oid)
    if item.kind == "compose":
        raise HTTPException(400, "Anteprima box non disponibile per i template (usa Rigenera)")
    src = db.get(SourceImage, item.source_image_id)
    fmt = db.get(FormatProfile, item.format_profile_id)
    if not src or not fmt:
        raise HTTPException(404, "Sorgente o formato mancante")
    storage = get_storage()
    with Image.open(io.BytesIO(storage.get(src.storage_path))) as img:
        img.load()
        piano = calcola_piano(src.width, src.height, fmt.larghezza_px, fmt.altezza_px, _tolleranza(db))
        strat = "saliency" if piano.needs_outpaint else fmt.strategia_crop
        box = box_da_strategia(img, fmt.larghezza_px, fmt.altezza_px, strat)
    return {
        "box": box.as_dict(),
        "strategia": piano.strategia.value,
        "needs_outpaint": piano.needs_outpaint,
        "master_width": src.width,
        "master_height": src.height,
        "nota": piano.nota,
    }


@router.post("/{oid}/recrop", response_model=OutputItemOut)
def recrop(oid: str, payload: RecropRequest, db: Session = Depends(get_db)):
    """Override manuale del box: ri-esporta l'output con il box scelto dall'utente (RF-7)."""
    item = _get(db, oid)
    if item.kind == "compose":
        raise HTTPException(400, "Il ritaglio manuale non si applica ai template (usa Rigenera)")
    src = db.get(SourceImage, item.source_image_id)
    fmt = db.get(FormatProfile, item.format_profile_id)
    if not src or not fmt:
        raise HTTPException(404, "Sorgente o formato mancante")
    storage = get_storage()
    img_bytes = storage.get(src.storage_path)
    res = elabora(img_bytes, fmt, _tolleranza(db), box_override=payload.box)
    out_path = item.storage_path or f"outputs/{item.job_id}/{item.id}.{fmt.formato_file}"
    storage.put(out_path, res.data, res.content_type)
    item.storage_path = out_path
    item.crop_box = res.box.as_dict()
    item.strategia_applicata = res.strategia
    item.stato = "done"
    item.error_msg = None
    db.commit()
    db.refresh(item)
    return item


@router.post("/{oid}/approve", response_model=OutputItemOut)
def approva(oid: str, db: Session = Depends(get_db)):
    item = _get(db, oid)
    if item.stato not in ("done", "approved"):
        raise HTTPException(409, "Si possono approvare solo output completati")
    item.stato = "approved"
    db.commit()
    db.refresh(item)
    return item


@router.post("/{oid}/discard", response_model=OutputItemOut)
def scarta(oid: str, db: Session = Depends(get_db)):
    item = _get(db, oid)
    item.stato = "discarded"
    db.commit()
    db.refresh(item)
    return item
