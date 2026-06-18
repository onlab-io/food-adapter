"""SPIKE isolato Stability AI outpaint (PRD §8) — test su UNA immagine con la chiave reale.

Prerequisito: STABILITY_API_KEY nel .env (o nell'ambiente).
Uso:
  ./.venv/bin/python spike_stability.py <master.(png|jpg)> [W] [H]
Esempio (ledwall):
  ./.venv/bin/python spike_stability.py ../../_originali/food/<master>.png 2750 650
Salva il risultato in spike_outpaint.jpg.
"""
from __future__ import annotations

import sys

from app.config import get_settings
from app.photoshop.base import TemplateSpec
from app.photoshop.stability import StabilityProvider


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 2750
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 650
    if not get_settings().stability_configured:
        print("ERRORE: STABILITY_API_KEY non configurata in .env")
        return 1
    spec = TemplateSpec(nome="spike", larghezza_px=w, altezza_px=h, formato_file="jpg", qualita=92)
    res = StabilityProvider().compose(open(path, "rb").read(), spec)
    open("spike_outpaint.jpg", "wb").write(res.image)
    print(f"OK — {w}x{h} generato, costo stimato €{res.cost} -> spike_outpaint.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
