"""Selezione del provider di composizione (PRD §6.4: provider intercambiabili)."""
from __future__ import annotations

from ..config import get_settings
from .base import RenderProvider
from .local import LocalStubProvider


def get_provider(name: str | None = None) -> RenderProvider:
    """Ritorna il provider richiesto; ripiega su 'local' se Adobe non è configurato."""
    s = get_settings()
    engine = (name or s.default_render_engine or "local").lower()
    if engine == "stability":
        if not s.stability_configured:
            return LocalStubProvider()  # nessuna chiave: stub a costo zero
        from .stability import StabilityProvider

        return StabilityProvider()
    if engine == "photoshop":
        if not s.adobe_configured:
            return LocalStubProvider()
        from .compose import AdobePhotoshopProvider

        return AdobePhotoshopProvider()
    return LocalStubProvider()
