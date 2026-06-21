"""Autenticazione DISABILITATA — accesso libero (gate a password rimosso).

`require_auth` è un no-op: resta come dipendenza dei router per non doverli
modificare, ma non effettua alcun controllo. Per ripristinare il gate, vedi
la cronologia git di questo file.
"""
from __future__ import annotations


def require_auth() -> None:
    """No-op: nessun controllo di autenticazione."""
    return None
