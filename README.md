# Food Image Multi-Format Adapter — Fase 1

Adattamento batch di scatti food a formati multipli configurabili.
**Fase 1 = core deterministico, senza alcun costo AI**: gestione formati, upload batch,
smart-crop (center / saliency / ancora manuale), anteprima del box di crop con override,
export a px esatte, download singolo e ZIP. Pubblicabile e utile così com'è.

L'outpainting AI (ledwall e formati panoramici), i provider Adobe/Magnific e la stima
costi sono previsti per la **Fase 2** e non sono inclusi qui. I formati che richiederebbero
outpainting vengono **segnalati** e gestiti con un fallback locale (crop forzato o letterbox).

---

## Architettura

```
food-adapter/
├── backend/     FastAPI + Pillow/OpenCV (imaging deterministico)
├── frontend/    React + TypeScript (Vite), UI in italiano
└── supabase/    SQL della migrazione iniziale
```

- **Imaging** (`backend/app/imaging/`): routing crop-vs-outpaint (§3.4), crop per strategia
  (center/saliency/manual_anchor), saliency via OpenCV, export a px esatte, naming, zip.
- **Storage**: astrazione con due backend intercambiabili — **Supabase Storage** (produzione)
  o **filesystem locale** (sviluppo). Le chiavi restano sempre server-side; il frontend riceve
  i byte tramite endpoint proxy del backend (NFR-5).
- **DB**: **Supabase Postgres** in produzione, **SQLite** locale come fallback per sviluppo/test.

---

## Avvio in locale (sviluppo, senza Supabase)

Funziona out-of-the-box con SQLite + storage su filesystem: nessuna credenziale necessaria.

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # i default vanno bene per lo sviluppo locale
uvicorn app.main:app --port 8000 --reload
```
Backend su http://localhost:8000 — DB in `backend/data/app.db`, immagini in `backend/data/storage/`.

> Python: testato su 3.9 (di sistema). Consigliato 3.11+.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE=http://localhost:8000
npm run dev
```
App su http://localhost:5173. Password di default: `cambiami` (impostata in `backend/.env`).

---

## Fase 2 — Composizione su template PSD (Adobe Photoshop API)

Oltre al crop deterministico, l'app compone il **prodotto finito** dai template PSD: sostituisce
lo smart object del prodotto, **genera lo sfondo mancante con AI** (Firefly, `sfondo_only` →
il piatto reale resta intatto) e renderizza il file finale con layout, alle px esatte.

- **Senza credenziali Adobe** il motore `local` produce uno **stub** (prodotto a fuoco su sfondo
  cover sfocato) per collaudare il flusso a costo zero.
- **Con Adobe** (motore `photoshop`) la composizione reale avviene via Photoshop API.

Credenziali (server-side, mai esposte): in `backend/.env`
```
ADOBE_CLIENT_ID=<da Adobe Developer Console>
ADOBE_CLIENT_SECRET=<...>
DEFAULT_RENDER_ENGINE=photoshop      # 'local' per lo stub
COSTO_PER_OPERAZIONE_AI=0.0          # stima costo per operazione (per la conferma costi)
```
Dove prenderle: **developer.adobe.com/console** → nuovo progetto → **Add API: Photoshop API + Firefly API**
→ **OAuth Server-to-Server** → copia Client ID e Client Secret (richiede entitlement Firefly Services).

Prima di usare il motore reale: esegui lo **spike isolato** (PRD §8) su una sola immagine:
```
cd backend && source .venv/bin/activate
python spike_photoshop.py ../../BOR_template_prodotti/BOR_ledwall.psd <master> 2750 650 <layer_smart_object>
```
Se gli endpoint/payload reali differiscono, aggiorna `app/photoshop/compose.py`.

Uso nell'app: **Impostazioni → Template PSD** (carica i .psd, mappa lo smart object); poi nel
**Batch** seleziona i template insieme ai formati. Il piano mostra operazioni AI e **costo stimato**
con conferma esplicita; la galleria marca gli output **"Generato con AI"** e offre **Rigenera con prompt**.

## Configurazione per la produzione (Supabase)

In `backend/.env`:
```
APP_PASSWORD=<password-condivisa-robusta>
SESSION_SECRET=<segreto-lungo-e-casuale>
CORS_ORIGINS=https://<dominio-frontend>
DATABASE_URL=postgresql+psycopg://postgres:<DB_PASSWORD>@db.<REF>.supabase.co:5432/postgres
SUPABASE_URL=https://<REF>.supabase.co
SUPABASE_SERVICE_KEY=<service_role key>     # MAI esporre al client
STORAGE_BUCKET=photo-adapter
```

Passi:
1. Crea (o usa) un progetto Supabase.
2. Applica `supabase/0001_init.sql` (dashboard SQL editor o Supabase MCP). In alternativa il
   backend crea le tabelle automaticamente all'avvio (`create_all`).
3. Crea un bucket di storage **privato** chiamato `photo-adapter`.
4. Imposta le variabili sopra e riavvia il backend. `GET /health` deve riportare `"storage":"supabase"`.

---

## Flusso d'uso

1. **Impostazioni → Formati**: crea i profili (dimensioni, formato file, strategia di crop,
   suffisso, comportamento di fallback). Import/export JSON per backup e condivisione.
2. **Elabora batch**: trascina gli scatti master, scegli i formati, calcola il **piano**
   (strategia per ogni coppia immagine×formato — 0 operazioni AI in Fase 1), avvia.
3. **Risultati**: galleria per immagine; per ogni output puoi **approvare**, **ritagliare a mano**
   (trascinando il box sul master) o **scartare**. Scarica il singolo file o lo **ZIP** del batch.

---

## Verifica / test

- Smoke test imaging isolato:
  ```bash
  cd backend && source .venv/bin/activate
  python smoke_imaging.py ../../_originali/food/<un_master>.png
  ```
  Genera alcuni formati in `backend/smoke_out/` e verifica le px esatte.
- Tutta la catena API (formati, upload, job, run, resilienza/retry, recrop, zip, px esatte) è
  stata validata end-to-end in locale.

---

## Note di prodotto (Fase 1)

- Nessuna rigenerazione del piatto reale: in Fase 1 non c'è AI, solo crop deterministico.
- I formati che richiederebbero outpainting sono evidenziati (tag *“AI in Fase 2”*) e gestiti
  con crop forzato o letterbox secondo la scelta del profilo.
- Tutti gli output rispettano le dimensioni esatte del formato (verifica finale prima dell'export).
- **File di lavoro effimeri**: i master caricati e gli output generati vengono cancellati a fine
  batch ("Nuovo batch" / "Esci"), con pulizia automatica dei batch abbandonati oltre 24h. Resta
  salvata solo la configurazione (formati, template, impostazioni).
