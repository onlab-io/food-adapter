"""CRUD template PSD + upload del file PSD (Fase 2)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..config import get_settings
from ..db import get_db
from ..models import TemplateProfile
from ..schemas import TemplateProfileCreate, TemplateProfileOut
from ..storage import get_storage

router = APIRouter(prefix="/templates", tags=["templates"], dependencies=[Depends(require_auth)])


def _get(db: Session, tid: str) -> TemplateProfile:
    obj = db.get(TemplateProfile, tid)
    if not obj:
        raise HTTPException(404, "Template non trovato")
    return obj


@router.get("", response_model=list[TemplateProfileOut])
def lista(db: Session = Depends(get_db)):
    return db.scalars(select(TemplateProfile).order_by(TemplateProfile.created_at)).all()


@router.post("", response_model=TemplateProfileOut, status_code=201)
def crea(payload: TemplateProfileCreate, db: Session = Depends(get_db)):
    obj = TemplateProfile(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{tid}", response_model=TemplateProfileOut)
def dettaglio(tid: str, db: Session = Depends(get_db)):
    return _get(db, tid)


@router.put("/{tid}", response_model=TemplateProfileOut)
def aggiorna(tid: str, payload: TemplateProfileCreate, db: Session = Depends(get_db)):
    obj = _get(db, tid)
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{tid}", status_code=204)
def elimina(tid: str, db: Session = Depends(get_db)):
    obj = _get(db, tid)
    db.delete(obj)
    db.commit()


@router.post("/{tid}/psd", response_model=TemplateProfileOut)
def carica_psd(tid: str, file: UploadFile, db: Session = Depends(get_db)):
    obj = _get(db, tid)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".psd":
        raise HTTPException(415, "Carica un file .psd")
    data = file.file.read()
    max_bytes = get_settings().max_file_mb * 1024 * 1024 * 2  # i PSD sono pesanti: doppio limite
    if len(data) > max_bytes:
        raise HTTPException(413, "PSD troppo grande")
    path = f"templates/{obj.id}.psd"
    get_storage().put(path, data, "image/vnd.adobe.photoshop")
    obj.psd_storage_path = path
    db.commit()
    db.refresh(obj)
    return obj
