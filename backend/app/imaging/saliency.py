"""Mappa di saliency e ricerca della finestra di crop ottimale (PRD §3.2 entropy/saliency).

Equivalente concettuale dell'`attention` di sharp: si calcola una mappa di
salienza e si sceglie, lungo l'asse libero, la posizione della finestra di crop
che ne massimizza il contenuto informativo.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .routing import Box

try:  # opencv-contrib espone il modulo saliency
    import cv2

    _HAS_CV2 = hasattr(cv2, "saliency")
except Exception:  # pragma: no cover - ambiente senza opencv
    cv2 = None
    _HAS_CV2 = False


def mappa_saliency(img: Image.Image) -> np.ndarray:
    """Restituisce una mappa di salienza float32 in [0,1], stessa dimensione (h,w) dell'immagine.

    Usa OpenCV StaticSaliencyFineGrained se disponibile; in fallback usa il
    gradiente locale (Sobel) come proxy di "contenuto informativo".
    """
    rgb = img.convert("RGB")
    arr = np.asarray(rgb)
    if _HAS_CV2:
        try:
            algo = cv2.saliency.StaticSaliencyFineGrained_create()
            ok, sal = algo.computeSaliency(arr)
            if ok and sal is not None:
                sal = sal.astype(np.float32)
                m = float(sal.max())
                if m > 0:
                    sal = sal / m
                return sal
        except Exception:
            pass
    return _gradiente(arr)


def _gradiente(arr: np.ndarray) -> np.ndarray:
    """Proxy di salienza basato sul gradiente (usato se OpenCV non è disponibile)."""
    gray = arr.mean(axis=2).astype(np.float32)
    gy, gx = np.gradient(gray)
    mag = np.hypot(gx, gy)
    m = float(mag.max())
    if m > 0:
        mag = mag / m
    return mag


def finestra_ottimale(
    sal: np.ndarray,
    master_w: int,
    master_h: int,
    crop_w: int,
    crop_h: int,
) -> Box:
    """Trova la posizione della finestra (crop_w × crop_h) che massimizza la salienza contenuta.

    Si scorre solo l'asse libero (quello in cui la finestra è più piccola del master),
    usando l'immagine integrale per somme O(1).
    """
    crop_w = min(crop_w, master_w)
    crop_h = min(crop_h, master_h)

    free_x = master_w - crop_w
    free_y = master_h - crop_h

    # Immagine integrale (somma cumulativa con padding di zeri).
    integ = np.zeros((master_h + 1, master_w + 1), dtype=np.float64)
    integ[1:, 1:] = np.cumsum(np.cumsum(sal, axis=0), axis=1)

    def somma(x: int, y: int) -> float:
        x2, y2 = x + crop_w, y + crop_h
        return float(integ[y2, x2] - integ[y, x2] - integ[y2, x] + integ[y, x])

    if free_x <= 0 and free_y <= 0:
        return Box(0, 0, crop_w, crop_h)

    best_x, best_y, best_val = (master_w - crop_w) // 2, (master_h - crop_h) // 2, -1.0
    # Campionamento a passo adattivo per restare veloci su master grandi.
    if free_x >= free_y:
        step = max(1, free_x // 256)
        y = (master_h - crop_h) // 2
        for x in range(0, free_x + 1, step):
            v = somma(x, y)
            if v > best_val:
                best_val, best_x = v, x
    else:
        step = max(1, free_y // 256)
        x = (master_w - crop_w) // 2
        for y in range(0, free_y + 1, step):
            v = somma(x, y)
            if v > best_val:
                best_val, best_y = v, y

    return Box(best_x, best_y, crop_w, crop_h)
