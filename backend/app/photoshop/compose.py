"""Composizione del prodotto finito via Adobe Photoshop API (Firefly Services).

Workflow (PRD §6.5 adattato ai PSD):
  1. replace_smart_object: inserisce il master nel layer smart object del template PSD
  2. generative_fill_background (opzionale): estende/genera lo sfondo mancante (sfondo_only)
  3. rendition: renderizza il PSD risultante a JPG/PNG alle px esatte

ATTENZIONE: gli endpoint e i payload esatti vanno confermati con `spike_photoshop.py`
(PRD §8). Le costanti sono centralizzate qui per facilitarne la correzione post-spike.
"""
from __future__ import annotations

import httpx

from ..config import get_settings
from ..imaging.export import CONTENT_TYPE
from ..storage import SupabaseStorage, get_storage
from .base import ComposeResult, TemplateSpec
from .client import PHOTOSHOP_HOST, AdobeClient

# Endpoint Photoshop API (da confermare con lo spike).
EP_SMART_OBJECT = f"{PHOTOSHOP_HOST}/pie/psdService/smartObject"
EP_DOC_OPERATIONS = f"{PHOTOSHOP_HOST}/pie/psdService/documentOperations"
EP_RENDITION = f"{PHOTOSHOP_HOST}/pie/psdService/renditionCreate"

_RENDITION_TYPE = {"jpg": "image/jpeg", "png": "image/vnd.adobe.photoshop", "webp": "image/webp"}


class AdobePhotoshopProvider:
    name = "photoshop"

    def __init__(self) -> None:
        s = get_settings()
        if not s.adobe_configured:
            raise RuntimeError("Credenziali Adobe non configurate (ADOBE_CLIENT_ID/SECRET).")
        self.client = AdobeClient(s.adobe_client_id, s.adobe_client_secret)

    def estimate_cost(self, template: TemplateSpec) -> float:
        # 1 operazione generativa per composizione (raffinare dopo lo spike sui crediti reali).
        return get_settings().costo_per_operazione_ai

    def _storage(self) -> SupabaseStorage:
        st = get_storage()
        if not isinstance(st, SupabaseStorage):
            raise RuntimeError(
                "Il provider Photoshop richiede Supabase Storage (URL firmati). "
                "Configura SUPABASE_URL/SERVICE_KEY."
            )
        return st

    def compose(self, master_bytes: bytes, template: TemplateSpec, prompt=None) -> ComposeResult:
        if not template.psd_storage_path:
            raise ValueError("Template senza PSD caricato.")
        st = self._storage()
        ext = template.formato_file.lower()

        # Carica il master in storage e prepara URL firmati per Adobe.
        master_path = f"tmp/master-{abs(hash(master_bytes)) % (10**12)}.png"
        st.put(master_path, master_bytes, "image/png")
        psd_url = st.signed_read_url(template.psd_storage_path)
        master_url = st.signed_read_url(master_path)
        composed_psd_path = f"tmp/composed-{master_path.split('/')[-1]}.psd"
        composed_psd_put = st.signed_upload_url(composed_psd_path)

        # 1) Replace smart object -> PSD composto
        body_so = {
            "inputs": [{"href": psd_url, "storage": "external"}],
            "options": {
                "layers": [
                    {
                        "name": template.smart_object_layer,
                        "input": {"href": master_url, "storage": "external"},
                    }
                ]
            },
            "outputs": [{"href": composed_psd_put, "storage": "external", "type": "image/vnd.adobe.photoshop"}],
        }
        resp = self.client.submit(EP_SMART_OBJECT, body_so)
        self.client.poll(self.client.status_url(resp))

        used_ai = False
        source_psd_url = st.signed_read_url(composed_psd_path)

        # 2) Generative fill dello sfondo (sfondo_only) — opzionale, validato dallo spike.
        # Se il template ha già lo sfondo, questo step può essere disattivato.
        # (placeholder: lasciato al post-spike; per ora si procede al rendition del PSD composto)

        # 3) Rendition -> immagine finale alle px esatte
        out_img_path = f"tmp/render-{master_path.split('/')[-1]}.{ext}"
        out_put = st.signed_upload_url(out_img_path)
        body_rend = {
            "inputs": [{"href": source_psd_url, "storage": "external"}],
            "outputs": [
                {
                    "href": out_put,
                    "storage": "external",
                    "type": _RENDITION_TYPE.get(ext, "image/jpeg"),
                    "width": template.larghezza_px,
                    "height": template.altezza_px,
                    "quality": template.qualita,
                }
            ],
        }
        resp = self.client.submit(EP_RENDITION, body_rend)
        self.client.poll(self.client.status_url(resp))

        data = st.get(out_img_path)
        # pulizia file temporanei
        for p in (master_path, composed_psd_path, out_img_path):
            try:
                st.delete(p)
            except Exception:  # noqa: BLE001
                pass

        return ComposeResult(
            image=data,
            content_type=CONTENT_TYPE.get(ext, "image/jpeg"),
            cost=self.estimate_cost(template),
            is_ai=used_ai,
            engine="photoshop",
            note="Composizione via Adobe Photoshop API.",
        )


def download_url(url: str) -> bytes:
    r = httpx.get(url, timeout=120)
    r.raise_for_status()
    return r.content
