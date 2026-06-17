"""Naming convention configurabile per gli output (PRD RF-20)."""
from __future__ import annotations

import os
import re

# Placeholder supportati nel pattern di naming.
#   {nome}      -> nome file originale senza estensione
#   {suffisso}  -> suffisso_naming del profilo formato (es. _card)
#   {formato}   -> etichetta del formato (slug)
#   {larghezza} / {altezza} -> px del formato
#   {ext}       -> estensione di output (jpg/png/webp)
DEFAULT_PATTERN = "{nome}{suffisso}.{ext}"

_INVALID = re.compile(r'[\\/:*?"<>|]+')


def slug(s: str) -> str:
    s = _INVALID.sub("", s).strip().replace(" ", "-")
    return s or "file"


def nome_output(
    pattern: str,
    nome_originale: str,
    suffisso: str,
    formato_label: str,
    larghezza: int,
    altezza: int,
    ext: str,
) -> str:
    base = os.path.splitext(os.path.basename(nome_originale))[0]
    valori = {
        "nome": slug(base),
        "suffisso": suffisso or "",
        "formato": slug(formato_label),
        "larghezza": str(larghezza),
        "altezza": str(altezza),
        "ext": ext.lower().lstrip("."),
    }
    try:
        out = (pattern or DEFAULT_PATTERN).format(**valori)
    except (KeyError, IndexError, ValueError):
        out = DEFAULT_PATTERN.format(**valori)
    # Evita separatori di percorso accidentali nel nome file.
    out = out.replace("/", "-").replace("\\", "-")
    return out
