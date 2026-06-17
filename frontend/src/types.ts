export type FormatoFile = "jpg" | "png" | "webp";
export type StrategiaCrop = "center" | "entropy" | "saliency" | "manual_anchor";
export type FallbackNoAi = "crop" | "letterbox";

export interface FormatProfile {
  id: string;
  nome: string;
  larghezza_px: number;
  altezza_px: number;
  formato_file: FormatoFile;
  qualita: number;
  strategia_crop: StrategiaCrop;
  punto_focale: string;
  outpaint_mode: "off" | "auto" | "force";
  outpaint_engine: string;
  preserve_mode: "sfondo_only" | "full_ai";
  prompt_default: string;
  fallback_no_ai: FallbackNoAi;
  suffisso_naming: string;
}

export type FormatProfileInput = Omit<FormatProfile, "id">;

export interface AppSettings {
  naming_pattern: string;
  zip_structure: "per_formato" | "per_immagine" | "flat";
  tolleranza_crop: number;
  default_outpaint_engine: string;
  max_file_mb: number;
}

export interface SourceImage {
  id: string;
  original_filename: string;
  width: number;
  height: number;
  storage_path: string;
}

export interface TemplateProfile {
  id: string;
  nome: string;
  larghezza_px: number;
  altezza_px: number;
  formato_file: FormatoFile;
  qualita: number;
  suffisso_naming: string;
  smart_object_layer: string;
  text_layers: Record<string, string>;
  preserve_mode: "sfondo_only" | "full_ai";
  prompt_default: string;
  engine: "photoshop" | "local";
  psd_storage_path: string | null;
}

export type TemplateProfileInput = Omit<TemplateProfile, "id" | "psd_storage_path">;

export interface PianoVoce {
  source_image_id: string;
  source_filename: string;
  kind: "crop" | "compose";
  format_profile_id: string | null;
  template_profile_id: string | null;
  format_label: string;
  strategia: string;
  scarto: number;
  needs_outpaint: boolean;
  upscaling: boolean;
  is_ai: boolean;
  costo: number;
  nota: string;
}

export interface JobPiano {
  job_id: string;
  voci: PianoVoce[];
  operazioni_ai_previste: number;
  costo_stimato: number;
}

export interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface OutputItem {
  id: string;
  job_id: string;
  source_image_id: string;
  kind: "crop" | "compose";
  format_profile_id: string | null;
  template_profile_id: string | null;
  strategia_applicata: string;
  crop_box: CropBox | null;
  needs_outpaint: boolean;
  stato: "queued" | "processing" | "done" | "error" | "approved" | "discarded";
  storage_path: string | null;
  error_msg: string | null;
  is_ai: boolean;
  engine_used: string | null;
  costo_effettivo: number;
  prompt_usato: string | null;
}

export interface Job {
  id: string;
  stato: string;
  source_image_ids: string[];
  format_ids: string[];
  template_ids: string[];
  cost_estimate: number;
  outputs: OutputItem[];
}
