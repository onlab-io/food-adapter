import { useState } from "react";
import { api } from "../api";
import type { TemplateProfile, TemplateProfileInput } from "../types";

const VUOTO: TemplateProfileInput = {
  nome: "",
  larghezza_px: 2750,
  altezza_px: 650,
  formato_file: "jpg",
  qualita: 92,
  suffisso_naming: "",
  smart_object_layer: "",
  text_layers: {},
  preserve_mode: "sfondo_only",
  prompt_default: "",
  engine: "photoshop",
};

export default function TemplateEditor({
  initial,
  onSaved,
  onClose,
}: {
  initial?: TemplateProfile;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [t, setT] = useState<TemplateProfileInput>(
    initial ? { ...(initial as unknown as TemplateProfileInput) } : { ...VUOTO }
  );
  const [psdName, setPsdName] = useState<string | null>(initial?.psd_storage_path ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function set<K extends keyof TemplateProfileInput>(k: K, v: TemplateProfileInput[K]) {
    setT((p) => ({ ...p, [k]: v }));
  }

  async function save() {
    if (!t.nome.trim()) return;
    setBusy(true);
    setError("");
    try {
      const saved = initial ? await api.updateTemplate(initial.id, t) : await api.createTemplate(t);
      // PSD upload se selezionato un nuovo file
      const fileInput = document.getElementById("psd-file") as HTMLInputElement | null;
      if (fileInput?.files?.[0]) {
        await api.uploadTemplatePsd(saved.id, fileInput.files[0]);
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
        <h2>{initial ? "Modifica template" : "Nuovo template PSD"}</h2>
        {error && <div className="error-banner">{error}</div>}

        <div className="field">
          <label>Nome</label>
          <input value={t.nome} onChange={(e) => set("nome", e.target.value)} placeholder="es. Ledwall hall ingresso" />
        </div>

        <div className="row">
          <div className="field">
            <label>Larghezza (px)</label>
            <input type="number" value={t.larghezza_px} onChange={(e) => set("larghezza_px", parseInt(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label>Altezza (px)</label>
            <input type="number" value={t.altezza_px} onChange={(e) => set("altezza_px", parseInt(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label>File</label>
            <select value={t.formato_file} onChange={(e) => set("formato_file", e.target.value as TemplateProfileInput["formato_file"])}>
              <option value="jpg">JPG</option>
              <option value="png">PNG</option>
              <option value="webp">WEBP</option>
            </select>
          </div>
          <div className="field">
            <label>Suffisso</label>
            <input value={t.suffisso_naming} onChange={(e) => set("suffisso_naming", e.target.value)} placeholder="_ledwall" />
          </div>
        </div>

        <div className="row">
          <div className="field">
            <label>Motore</label>
            <select value={t.engine} onChange={(e) => set("engine", e.target.value as TemplateProfileInput["engine"])}>
              <option value="photoshop">Adobe Photoshop API (AI)</option>
              <option value="local">Stub locale (no AI, test)</option>
            </select>
          </div>
          <div className="field">
            <label>Layer smart object (prodotto)</label>
            <input value={t.smart_object_layer} onChange={(e) => set("smart_object_layer", e.target.value)} placeholder="es. PRODOTTO" />
          </div>
          <div className="field">
            <label>Preservazione</label>
            <select value={t.preserve_mode} onChange={(e) => set("preserve_mode", e.target.value as TemplateProfileInput["preserve_mode"])}>
              <option value="sfondo_only">Solo sfondo (piatto intatto)</option>
              <option value="full_ai">Full AI (rigenera tutto)</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label>Prompt sfondo (opzionale)</label>
          <textarea
            rows={2}
            value={t.prompt_default}
            onChange={(e) => set("prompt_default", e.target.value)}
            placeholder="vuoto = estende lo sfondo esistente"
          />
        </div>

        <div className="field">
          <label>File PSD del template {psdName ? "(caricato ✓)" : ""}</label>
          <input id="psd-file" type="file" accept=".psd" onChange={(e) => setPsdName(e.target.files?.[0]?.name ?? psdName)} />
          {t.preserve_mode === "full_ai" && (
            <div className="hint" style={{ color: "var(--warn)" }}>
              ⚠️ Full AI può alterare il prodotto reale: usare con cautela per il food in vendita.
            </div>
          )}
        </div>

        <div className="toolbar" style={{ justifyContent: "flex-end", marginTop: 14 }}>
          <button onClick={onClose}>Annulla</button>
          <button className="primary" onClick={save} disabled={busy || !t.nome.trim()}>
            {busy ? "Salvataggio…" : "Salva"}
          </button>
        </div>
      </div>
    </div>
  );
}
