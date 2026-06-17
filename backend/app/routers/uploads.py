"""Upload master singolo o batch (PRD RF-14). I file vanno nello storage server-side."""
from __future__ import annotations

import io
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..config import get_settings
from ..db import get_db
from ..models import SourceImage
from ..schemas import SourceImageOut
from ..storage import get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"], dependencies=[Depends(require_auth)])

ESTENSIONI_OK = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
CONTENT_TYPE = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff",
}


@router.post("", response_model=list[SourceImageOut])
def carica(files: list[UploadFile], db: Session = Depends(get_db)):
    settings = get_settings()
    storage = get_storage()
    max_bytes = settings.max_file_mb * 1024 * 1024
    risultati: list[SourceImage] = []

    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ESTENSIONI_OK:
            raise HTTPException(415, f"Formato non supportato: {f.filename} (ammessi: jpg, png, webp, tiff)")
        data = f.file.read()
        if len(data) > max_bytes:
            raise HTTPException(413, f"File troppo grande: {f.filename} (max {settings.max_file_mb} MB)")
        try:
            with Image.open(io.BytesIO(data)) as im:
                w, h = im.size
        except UnidentifiedImageError:
            raise HTTPException(422, f"Immagine non leggibile: {f.filename}")

        # Genera l'id ESPLICITAMENTE: il default SQLAlchemy si applica solo al flush,
        # quindi src.id sarebbe None qui e il path collasserebbe su "masters/None.png".
        sid = str(uuid.uuid4())
        path = f"masters/{sid}{ext}"
        storage.put(path, data, CONTENT_TYPE.get(ext, "application/octet-stream"))
        src = SourceImage(id=sid, original_filename=f.filename or "master", width=w, height=h, storage_path=path)
        db.add(src)
        risultati.append(src)

    db.commit()
    for r in risultati:
        db.refresh(r)
    return risultati
