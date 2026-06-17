-- Catalogo formati iniziale (seed). Idempotente: non duplica se i nomi esistono già.
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
