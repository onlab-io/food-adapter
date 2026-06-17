"""Calcolo del box di crop secondo la strategia (PRD §3.2).

Strategie Fase 1: center, entropy/saliency, manual_anchor.
Il risultato è sempre un Box in pixel relativo al master, restituito al frontend
per l'overlay di anteprima (RF-7) PRIMA dell'esportazione.
"""
from __future__ import annotations

from PIL import Image

from .routing import Box, finestra_max
from .saliency import finestra_ottimale, mappa_saliency

STRATEGIE_VALIDE = {"center", "entropy", "saliency", "manual_anchor"}


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(v, hi))


def box_da_strategia(
    img: Image.Image,
    target_w: int,
    target_h: int,
    strategia: str,
    anchor: tuple[float, float] | None = None,
    sal_map=None,
) -> Box:
    """Calcola il box di crop per il formato target.

    - center: finestra massima centrata.
    - entropy/saliency: finestra massima posizionata sulla regione a maggior salienza.
      Se `sal_map` è fornita (mappa già calcolata per quel master), la riusa: utile per
      evitare di ricalcolare la salienza per ogni formato dello stesso master.
    - manual_anchor: finestra massima centrata sull'ancora normalizzata (x,y in [0,1]),
      clampata ai bordi. Se anchor è None, si comporta come center.
    """
    mw, mh = img.size
    base = finestra_max(mw, mh, target_w, target_h)
    cw, ch = base.w, base.h

    if strategia in ("entropy", "saliency"):
        sal = sal_map if sal_map is not None else mappa_saliency(img)
        return finestra_ottimale(sal, mw, mh, cw, ch)

    if strategia == "manual_anchor" and anchor is not None:
        ax = _clamp(round(anchor[0] * mw), 0, mw)
        ay = _clamp(round(anchor[1] * mh), 0, mh)
        x = _clamp(ax - cw // 2, 0, mw - cw)
        y = _clamp(ay - ch // 2, 0, mh - ch)
        return Box(x, y, cw, ch)

    # center (default)
    return base


def normalizza_box(img: Image.Image, box: dict) -> Box:
    """Converte un box di override dal frontend in pixel interi, clampato dentro il master.

    Accetta o coordinate normalizzate {nx,ny,nw,nh in [0,1]} o pixel {x,y,w,h}.
    """
    mw, mh = img.size
    if "nx" in box:
        x = round(box["nx"] * mw)
        y = round(box["ny"] * mh)
        w = round(box["nw"] * mw)
        h = round(box["nh"] * mh)
    else:
        x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    w = _clamp(w, 1, mw)
    h = _clamp(h, 1, mh)
    x = _clamp(x, 0, mw - w)
    y = _clamp(y, 0, mh - h)
    return Box(x, y, w, h)
