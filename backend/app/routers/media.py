"""Serve i byte di master e output facendo da proxy verso lo storage (le chiavi restano server-side)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..db import get_db
from ..imaging.export import CONTENT_TYPE
from ..models import FormatProfile, OutputItem, SourceImage, TemplateProfile
from ..storage import get_storage

router = APIRouter(prefix="/media", tags=["media"], dependencies=[Depends(require_auth)])

_SRC_CT = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
           "webp": "image/webp", "tif": "image/tiff", "tiff": "image/tiff"}


@router.get("/source/{sid}")
def source(sid: str, db: Session = Depends(get_db)):
    src = db.get(SourceImage, sid)
    if not src:
        raise HTTPException(404, "Immagine non trovata")
    data = get_storage().get(src.storage_path)
    ext = src.storage_path.rsplit(".", 1)[-1].lower()
    return Response(content=data, media_type=_SRC_CT.get(ext, "application/octet-stream"))


@router.get("/output/{oid}")
def output(oid: str, db: Session = Depends(get_db)):
    item = db.get(OutputItem, oid)
    if not item or not item.storage_path:
        raise HTTPException(404, "Output non disponibile")
    if item.kind == "compose":
        tpl = db.get(TemplateProfile, item.template_profile_id)
        ff = tpl.formato_file if tpl else "jpg"
    else:
        fmt = db.get(FormatProfile, item.format_profile_id)
        ff = fmt.formato_file if fmt else "jpg"
    ct = CONTENT_TYPE.get(ff, "application/octet-stream")
    return Response(content=get_storage().get(item.storage_path), media_type=ct)
