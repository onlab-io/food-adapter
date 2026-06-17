"""SPIKE ISOLATO Adobe Photoshop API (PRD §8) — da eseguire con le credenziali reali.

Verifica su UNA sola immagine la sequenza: token IMS -> (storage URL firmati) ->
replace smart object sul template PSD -> [generative fill sfondo] -> rendition -> download.
Stampa le risposte per confermare endpoint/payload prima di cablare nel batch.

Prerequisiti (.env):
  ADOBE_CLIENT_ID, ADOBE_CLIENT_SECRET
  SUPABASE_URL, SUPABASE_SERVICE_KEY, STORAGE_BUCKET  (servono gli URL firmati)

Uso:
  ./.venv/bin/python spike_photoshop.py <template.psd> <master.(png|jpg)> <W> <H> <smart_object_layer>
Esempio:
  ./.venv/bin/python spike_photoshop.py \
      "../../BOR_template_prodotti/BOR_ledwall.psd" \
      "../../_originali/food/<master>.png" 2750 650 "PRODOTTO"
"""
from __future__ import annotations

import sys

from app.config import get_settings
from app.photoshop.client import AdobeClient
from app.storage import SupabaseStorage, get_storage


def main() -> int:
    if len(sys.argv) < 6:
        print(__doc__)
        return 2
    psd_path, master_path, w, h, so_layer = (
        sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    )
    s = get_settings()
    if not s.adobe_configured:
        print("ERRORE: ADOBE_CLIENT_ID/SECRET non configurati in .env")
        return 1
    st = get_storage()
    if not isinstance(st, SupabaseStorage):
        print("ERRORE: serve Supabase Storage (URL firmati). Configura SUPABASE_URL/SERVICE_KEY.")
        return 1

    client = AdobeClient(s.adobe_client_id, s.adobe_client_secret)
    print("1) Token IMS…")
    tok = client.token()
    print("   OK, token len", len(tok))

    print("2) Upload PSD + master su storage e URL firmati…")
    psd_key = "spike/template.psd"
    master_key = "spike/master.png"
    st.put(psd_key, open(psd_path, "rb").read(), "image/vnd.adobe.photoshop")
    st.put(master_key, open(master_path, "rb").read(), "image/png")
    psd_url = st.signed_read_url(psd_key)
    master_url = st.signed_read_url(master_key)
    composed_put = st.signed_upload_url("spike/composed.psd")
    out_put = st.signed_upload_url("spike/render.jpg")
    print("   URL firmati pronti.")

    from app.photoshop.compose import EP_RENDITION, EP_SMART_OBJECT

    print("3) Replace smart object…")
    body_so = {
        "inputs": [{"href": psd_url, "storage": "external"}],
        "options": {"layers": [{"name": so_layer, "input": {"href": master_url, "storage": "external"}}]},
        "outputs": [{"href": composed_put, "storage": "external", "type": "image/vnd.adobe.photoshop"}],
    }
    print("   POST", EP_SMART_OBJECT)
    resp = client.submit(EP_SMART_OBJECT, body_so)
    print("   submit resp:", resp)
    final = client.poll(client.status_url(resp))
    print("   job finale:", final)

    print("4) Rendition…")
    composed_url = st.signed_read_url("spike/composed.psd")
    body_rend = {
        "inputs": [{"href": composed_url, "storage": "external"}],
        "outputs": [{"href": out_put, "storage": "external", "type": "image/jpeg",
                     "width": w, "height": h}],
    }
    print("   POST", EP_RENDITION)
    resp = client.submit(EP_RENDITION, body_rend)
    print("   submit resp:", resp)
    final = client.poll(client.status_url(resp))
    print("   job finale:", final)

    data = st.get("spike/render.jpg")
    out = "spike_render.jpg"
    open(out, "wb").write(data)
    print(f"\nOK — output {len(data)//1024} KB salvato in {out}")
    print("NB: se i payload/endpoint differiscono, aggiornare app/photoshop/compose.py di conseguenza.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
