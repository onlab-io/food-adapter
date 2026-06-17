-- Fase 2 — composizione su template PSD (Adobe Photoshop API).

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

alter table jobs add column if not exists template_ids jsonb not null default '[]'::jsonb;

alter table output_items add column if not exists kind varchar not null default 'crop';
alter table output_items add column if not exists template_profile_id varchar;
alter table output_items add column if not exists is_ai boolean not null default false;
alter table output_items add column if not exists engine_used varchar;
alter table output_items add column if not exists costo_effettivo double precision not null default 0;
alter table output_items add column if not exists prompt_usato text;
alter table output_items alter column format_profile_id drop not null;
