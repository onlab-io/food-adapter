"""Smoke test del core imaging (Fase 1), isolato dal resto dell'app.

Prende un master reale e genera alcuni formati, verificando px esatte e box plausibili.
Uso: ./.venv/bin/python smoke_imaging.py <path_immagine_master>
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from app.imaging.crop import box_da_strategia
from app.imaging.export import esporta, verifica_dimensioni
from app.imaging.naming import nome_output
from app.imaging.packaging import VoceZip, costruisci_zip
from app.imaging.routing import calcola_piano

FORMATI = [
    # (label, w, h, strategia, formato, suffisso)
    ("Card prodotto", 600, 680, "saliency", "jpg", "_card"),
    ("Modale", 1080, 840, "saliency", "webp", "_modale"),
    ("Quadrato social", 1080, 1080, "center", "jpg", "_sq"),
    ("Ledwall hall", 2750, 650, "saliency", "jpg", "_ledwall"),
]


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python smoke_imaging.py <master.png>")
        return 2
    src = Path(sys.argv[1])
    img = Image.open(src)
    img.load()
    mw, mh = img.size
    print(f"Master: {src.name}  {mw}x{mh}  AR={mw/mh:.3f}\n")

    out_dir = Path("smoke_out")
    out_dir.mkdir(exist_ok=True)
    voci: list[VoceZip] = []
    ok_all = True

    for label, w, h, strat, fmt, suff in FORMATI:
        piano = calcola_piano(mw, mh, w, h, tolleranza=0.35)
        if piano.needs_outpaint:
            # Fase 1: fallback crop forzato sulla finestra max (centrata su saliency).
            box = box_da_strategia(img, w, h, "saliency")
            etich = f"{piano.strategia.value} -> fallback crop forzato"
        else:
            box = box_da_strategia(img, w, h, strat)
            etich = piano.strategia.value

        data = esporta(img, box, w, h, fmt, qualita=85)
        ok = verifica_dimensioni(data, w, h)
        ok_all = ok_all and ok

        fname = nome_output("{nome}{suffisso}.{ext}", src.name, suff, label, w, h, fmt)
        (out_dir / fname).write_bytes(data)
        voci.append(VoceZip(fname, label, src.name, data))

        print(
            f"  {label:16s} {w}x{h}  AR={w/h:.2f}  "
            f"scarto={piano.scarto*100:4.0f}%  {etich:35s} "
            f"box=({box.x},{box.y},{box.w},{box.h})  px_esatte={'OK' if ok else 'NO'}  -> {fname}"
        )

    zip_bytes = costruisci_zip(voci, struttura="per_formato")
    (out_dir / "batch.zip").write_bytes(zip_bytes)
    print(f"\nZip: {len(zip_bytes)} byte -> {out_dir/'batch.zip'}")
    print("\nRISULTATO:", "TUTTE le px esatte OK" if ok_all else "ATTENZIONE: px non esatte")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
