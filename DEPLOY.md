# Deploy in produzione

Architettura: **Frontend → Netlify** · **Backend → Render** (Docker) · **DB + Storage → Supabase**.
(Render è sostituibile con Railway o Fly.io: stesso Dockerfile.)

```
Browser ──> Netlify (React statico) ──HTTPS──> Render (FastAPI) ──> Supabase (Postgres + Storage)
```

---

## 0) Prerequisiti

1. **Repo Git su GitHub** (Render e Netlify deployano da git). Dalla cartella `food-adapter/`:
   ```bash
   git init
   git add .
   git commit -m "Food Image Adapter"
   git branch -M main
   git remote add origin https://github.com/<tuo-utente>/food-adapter.git
   git push -u origin main
   ```
   > `.gitignore` esclude già `.venv`, `node_modules`, `.env`, `data/`.

2. **Segreti Supabase** (progetto già creato, ref `xhsyelmouobpyjmrhnyo`). Servono tre valori dal dashboard
   Supabase → Project Settings:
   - **Service role key**: *API → Project API keys → `service_role` (secret)*.
   - **Database password**: *Database → Reset database password* (copiala, è mostrata una volta).
   - **Connection string**: *Database → Connection string → URI* (o "Session pooler").
     Va riscritta col driver psycopg (sostituisci `<REF>` col ref del TUO progetto), così:
     ```
     postgresql+psycopg://postgres:<DB_PASSWORD>@db.<REF>.supabase.co:5432/postgres
     ```
     Se la rete dà problemi (IPv6), usa la stringa del **Session pooler** (porta 5432) sostituendo
     `postgresql://` con `postgresql+psycopg://`.

---

## 1) Backend su Render

1. Render → **New + → Blueprint** → seleziona il repo. Render legge `render.yaml` e crea il
   servizio `photo-adapter-api` dal `backend/Dockerfile`.
   *(In alternativa: New → Web Service → Docker → Root/Context `backend`.)*
2. Imposta le **Environment Variables** (quelle con `sync:false`):
   | Variabile | Valore |
   |---|---|
   | `APP_PASSWORD` | password condivisa per accedere all'app |
   | `CORS_ORIGINS` | (per ora) `*` — lo stringi al punto 3 con l'URL Netlify |
   | `DATABASE_URL` | la connection string psycopg del punto 0.2 |
   | `SUPABASE_URL` | `https://xhsyelmouobpyjmrhnyo.supabase.co` |
   | `SUPABASE_SERVICE_KEY` | la service_role key |
   | `STORAGE_BUCKET` | `photo-adapter` |
   | `DEFAULT_RENDER_ENGINE` | `local` (resta stub finché non c'è Adobe) |
   `SESSION_SECRET` viene generata da Render. Le `ADOBE_*` lasciale vuote per ora.
3. **Deploy**. A fine build verifica: `https://<servizio>.onrender.com/health` →
   `{"status":"ok","storage":"supabase"}`.

> Note Render: tieni **1 sola istanza** (i job in background sono in-process). Sul piano **free**
> il servizio va in spin-down dopo inattività (primo accesso lento); per i job AI lunghi (Fase 2)
> passa al piano **starter**.

---

## 2) Frontend su Netlify

1. Netlify → **Add new site → Import from Git** → seleziona il repo.
2. Impostazioni build:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist` (Netlify lo deduce da `netlify.toml`)
3. **Environment variables** → aggiungi:
   - `VITE_API_BASE` = `https://<servizio>.onrender.com` (l'URL del backend Render)
4. **Deploy**. Ottieni l'URL, es. `https://tuo-sito.netlify.app`.

> `VITE_API_BASE` è letta a *build time*: se cambi l'URL del backend, fai un nuovo deploy del frontend.

---

## 3) Collega i due (CORS)

Su Render aggiorna `CORS_ORIGINS` con l'URL esatto del frontend e redeploy:
```
CORS_ORIGINS=https://tuo-sito.netlify.app
```
(Per più domini: separali con virgola.)

---

## 4) Verifica finale

1. Apri il sito Netlify → login con `APP_PASSWORD`.
2. Impostazioni → crea un formato. Ricarica: deve persistere (→ Supabase OK).
3. Carica 1–2 scatti, calcola il piano, avvia, scarica lo ZIP.
4. Su Supabase: *Storage → photo-adapter* mostra `masters/` e `outputs/`; le tabelle si popolano.

---

## 5) Sicurezza (consigliato)

- Imposta una `APP_PASSWORD` robusta; le chiavi (service key, DB, Adobe) restano **solo** su Render.
- Abilita RLS sulle tabelle (il backend usa service role/connessione diretta → continua a funzionare):
  ```sql
  alter table public.format_profiles   enable row level security;
  alter table public.template_profiles enable row level security;
  alter table public.app_settings      enable row level security;
  alter table public.source_images     enable row level security;
  alter table public.jobs              enable row level security;
  alter table public.output_items      enable row level security;
  ```

---

## 6) Fase 2 (Adobe) — quando avrai l'entitlement

Aggiungi su Render `ADOBE_CLIENT_ID`, `ADOBE_CLIENT_SECRET`, e metti `DEFAULT_RENDER_ENGINE=photoshop`.
Prima esegui lo spike isolato (`backend/spike_photoshop.py`) per validare gli endpoint. Finché Adobe
non è configurato, i template usano lo **stub locale** automaticamente.
