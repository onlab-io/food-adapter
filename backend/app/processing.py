"""Servizio di elaborazione di un singolo output (riusa il core imaging).

Usato sia dall'esecuzione del job sia dal recrop manuale. Deterministico: nessuna AI.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

from .imaging.crop import box_da_strategia, normalizza_box
from .imaging.export import CONTENT_TYPE, esporta
from .imaging.routing import Box, calcola_piano
from .models import FormatProfile, TemplateProfile
from .photoshop.base import ComposeResult, TemplateSpec
from .photoshop.registry import get_provider


@dataclass
class RisultatoOutput:
    data: bytes
    content_type: str
    box: Box
    strategia: str
    needs_outpaint: bool


def _carica(img_bytes: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(img_bytes))
    im.load()
    return im


def elabora(
    img_bytes: bytes,
    profilo: FormatProfile,
    tolleranza: float,
    box_override: dict | None = None,
    sal_map=None,
) -> RisultatoOutput:
    """Genera l'output per (immagine, profilo). Se box_override è dato, usa quel box (recrop).

    sal_map: mappa di salienza precalcolata per il master (riuso tra formati dello stesso master).
    """
    img = _carica(img_bytes)
    mw, mh = img.size
    tw, th = profilo.larghezza_px, profilo.altezza_px
    ext = profilo.formato_file
    icc = img.info.get("icc_profile")  # preserva il profilo colore del master
    piano = calcola_piano(mw, mh, tw, th, tolleranza)

    # Recrop manuale: il box deciso dall'utente vince sempre.
    if box_override is not None:
        box = normalizza_box(img, box_override)
        data = esporta(img, box, tw, th, ext, profilo.qualita, icc_profile=icc)
        return RisultatoOutput(data, CONTENT_TYPE[ext], box, "manual_anchor", piano.needs_outpaint)

    if piano.needs_outpaint:
        # Fase 1: nessuna AI. Fallback secondo il profilo.
        if profilo.fallback_no_ai == "letterbox":
            box = Box(0, 0, mw, mh)
            data = esporta(img, box, tw, th, ext, profilo.qualita, fallback_letterbox=True, icc_profile=icc)
            strategia = f"{piano.strategia.value}+letterbox"
        else:
            box = box_da_strategia(img, tw, th, "saliency", sal_map=sal_map)
            data = esporta(img, box, tw, th, ext, profilo.qualita, icc_profile=icc)
            strategia = f"{piano.strategia.value}+crop_forzato"
        return RisultatoOutput(data, CONTENT_TYPE[ext], box, strategia, True)

    # Crop normale secondo la strategia del profilo.
    box = box_da_strategia(img, tw, th, profilo.strategia_crop, sal_map=sal_map)
    data = esporta(img, box, tw, th, ext, profilo.qualita, icc_profile=icc)
    return RisultatoOutput(data, CONTENT_TYPE[ext], box, piano.strategia.value, False)


def componi(
    master_bytes: bytes, template: TemplateProfile, prompt: str | None = None
) -> ComposeResult:
    """Compone il prodotto finito su un template PSD via provider (Fase 2)."""
    spec = TemplateSpec(
        nome=template.nome,
        larghezza_px=template.larghezza_px,
        altezza_px=template.altezza_px,
        formato_file=template.formato_file,
        qualita=template.qualita,
        psd_storage_path=template.psd_storage_path,
        smart_object_layer=template.smart_object_layer,
        text_layers=template.text_layers or {},
        preserve_mode=template.preserve_mode,
        prompt_default=template.prompt_default,
    )
    provider = get_provider(template.engine)
    return provider.compose(master_bytes, spec, prompt or template.prompt_default or None)
