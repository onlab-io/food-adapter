"""Impostazioni globali: naming, struttura zip, tolleranza crop (PRD §3.6 / RF-20)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..db import get_db
from ..models import AppSetting
from ..schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_auth)])


def _get_or_create(db: Session) -> AppSetting:
    obj = db.get(AppSetting, 1)
    if not obj:
        obj = AppSetting(id=1)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


@router.get("", response_model=SettingsOut)
def leggi(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=SettingsOut)
def aggiorna(payload: SettingsUpdate, db: Session = Depends(get_db)):
    obj = _get_or_create(db)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj
