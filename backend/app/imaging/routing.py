"""Logica di routing crop vs outpainting (PRD §3.4).

In Fase 1 non esiste outpainting: quando servirebbe, l'output viene marcato
`needs_outpaint` e si applica un fallback locale (crop forzato o letterbox)
secondo la scelta del profilo. Nessuna chiamata AI.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Strategia(str, Enum):
    CROP_LEGGERO = "crop_leggero"
    CROP_AGGRESSIVO = "crop_aggressivo"
    NEEDS_OUTPAINT = "needs_outpaint"  # servirebbe outpainting (Fase 2)


# Soglia oltre la quale, pur restando sotto la tolleranza, il crop è "aggressivo".
SOGLIA_LEGGERO = 0.15


@dataclass(frozen=True)
class Box:
    """Box di crop in pixel, relativo all'immagine master (origine in alto a sinistra)."""

    x: int
    y: int
    w: int
    h: int

    def as_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @staticmethod
    def from_dict(d: dict) -> "Box":
        return Box(int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"]))


@dataclass
class PianoOutput:
    """Esito del routing per una coppia immagine × formato, mostrato prima dell'esecuzione (RF-13)."""

    strategia: Strategia
    scarto: float            # frazione di pixel del master scartati dal crop max [0..1]
    max_box: Box             # finestra massima di AR target contenuta nel master
    needs_outpaint: bool     # True se servirebbe estendere la scena (non disponibile in Fase 1)
    upscaling: bool          # True se il crop è più piccolo del formato target (perdita di qualità)
    nota: str

    def as_dict(self) -> dict:
        return {
            "strategia": self.strategia.value,
            "scarto": round(self.scarto, 4),
            "max_box": self.max_box.as_dict(),
            "needs_outpaint": self.needs_outpaint,
            "upscaling": self.upscaling,
            "nota": self.nota,
        }


def finestra_max(master_w: int, master_h: int, target_w: int, target_h: int) -> Box:
    """Restituisce la più grande finestra con aspect ratio del target contenuta nel master, centrata."""
    ar_t = target_w / target_h
    ar_m = master_w / master_h
    if ar_t >= ar_m:
        # target più "largo": limitato dalla larghezza del master
        cw = master_w
        ch = round(master_w / ar_t)
    else:
        # target più "alto": limitato dall'altezza del master
        ch = master_h
        cw = round(master_h * ar_t)
    cw = min(cw, master_w)
    ch = min(ch, master_h)
    x = (master_w - cw) // 2
    y = (master_h - ch) // 2
    return Box(x, y, cw, ch)


def calcola_piano(
    master_w: int,
    master_h: int,
    target_w: int,
    target_h: int,
    tolleranza: float = 0.35,
) -> PianoOutput:
    """Decide la strategia (PRD §3.4) per una coppia master/formato.

    tolleranza: frazione massima di immagine scartabile dal crop prima di considerare
    necessario l'outpainting (default 35%).
    """
    box = finestra_max(master_w, master_h, target_w, target_h)
    area_master = master_w * master_h
    area_box = box.w * box.h
    scarto = 1.0 - (area_box / area_master) if area_master else 0.0
    upscaling = box.w < target_w or box.h < target_h

    if scarto > tolleranza:
        return PianoOutput(
            strategia=Strategia.NEEDS_OUTPAINT,
            scarto=scarto,
            max_box=box,
            needs_outpaint=True,
            upscaling=upscaling,
            nota=(
                f"Il crop scarterebbe il {scarto*100:.0f}% dell'immagine "
                f"(oltre la tolleranza del {tolleranza*100:.0f}%): servirebbe outpainting "
                "(non disponibile in Fase 1)."
            ),
        )

    if scarto <= SOGLIA_LEGGERO:
        strategia = Strategia.CROP_LEGGERO
        nota = f"Ritaglio leggero: scartato il {scarto*100:.0f}% dell'immagine."
    else:
        strategia = Strategia.CROP_AGGRESSIVO
        nota = f"Ritaglio aggressivo: scartato il {scarto*100:.0f}% dell'immagine."

    if upscaling:
        nota += " Attenzione: il formato è più grande dell'area ritagliata, ci sarà upscaling."

    return PianoOutput(
        strategia=strategia,
        scarto=scarto,
        max_box=box,
        needs_outpaint=False,
        upscaling=upscaling,
        nota=nota,
    )
