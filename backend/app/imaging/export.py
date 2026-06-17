"""Esportazione output a px esatte (PRD RF-21).

Crop secondo box -> resize alle dimensioni esatte del formato -> encode con qualità.
Verifica finale obbligatoria: l'output deve avere ESATTAMENTE (target_w, target_h).
"""
from __future__ import annotations

import io

from PIL import Image

from .routing import Box

FORMATI_OUTPUT = {"jpg", "png", "webp"}
_PIL_FORMAT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}
CONTENT_TYPE = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def esporta(
    img: Image.Image,
    box: Box,
    target_w: int,
    target_h: int,
    formato: str,
    qualita: int = 92,
    fallback_letterbox: bool = False,
    bg_color: tuple[int, int, int] = (255, 255, 255),
    icc_profile: bytes | None = None,
) -> bytes:
    """Ritaglia, ridimensiona alle px esatte ed esegue l'encode preservando la qualità.

    fallback_letterbox: se True, invece di ritagliare l'immagine viene inserita
    intera dentro il canvas target con bande (usato come alternativa al crop
    forzato per i formati che richiederebbero outpainting in Fase 1).
    icc_profile: profilo colore del master, ri-incorporato nell'output per fedeltà cromatica.
    """
    formato = formato.lower()
    if formato not in FORMATI_OUTPUT:
        raise ValueError(f"Formato non supportato: {formato}")

    if fallback_letterbox:
        out = _letterbox(img, target_w, target_h, bg_color)
    else:
        cropped = img.crop((box.x, box.y, box.x + box.w, box.y + box.h))
        # LANCZOS con reducing_gap migliora il downscale; per l'upscale resta nitido quanto possibile.
        out = cropped.resize((target_w, target_h), Image.LANCZOS, reducing_gap=3.0)

    # Verifica finale px esatte (RF-21): correggi se per arrotondamenti non combacia.
    if out.size != (target_w, target_h):
        out = out.resize((target_w, target_h), Image.LANCZOS)

    return _encode(out, formato, qualita, bg_color, icc_profile)


def _letterbox(
    img: Image.Image, tw: int, th: int, bg: tuple[int, int, int]
) -> Image.Image:
    scale = min(tw / img.width, th / img.height)
    nw, nh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    resized = img.convert("RGB").resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (tw, th), bg)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def _encode(
    img: Image.Image,
    formato: str,
    qualita: int,
    bg: tuple[int, int, int],
    icc_profile: bytes | None = None,
) -> bytes:
    buf = io.BytesIO()
    extra = {}
    if icc_profile:
        extra["icc_profile"] = icc_profile
    if formato == "jpg":
        if img.mode != "RGB":
            base = Image.new("RGB", img.size, bg)
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                base.paste(rgba, mask=rgba.split()[-1])
                img = base
            else:
                img = img.convert("RGB")
        # subsampling=0 (4:4:4): nessun sottocampionamento del colore -> bordi cromatici netti,
        # importante sul food (colori saturi). keep_rgb evita la conversione a YCbCr a qualità alte.
        img.save(
            buf, _PIL_FORMAT[formato], quality=qualita, optimize=True, subsampling=0, **extra
        )
    elif formato == "webp":
        # method=6 = compressione più accurata; per qualità >=98 si passa a webp lossless.
        if qualita >= 98:
            img.save(buf, _PIL_FORMAT[formato], lossless=True, method=6, **extra)
        else:
            img.save(buf, _PIL_FORMAT[formato], quality=qualita, method=6, **extra)
    else:  # png (sempre lossless)
        if img.mode == "P":
            img = img.convert("RGBA")
        img.save(buf, _PIL_FORMAT[formato], optimize=True, **extra)
    return buf.getvalue()


def riconverti(data: bytes, fmt: str, qualita: int = 92) -> bytes:
    """Ri-codifica byte immagine in un altro formato (per la scelta del formato al download)."""
    fmt = fmt.lower()
    if fmt not in FORMATI_OUTPUT:
        raise ValueError(f"Formato non supportato: {fmt}")
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        icc = im.info.get("icc_profile")
        return _encode(im, fmt, qualita, (255, 255, 255), icc)


def verifica_dimensioni(data: bytes, target_w: int, target_h: int) -> bool:
    """Riapre i byte e conferma le dimensioni esatte (usato nei test/verifica)."""
    with Image.open(io.BytesIO(data)) as im:
        return im.size == (target_w, target_h)
