"""Astrazione di storage per master e output.

Due backend intercambiabili:
  - SupabaseStorage: REST API di Supabase Storage via httpx (service key, solo server-side).
  - LocalStorage: filesystem locale (fallback per sviluppo/test quando Supabase non è configurato).

Le chiavi non vengono mai esposte al client: il frontend richiede i byte tramite
gli endpoint del backend, che fanno da proxy verso lo storage (NFR-5).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

import httpx

from .config import get_settings


class Storage(Protocol):
    def put(self, path: str, data: bytes, content_type: str) -> str: ...
    def get(self, path: str) -> bytes: ...
    def delete(self, path: str) -> None: ...


class LocalStorage:
    """Salva i file sotto data/storage/<path>. Usato quando Supabase non è configurato."""

    def __init__(self, root: str = "data/storage") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _full(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("Percorso non valido")
        return p

    def put(self, path: str, data: bytes, content_type: str) -> str:
        full = self._full(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return path

    def get(self, path: str) -> bytes:
        return self._full(path).read_bytes()

    def delete(self, path: str) -> None:
        full = self._full(path)
        if full.exists():
            full.unlink()


class SupabaseStorage:
    """Backend su Supabase Storage via REST. Bucket privato; accesso solo con service key."""

    def __init__(self, base_url: str, service_key: str, bucket: str) -> None:
        self.base = base_url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
        }

    def put(self, path: str, data: bytes, content_type: str) -> str:
        url = f"{self.base}/object/{self.bucket}/{path}"
        # upsert per consentire ri-export dello stesso output (recrop).
        headers = {**self.headers, "Content-Type": content_type, "x-upsert": "true"}
        r = httpx.post(url, content=data, headers=headers, timeout=60)
        r.raise_for_status()
        return path

    def get(self, path: str) -> bytes:
        url = f"{self.base}/object/{self.bucket}/{path}"
        r = httpx.get(url, headers=self.headers, timeout=60)
        r.raise_for_status()
        return r.content

    def delete(self, path: str) -> None:
        url = f"{self.base}/object/{self.bucket}/{path}"
        httpx.request("DELETE", url, headers=self.headers, timeout=30)

    # --- URL firmati (per I/O con servizi esterni es. Adobe; mai esposti al client finale) ---
    def signed_read_url(self, path: str, expires_in: int = 600) -> str:
        url = f"{self.base}/object/sign/{self.bucket}/{path}"
        r = httpx.post(url, headers=self.headers, json={"expiresIn": expires_in}, timeout=30)
        r.raise_for_status()
        signed = r.json()["signedURL"]
        return f"{self.base}{signed}" if signed.startswith("/") else signed

    def signed_upload_url(self, path: str) -> str:
        url = f"{self.base}/object/upload/sign/{self.bucket}/{path}"
        r = httpx.post(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        signed = r.json()["url"]
        return f"{self.base}{signed}" if signed.startswith("/") else signed


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_configured:
            _storage = SupabaseStorage(s.supabase_url, s.supabase_service_key, s.storage_bucket)
        else:
            _storage = LocalStorage()
    return _storage
