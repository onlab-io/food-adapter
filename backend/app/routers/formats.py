"""CRUD profili formato + import/export JSON (PRD RF-1/2/3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..db import get_db
from ..models import FormatProfile
from ..schemas import FormatProfileCreate, FormatProfileOut

router = APIRouter(prefix="/formats", tags=["formats"], dependencies=[Depends(require_auth)])


def _get_or_404(db: Session, fid: str) -> FormatProfile:
    obj = db.get(FormatProfile, fid)
    if not obj:
        raise HTTPException(404, "Profilo formato non trovato")
    return obj


@router.get("", response_model=list[FormatProfileOut])
def lista(db: Session = Depends(get_db)):
    return db.scalars(select(FormatProfile).order_by(FormatProfile.created_at)).all()


@router.post("", response_model=FormatProfileOut, status_code=201)
def crea(payload: FormatProfileCreate, db: Session = Depends(get_db)):
    obj = FormatProfile(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/export")
def esporta_json(db: Session = Depends(get_db)):
    """Esporta tutti i profili come JSON per backup/condivisione (RF-3)."""
    profili = db.scalars(select(FormatProfile)).all()
    return {"profili": [FormatProfileCreate.model_validate(p, from_attributes=True).model_dump() for p in profili]}


@router.post("/import", response_model=list[FormatProfileOut])
def importa_json(payload: dict, db: Session = Depends(get_db)):
    """Importa profili da JSON (lista sotto chiave 'profili'). Aggiunge, non sostituisce."""
    voci = payload.get("profili", [])
    creati: list[FormatProfile] = []
    for v in voci:
        try:
            dati = FormatProfileCreate.model_validate(v)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, f"Profilo non valido nell'import: {e}")
        obj = FormatProfile(**dati.model_dump())
        db.add(obj)
        creati.append(obj)
    db.commit()
    for c in creati:
        db.refresh(c)
    return creati


@router.get("/{fid}", response_model=FormatProfileOut)
def dettaglio(fid: str, db: Session = Depends(get_db)):
    return _get_or_404(db, fid)


@router.put("/{fid}", response_model=FormatProfileOut)
def aggiorna(fid: str, payload: FormatProfileCreate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, fid)
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{fid}/duplicate", response_model=FormatProfileOut, status_code=201)
def duplica(fid: str, db: Session = Depends(get_db)):
    src = _get_or_404(db, fid)
    dati = FormatProfileCreate.model_validate(src, from_attributes=True).model_dump()
    dati["nome"] = f"{src.nome} (copia)"
    obj = FormatProfile(**dati)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{fid}", status_code=204)
def elimina(fid: str, db: Session = Depends(get_db)):
    obj = _get_or_404(db, fid)
    db.delete(obj)
    db.commit()
