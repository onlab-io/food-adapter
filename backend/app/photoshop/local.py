"""Composizione NON-AI (costo zero) per la Fase 2 senza Adobe.

Estende lo sfondo esistente del master ai lati (o sopra/sotto) per riempire il formato,
continuando i bordi invece di sfocare. Per gli sfondi "studio" a toni piatti (piano + parete)
il risultato è vicino a quello dell'outpainting reale, mantenendo il soggetto intatto.
Per uno sfondo complesso serve comunque il motore AI (Adobe/alternativo).
"""
from __future__ import annotations

import io

from PIL import Image, ImageFilter

from ..imaging.export import CONTENT_TYPE, _encode
from .base import ComposeResult, TemplateSpec


def _estendi_orizzontale(canvas: Image.Image, strip: Image.Image, x0: int) -> None:
    """Riempie le bande sinistra/destra continuando le colonne di bordo dello strip."""
    sw, sh = strip.size
    canvas.paste(strip, (x0, 0))
    if x0 > 0:
        left = strip.crop((0, 0, 1, sh)).resize((x0, sh), Image.BILINEAR)
        canvas.paste(left, (0, 0))
    right_w = canvas.width - (x0 + sw)
    if right_w > 0:
        right = strip.crop((sw - 1, 0, sw, sh)).resize((right_w, sh), Image.BILINEAR)
        canvas.paste(right, (x0 + sw, 0))


def _estendi_verticale(canvas: Image.Image, strip: Image.Image, y0: int) -> None:
    """Riempie le bande sopra/sotto continuando le righe di bordo dello strip."""
    sw, sh = strip.size
    canvas.paste(strip, (0, y0))
    if y0 > 0:
        top = strip.crop((0, 0, sw, 1)).resize((sw, y0), Image.BILINEAR)
        canvas.paste(top, (0, 0))
    bot_h = canvas.height - (y0 + sh)
    if bot_h > 0:
        bot = strip.crop((0, sh - 1, sw, sh)).resize((sw, bot_h), Image.BILINEAR)
        canvas.paste(bot, (0, y0 + sh))


class LocalStubProvider:
    name = "local"

    def estimate_cost(self, template: TemplateSpec) -> float:
        return 0.0

    def compose(self, master_bytes: bytes, template: TemplateSpec, prompt=None) -> ComposeResult:
        master = Image.open(io.BytesIO(master_bytes))
        master.load()
        master = master.convert("RGB")
        mw, mh = master.size
        tw, th = template.larghezza_px, template.altezza_px
        ext = template.formato_file.lower()
        icc = master.info.get("icc_profile")
        ar_t, ar_m = tw / th, mw / mh

        canvas = Image.new("RGB", (tw, th))
        if ar_t >= ar_m:
            # Formato più largo del master: scala ad altezza piena, estendi a sinistra/destra.
            sh = th
            sw = max(1, round(mw * th / mh))
            strip = master.resize((sw, sh), Image.LANCZOS)
            _estendi_orizzontale(canvas, strip, (tw - sw) // 2)
        else:
            # Formato più alto: scala a larghezza piena, estendi sopra/sotto.
            sw = tw
            sh = max(1, round(mh * tw / mw))
            strip = master.resize((sw, sh), Image.LANCZOS)
            _estendi_verticale(canvas, strip, (th - sh) // 2)

        # Lieve smussatura solo per ammorbidire il raccordo (lo sfondo studio è quasi piatto).
        canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))

        data = _encode(canvas, ext if ext in CONTENT_TYPE else "jpg", template.qualita, (255, 255, 255), icc)
        return ComposeResult(
            image=data,
            content_type=CONTENT_TYPE.get(ext, "image/jpeg"),
            cost=0.0,
            is_ai=False,
            engine="local-stub",
            note="Estensione locale dello sfondo (non-AI): continua i bordi del master.",
        )
