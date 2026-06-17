"""Interfaccia comune dei provider di composizione (PRD §6.4, adattata alla Fase 2 PSD).

Un RenderProvider prende il master del prodotto + un template e restituisce il prodotto
finito renderizzato alle px esatte del formato. Implementazioni: LocalStub (non-AI, costo 0)
e AdobePhotoshopProvider (Photoshop API / Firefly, a crediti).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class TemplateSpec:
    """Dati del template necessari alla composizione (sottoinsieme di TemplateProfile)."""

    nome: str
    larghezza_px: int
    altezza_px: int
    formato_file: str = "jpg"
    qualita: int = 92
    psd_storage_path: Optional[str] = None
    smart_object_layer: str = ""
    text_layers: dict = field(default_factory=dict)
    preserve_mode: str = "sfondo_only"
    prompt_default: str = ""


@dataclass
class ComposeResult:
    image: bytes
    content_type: str
    cost: float = 0.0
    is_ai: bool = False
    engine: str = ""
    note: str = ""


@runtime_checkable
class RenderProvider(Protocol):
    name: str

    def estimate_cost(self, template: TemplateSpec) -> float:
        """Stima del costo (crediti/€) di una singola composizione."""
        ...

    def compose(
        self,
        master_bytes: bytes,
        template: TemplateSpec,
        prompt: Optional[str] = None,
    ) -> ComposeResult:
        """Compone il prodotto finito alle px esatte del template."""
        ...
