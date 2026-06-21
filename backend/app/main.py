"""Food Image Multi-Format Adapter — backend FastAPI (Fase 1, core deterministico)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import (
    download,
    formats,
    jobs,
    media,
    outputs,
    settings as settings_router,
    templates,
    uploads,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all è idempotente: crea le tabelle se mancano (SQLite locale o Postgres Supabase).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Photo Adapter", version="1.0.0", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "fase": 1, "storage": "supabase" if _settings.storage_configured else "local"}


app.include_router(formats.router)
app.include_router(templates.router)
app.include_router(settings_router.router)
app.include_router(uploads.router)
app.include_router(jobs.router)
app.include_router(outputs.router)
app.include_router(media.router)
app.include_router(download.router)
