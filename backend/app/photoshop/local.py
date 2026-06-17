"""Stub di composizione NON-AI (costo zero) per collaudare il flusso Fase 2 senza Adobe.

Non elabora il PSD (impossibile senza Photoshop): produce un composito plausibile alle px
esatte del template — prodotto a fuoco in primo piano su uno sfondo "cover" sfocato ricavato
dallo stesso scatto (lo sfondo si estende coerentemente). Chiaramente etichettato come stub.
Quando si configura il provider 'photoshop', la composizione reale sui PSD avviene via Adobe.
"""
from __future__ import annotations

import io

from PIL import Image, ImageFilter

from ..imaging.export import CONTENT_TYPE, _encode
from .base import ComposeResult, TemplateSpec


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

        # Sfondo: scala "cover" del master, ritaglio centrale, sfocatura -> estende toni/colori.
        cover = max(tw / mw, th / mh)
        bw, bh = max(tw, round(mw * cover)), max(th, round(mh * cover))
        bg = master.resize((bw, bh), Image.LANCZOS)
        left, top = (bw - tw) // 2, (bh - th) // 2
        bg = bg.crop((left, top, left + tw, top + th))
        radius = max(8, round(max(tw, th) * 0.03))
        bg = bg.filter(ImageFilter.GaussianBlur(radius))

        # Primo piano: master "contain", a fuoco, centrato (prodotto interamente visibile).
        contain = min(tw / mw, th / mh)
        fw, fh = max(1, round(mw * contain)), max(1, round(mh * contain))
        fg = master.resize((fw, fh), Image.LANCZOS)
        canvas = bg.copy()
        canvas.paste(fg, ((tw - fw) // 2, (th - fh) // 2))

        data = _encode(canvas, ext if ext in CONTENT_TYPE else "jpg", template.qualita, (255, 255, 255), icc)
        return ComposeResult(
            image=data,
            content_type=CONTENT_TYPE.get(ext, "image/jpeg"),
            cost=0.0,
            is_ai=False,
            engine="local-stub",
            note="Composizione stub locale (non-AI): sfondo cover sfocato + prodotto a fuoco.",
        )
