"""Gate a password singola (PRD: autenticazione base, no RBAC).

Login: POST /auth/login con la password condivisa -> token firmato.
Le richieste protette portano `Authorization: Bearer <token>`.
Il token è un HMAC del valore atteso: non contiene dati, serve solo come prova di login.
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


def _token_atteso() -> str:
    s = get_settings()
    return hmac.new(s.session_secret.encode(), b"food-adapter-login", hashlib.sha256).hexdigest()


def login(password: str) -> str:
    s = get_settings()
    if not hmac.compare_digest(password, s.app_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password errata")
    return _token_atteso()


def require_auth(authorization: str = Header(default="")) -> None:
    """Dipendenza FastAPI: verifica il token di sessione."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token or not hmac.compare_digest(token, _token_atteso()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non autenticato",
            headers={"WWW-Authenticate": "Bearer"},
        )
