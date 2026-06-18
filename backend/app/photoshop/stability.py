"""Provider di outpainting AI via Stability AI (alternativa accessibile ad Adobe).

Estende lo sfondo del master per riempire il formato (il soggetto resta intatto:
l'outpaint aggiunge solo i bordi). Endpoint: /v2beta/stable-image/edit/outpaint.
Chiave self-service da platform.stability.ai, a consumo. NFR-5: chiave solo server-side.
"""
from __future__ import annotations

import io

import httpx
from PIL import Image

from ..config import get_settings
from ..imaging.export import CONTENT_TYPE, _encode
from .base import ComposeResult, TemplateSpec

ENDPOINT = "https://api.stability.ai/v2beta/stable-image/edit/outpaint"
MAX_SIDE = 2000  # estensione massima per lato consentita dall'API


class StabilityProvider:
    name = "stability"

    def estimate_cost(self, template: TemplateSpec) -> float:
        return get_settings().costo_per_operazione_ai

    def compose(self, master_bytes: bytes, template: TemplateSpec, prompt=None) -> ComposeResult:
        s = get_settings()
        if not s.stability_configured:
            raise RuntimeError("STABILITY_API_KEY non configurata.")
        tw, th = template.larghezza_px, template.altezza_px
        img = Image.open(io.BytesIO(master_bytes))
        img.load()
        img = img.convert("RGB")
        mw, mh = img.size
        ar_t, ar_m = tw / th, mw / mh

        # Porta il master alla dimensione "piena" sull'asse corto del target e calcola
        # quanto estendere sull'asse lungo per raggiungere l'aspect ratio richiesto.
        if ar_t >= ar_m:
            sh, sw = th, max(1, round(mw * th / mh))
            strip = img.resize((sw, sh), Image.LANCZOS)
            left = min(MAX_SIDE, max(0, (tw - sw) // 2))
            right = min(MAX_SIDE, max(0, tw - sw - left))
            up = down = 0
        else:
            sw, sh = tw, max(1, round(mh * tw / mw))
            strip = img.resize((sw, sh), Image.LANCZOS)
            up = min(MAX_SIDE, max(0, (th - sh) // 2))
            down = min(MAX_SIDE, max(0, th - sh - up))
            left = right = 0

        buf = io.BytesIO()
        strip.save(buf, "PNG")
        buf.seek(0)

        data = {"output_format": "png"}
        for k, v in (("left", left), ("right", right), ("up", up), ("down", down)):
            if v > 0:
                data[k] = str(v)
        p = (prompt or template.prompt_default or "").strip()
        if p:
            data["prompt"] = p

        r = httpx.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {s.stability_api_key}", "Accept": "image/*"},
            files={"image": ("master.png", buf, "image/png")},
            data=data,
            timeout=180,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Stability outpaint errore {r.status_code}: {r.text[:300]}")

        out = Image.open(io.BytesIO(r.content))
        out.load()
        out = out.convert("RGB")
        if out.size != (tw, th):  # rifinitura px esatte (RF-21)
            out = out.resize((tw, th), Image.LANCZOS)

        ext = template.formato_file.lower()
        enc = _encode(out, ext if ext in CONTENT_TYPE else "jpg", template.qualita, (255, 255, 255), None)
        return ComposeResult(
            image=enc,
            content_type=CONTENT_TYPE.get(ext, "image/jpeg"),
            cost=self.estimate_cost(template),
            is_ai=True,
            engine="stability",
            note="Outpaint AI (Stability): sfondo esteso, soggetto preservato.",
        )
