"""Client Adobe Firefly Services / Photoshop API: autenticazione IMS + chiamate async.

Le credenziali stanno solo server-side (NFR-5) e non vengono mai loggate.
NB: le forme esatte di alcune richieste (Photoshop document workflows) vanno confermate
con lo spike isolato (spike_photoshop.py) prima dell'uso in batch.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
SCOPES = "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis"

# Host API
FIREFLY_HOST = "https://firefly-api.adobe.io"
PHOTOSHOP_HOST = "https://image.adobe.io"  # Photoshop/Lightroom API host


@dataclass
class _Token:
    value: str
    expires_at: float


class AdobeClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._id = client_id
        self._secret = client_secret
        self._token: _Token | None = None

    # ---- Auth ----
    def token(self) -> str:
        now = time.time()
        if self._token and self._token.expires_at - 60 > now:
            return self._token.value
        r = httpx.post(
            IMS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._id,
                "client_secret": self._secret,
                "scope": SCOPES,
            },
            timeout=30,
        )
        r.raise_for_status()
        j = r.json()
        self._token = _Token(j["access_token"], now + int(j.get("expires_in", 86400)))
        return self._token.value

    def headers(self, content_type: str = "application/json") -> dict:
        h = {
            "Authorization": f"Bearer {self.token()}",
            "x-api-key": self._id,
        }
        if content_type:
            h["Content-Type"] = content_type
        return h

    # ---- Chiamate async generiche ----
    def submit(self, url: str, json_body: dict) -> dict:
        """POST async: ritorna il JSON con lo statusUrl del job (202)."""
        r = httpx.post(url, headers=self.headers(), json=json_body, timeout=60)
        r.raise_for_status()
        return r.json()

    def poll(self, status_url: str, interval: float = 2.0, timeout: float = 300.0) -> dict:
        """Polla lo statusUrl finché il job è concluso. Ritorna il JSON finale."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = httpx.get(status_url, headers=self.headers(content_type=""), timeout=30)
            r.raise_for_status()
            j = r.json()
            status = (j.get("status") or j.get("jobStatus") or "").lower()
            if status in ("succeeded", "done", "complete", "completed"):
                return j
            if status in ("failed", "error"):
                raise RuntimeError(f"Job Adobe fallito: {j}")
            time.sleep(interval)
        raise TimeoutError("Timeout in attesa del job Adobe")

    @staticmethod
    def status_url(submit_response: dict) -> str:
        """Estrae lo statusUrl dalla risposta di submit (forme note: _links.self.href, statusUrl)."""
        if "statusUrl" in submit_response:
            return submit_response["statusUrl"]
        links = submit_response.get("_links") or {}
        if "self" in links and "href" in links["self"]:
            return links["self"]["href"]
        # alcune risposte mettono il job sotto 'jobId' + endpoint dedicato: gestito dal chiamante
        raise KeyError(f"statusUrl non trovato nella risposta: {submit_response.keys()}")
