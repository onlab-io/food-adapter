-- ============================================================================
-- Photo Adapter — setup completo Supabase (incolla tutto nel SQL Editor del tuo progetto).
-- Crea: tabelle (Fase 1 + Fase 2), bucket di storage privato 'photo-adapter', 5 formati.
-- Idempotente: si può rieseguire senza danni. (Le tabelle vengono comunque create anche
-- dal backend all'avvio; questo script serve ad averle pronte + bucket + formati.)
-- ============================================================================

-- ---------- Tabelle ----------
create table if not exists format_profiles (
  id varchar primary key,
  nome varchar not null,
  larghezza_px integer not null,
  altezza_px integer not null,
  formato_file varchar not null default 'jpg',
  qualita integer not null default 92,
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
  template_ids jsonb not null default '[]'::jsonb,
  cost_estimate double precision not null default 0,
  note text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists template_profiles (
  id varchar primary key,
  nome varchar not null,
  larghezza_px integer not null,
  altezza_px integer not null,
  formato_file varchar not null default 'jpg',
  qualita integer not null default 92,
  suffisso_naming varchar not null default '',
  psd_storage_path varchar,
  smart_object_layer varchar not null default '',
  text_layers jsonb not null default '{}'::jsonb,
  preserve_mode varchar not null default 'sfondo_only',
  prompt_default text not null default '',
  engine varchar not null default 'photoshop',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists output_items (
  id varchar primary key,
  job_id varchar not null references jobs (id) on delete cascade,
  source_image_id varchar not null references source_images (id),
  kind varchar not null default 'crop',
  format_profile_id varchar,
  template_profile_id varchar,
  strategia_applicata varchar not null default '',
  crop_box jsonb,
  needs_outpaint boolean not null default false,
  stato varchar not null default 'queued',
  storage_path varchar,
  error_msg text,
  is_ai boolean not null default false,
  engine_used varchar,
  costo_effettivo double precision not null default 0,
  prompt_usato text,
  created_at timestamptz not null default now()
);
create index if not exists idx_output_items_job on output_items (job_id);
create index if not exists idx_output_items_stato on output_items (job_id, stato);

-- ---------- Bucket di storage privato ----------
insert into storage.buckets (id, name, public)
values ('photo-adapter', 'photo-adapter', false)
on conflict (id) do nothing;

-- ---------- Catalogo formati iniziale ----------
insert into format_profiles (id, nome, larghezza_px, altezza_px, formato_file, qualita, strategia_crop, punto_focale, fallback_no_ai, suffisso_naming)
select gen_random_uuid(), v.nome, v.w, v.h, 'jpg', 92, 'saliency', v.focale, v.fallback, v.suffisso
from (values
  ('Card prodotto',   600,  680,  'piatto',    'crop', '_card'),
  ('Card beverage',   600,  800,  'bicchiere', 'crop', '_card_bev'),
  ('Modale',          1080, 840,  'piatto',    'crop', '_modale'),
  ('Ledwall hall',    2750, 650,  'piatto',    'crop', '_ledwall'),
  ('Quadrato social', 1080, 1080, 'piatto',    'crop', '_sq')
) as v(nome, w, h, focale, fallback, suffisso)
where not exists (select 1 from format_profiles fp where fp.nome = v.nome);
