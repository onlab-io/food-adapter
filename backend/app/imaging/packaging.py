"""Costruzione dell'archivio zip del batch (PRD RF-20).

Struttura configurabile:
  - per_formato:  <etichetta_formato>/<nomefile>
  - per_immagine: <nome_originale>/<nomefile>
  - flat:         <nomefile>
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from .naming import slug


@dataclass
class VoceZip:
    nome_file: str        # nome file di output (già passato per naming.nome_output)
    formato_label: str    # etichetta del formato (per cartella per_formato)
    nome_originale: str    # nome master (per cartella per_immagine)
    dati: bytes


def costruisci_zip(voci: list[VoceZip], struttura: str = "per_formato") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        usati: dict[str, int] = {}
        for v in voci:
            if struttura == "per_immagine":
                base = slug(v.nome_originale.rsplit(".", 1)[0])
                path = f"{base}/{v.nome_file}"
            elif struttura == "flat":
                path = v.nome_file
            else:  # per_formato (default)
                path = f"{slug(v.formato_label)}/{v.nome_file}"
            path = _dedup(path, usati)
            zf.writestr(path, v.dati)
    return buf.getvalue()


def _dedup(path: str, usati: dict[str, int]) -> str:
    if path not in usati:
        usati[path] = 1
        return path
    usati[path] += 1
    n = usati[path]
    if "." in path:
        stem, ext = path.rsplit(".", 1)
        return f"{stem}-{n}.{ext}"
    return f"{path}-{n}"
