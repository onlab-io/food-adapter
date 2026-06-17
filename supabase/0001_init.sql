-- Food Image Multi-Format Adapter — schema iniziale (Fase 1).
-- Applicabile via Supabase MCP (apply_migration) o dashboard SQL editor.
-- Lo stesso schema viene creato anche da SQLAlchemy create_all all'avvio del backend;
-- questa migrazione serve per tracciabilità e per la visibilità nel dashboard Supabase.

create table if not exists format_profiles (
  id varchar primary key,
  nome varchar not null,
  larghezza_px integer not null,
  altezza_px integer not null,
  formato_file varchar not null default 'jpg',
  qualita integer not null default 85,
  strategia_crop varchar not null default 'saliency',
  punto_focale varchar not null default 'piatto',
  outpaint_mode varchar not null default 'off',
  outpaint_engine varchar not null default 'none',
  preserve_mode varchar not null default 'sfondo_only',
  prompt_default text not null default '',
  fallback_no_ai varchar not null default 'crop',
  suffisso_naming varchar not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists app_settings (
  id integer primary key,
  naming_pattern varchar not null default '{nome}{suffisso}.{ext}',
  zip_structure varchar not null default 'per_formato',
  tolleranza_crop double precision not null default 0.35,
  default_outpaint_engine varchar not null default 'none',
  max_file_mb integer not null default 40
);

create table if not exists source_images (
  id varchar primary key,
  original_filename varchar not null,
  width integer not null,
  height integer not null,
  storage_path varchar not null,
  created_at timestamptz not null default now()
);

create table if not exists jobs (
  id varchar primary key,
  stato varchar not null default 'created',
  source_image_ids jsonb not null default '[]'::jsonb,
  format_ids jsonb not null default '[]'::jsonb,
  cost_estimate double precision not null default 0,
  note text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists output_items (
  id varchar primary key,
  job_id varchar not null references jobs (id) on delete cascade,
  source_image_id varchar not null references source_images (id),
  format_profile_id varchar not null,
  strategia_applicata varchar not null default '',
  crop_box jsonb,
  needs_outpaint boolean not null default false,
  stato varchar not null default 'queued',
  storage_path varchar,
  error_msg text,
  created_at timestamptz not null default now()
);

create index if not exists idx_output_items_job on output_items (job_id);
create index if not exists idx_output_items_stato on output_items (job_id, stato);

-- NB: niente RLS in Fase 1. Il backend accede con la service key / connessione diretta;
-- il bucket di storage 'photo-adapter' deve essere PRIVATO (accesso solo server-side).
