"""Configurazione da variabili d'ambiente (.env). Le credenziali stanno SOLO qui, server-side (NFR-5)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_password: str = "cambiami"          # gate a password singola (PRD: auth base)
    session_secret: str = "dev-secret-cambiami"
    cors_origins: str = "http://localhost:5173"
    max_file_mb: int = 40

    # --- Database (Supabase Postgres) ---
    # Connection string (transaction pooler o diretta). Es:
    # postgresql+psycopg://postgres:<pwd>@db.<ref>.supabase.co:5432/postgres
    database_url: str = ""

    # --- Supabase Storage (REST) ---
    supabase_url: str = ""                   # es. https://<ref>.supabase.co
    supabase_service_key: str = ""           # service_role key (MAI esposta al client)
    storage_bucket: str = "photo-adapter"

    # --- Adobe Firefly Services / Photoshop API (Fase 2) ---
    adobe_client_id: str = ""                # OAuth Server-to-Server (server-side, mai loggato)
    adobe_client_secret: str = ""
    default_render_engine: str = "local"     # local (stub, costo 0) | photoshop (Adobe, a crediti)
    costo_per_operazione_ai: float = 0.0     # stima costo per operazione AI (crediti/€), configurabile

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def adobe_configured(self) -> bool:
        return bool(self.adobe_client_id and self.adobe_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
