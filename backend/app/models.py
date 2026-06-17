"""Modello dati (PRD §7). Tabelle: format_profiles, app_settings, source_images, jobs, output_items."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class FormatProfile(Base):
    __tablename__ = "format_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    larghezza_px: Mapped[int] = mapped_column(Integer, nullable=False)
    altezza_px: Mapped[int] = mapped_column(Integer, nullable=False)
    formato_file: Mapped[str] = mapped_column(String, default="jpg")  # jpg|png|webp
    qualita: Mapped[int] = mapped_column(Integer, default=92)
    strategia_crop: Mapped[str] = mapped_column(String, default="saliency")
    punto_focale: Mapped[str] = mapped_column(String, default="piatto")
    # Campi outpainting: presenti nello schema, ma trattati come "off" in Fase 1.
    outpaint_mode: Mapped[str] = mapped_column(String, default="off")  # off|auto|force
    outpaint_engine: Mapped[str] = mapped_column(String, default="none")
    preserve_mode: Mapped[str] = mapped_column(String, default="sfondo_only")
    prompt_default: Mapped[str] = mapped_column(Text, default="")
    # Fallback Fase 1 quando servirebbe outpainting: 'crop' (forzato) o 'letterbox' (bande).
    fallback_no_ai: Mapped[str] = mapped_column(String, default="crop")
    suffisso_naming: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppSetting(Base):
    """Riga singola di impostazioni globali."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    naming_pattern: Mapped[str] = mapped_column(String, default="{nome}{suffisso}.{ext}")
    zip_structure: Mapped[str] = mapped_column(String, default="per_formato")  # per_formato|per_immagine|flat
    tolleranza_crop: Mapped[float] = mapped_column(Float, default=0.35)
    default_outpaint_engine: Mapped[str] = mapped_column(String, default="none")
    max_file_mb: Mapped[int] = mapped_column(Integer, default=40)


class SourceImage(Base):
    __tablename__ = "source_images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stato: Mapped[str] = mapped_column(String, default="created")  # created|running|done|error
    source_image_ids: Mapped[list] = mapped_column(JSON, default=list)
    format_ids: Mapped[list] = mapped_column(JSON, default=list)
    template_ids: Mapped[list] = mapped_column(JSON, default=list)  # Fase 2: template PSD selezionati
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    outputs: Mapped[list["OutputItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class OutputItem(Base):
    __tablename__ = "output_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    source_image_id: Mapped[str] = mapped_column(ForeignKey("source_images.id"))
    # Un output è "crop" (Fase 1, format_profile_id) oppure "compose" (Fase 2, template_profile_id).
    kind: Mapped[str] = mapped_column(String, default="crop")  # crop|compose
    format_profile_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    template_profile_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    strategia_applicata: Mapped[str] = mapped_column(String, default="")
    crop_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    needs_outpaint: Mapped[bool] = mapped_column(default=False)
    stato: Mapped[str] = mapped_column(String, default="queued")
    # queued|processing|done|error|approved|discarded
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Campi Fase 2 (composizione AI)
    is_ai: Mapped[bool] = mapped_column(default=False)            # output generato/esteso con AI (§12)
    engine_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    costo_effettivo: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_usato: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job] = relationship(back_populates="outputs")


class TemplateProfile(Base):
    """Template PSD per la composizione del prodotto finito (Fase 2)."""

    __tablename__ = "template_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    larghezza_px: Mapped[int] = mapped_column(Integer, nullable=False)
    altezza_px: Mapped[int] = mapped_column(Integer, nullable=False)
    formato_file: Mapped[str] = mapped_column(String, default="jpg")
    qualita: Mapped[int] = mapped_column(Integer, default=92)
    suffisso_naming: Mapped[str] = mapped_column(String, default="")
    psd_storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Layer mapping nel PSD
    smart_object_layer: Mapped[str] = mapped_column(String, default="")  # nome layer smart object prodotto
    text_layers: Mapped[dict] = mapped_column(JSON, default=dict)        # {nome_layer: valore}
    # Generazione sfondo
    preserve_mode: Mapped[str] = mapped_column(String, default="sfondo_only")  # sfondo_only|full_ai
    prompt_default: Mapped[str] = mapped_column(Text, default="")
    engine: Mapped[str] = mapped_column(String, default="photoshop")     # photoshop|local
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
