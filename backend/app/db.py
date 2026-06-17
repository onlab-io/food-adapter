"""Engine e sessione SQLAlchemy verso il Postgres di Supabase."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()


def _resolve_url() -> str:
    """Postgres di Supabase se configurato; altrimenti SQLite locale (sviluppo/test)."""
    if _settings.database_url:
        return _settings.database_url
    from pathlib import Path

    Path("data").mkdir(exist_ok=True)
    return "sqlite:///./data/app.db"


_url = _resolve_url()
# pool_pre_ping evita connessioni morte col pooler di Supabase.
_kwargs: dict = {"pool_pre_ping": True, "future": True}
if _url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
