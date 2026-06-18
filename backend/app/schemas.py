"""Schemi Pydantic per input/output delle API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

FormatoFile = Literal["jpg", "png", "webp"]
StrategiaCrop = Literal["center", "entropy", "saliency", "manual_anchor"]
FallbackNoAi = Literal["crop", "letterbox"]


# ---------- Format profiles ----------
class FormatProfileBase(BaseModel):
    nome: str = Field(min_length=1)
    larghezza_px: int = Field(gt=0)
    altezza_px: int = Field(gt=0)
    formato_file: FormatoFile = "jpg"
    qualita: int = Field(default=92, ge=1, le=100)
    strategia_crop: StrategiaCrop = "saliency"
    punto_focale: str = "piatto"
    outpaint_mode: Literal["off", "auto", "force"] = "off"
    outpaint_engine: str = "none"
    preserve_mode: Literal["sfondo_only", "full_ai"] = "sfondo_only"
    prompt_default: str = ""
    fallback_no_ai: FallbackNoAi = "crop"
    suffisso_naming: str = ""


class FormatProfileCreate(FormatProfileBase):
    pass


class FormatProfileOut(FormatProfileBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Template profiles (Fase 2) ----------
class TemplateProfileBase(BaseModel):
    nome: str = Field(min_length=1)
    larghezza_px: int = Field(gt=0)
    altezza_px: int = Field(gt=0)
    formato_file: FormatoFile = "jpg"
    qualita: int = Field(default=92, ge=1, le=100)
    suffisso_naming: str = ""
    smart_object_layer: str = ""
    text_layers: dict = Field(default_factory=dict)
    preserve_mode: Literal["sfondo_only", "full_ai"] = "sfondo_only"
    prompt_default: str = ""
    engine: Literal["stability", "photoshop", "local"] = "stability"


class TemplateProfileCreate(TemplateProfileBase):
    pass


class TemplateProfileOut(TemplateProfileBase):
    id: str
    psd_storage_path: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Settings ----------
class SettingsOut(BaseModel):
    naming_pattern: str
    zip_structure: Literal["per_formato", "per_immagine", "flat"]
    tolleranza_crop: float
    default_outpaint_engine: str
    max_file_mb: int

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    naming_pattern: Optional[str] = None
    zip_structure: Optional[Literal["per_formato", "per_immagine", "flat"]] = None
    tolleranza_crop: Optional[float] = Field(default=None, ge=0.0, le=0.95)
    default_outpaint_engine: Optional[str] = None
    max_file_mb: Optional[int] = Field(default=None, ge=1, le=200)


# ---------- Source images ----------
class SourceImageOut(BaseModel):
    id: str
    original_filename: str
    width: int
    height: int
    storage_path: str

    class Config:
        from_attributes = True


# ---------- Jobs ----------
class JobCreate(BaseModel):
    source_image_ids: list[str] = Field(min_length=1)
    format_ids: list[str] = Field(default_factory=list)      # Fase 1 (crop)
    template_ids: list[str] = Field(default_factory=list)    # Fase 2 (compose su PSD)


class PianoVoce(BaseModel):
    source_image_id: str
    source_filename: str
    kind: str = "crop"                       # crop | compose
    format_profile_id: Optional[str] = None
    template_profile_id: Optional[str] = None
    format_label: str
    strategia: str
    scarto: float = 0.0
    needs_outpaint: bool = False
    upscaling: bool = False
    is_ai: bool = False
    costo: float = 0.0
    nota: str


class JobPiano(BaseModel):
    job_id: str
    voci: list[PianoVoce]
    operazioni_ai_previste: int = 0
    costo_stimato: float = 0.0


class OutputItemOut(BaseModel):
    id: str
    job_id: str
    source_image_id: str
    kind: str = "crop"
    format_profile_id: Optional[str] = None
    template_profile_id: Optional[str] = None
    strategia_applicata: str
    crop_box: Optional[dict] = None
    needs_outpaint: bool
    stato: str
    storage_path: Optional[str] = None
    error_msg: Optional[str] = None
    is_ai: bool = False
    engine_used: Optional[str] = None
    costo_effettivo: float = 0.0
    prompt_usato: Optional[str] = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    stato: str
    source_image_ids: list[str]
    format_ids: list[str]
    template_ids: list[str] = []
    cost_estimate: float
    outputs: list[OutputItemOut] = []

    class Config:
        from_attributes = True


# ---------- Recrop ----------
class RecropRequest(BaseModel):
    # box in pixel {x,y,w,h} OPPURE normalizzato {nx,ny,nw,nh in [0,1]}
    box: dict


# ---------- Auth ----------
class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
