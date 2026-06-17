import { useState } from "react";
import type { FormatProfile, FormatProfileInput } from "../types";

const VUOTO: FormatProfileInput = {
  nome: "",
  larghezza_px: 1080,
  altezza_px: 1080,
  formato_file: "jpg",
  qualita: 92,
  strategia_crop: "saliency",
  punto_focale: "piatto",
  outpaint_mode: "off",
  outpaint_engine: "none",
  preserve_mode: "sfondo_only",
  prompt_default: "",
  fallback_no_ai: "crop",
  suffisso_naming: "",
};

export function arLabel(w: number, h: number): string {
  const g = gcd(w, h);
  return `${(w / h).toFixed(2)} (${w / g}:${h / g})`;
}
function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

export default function FormatEditor({
  initial,
  onSave,
  onClose,
}: {
  initial?: FormatProfile;
  onSave: (data: FormatProfileInput) => Promise<void>;
  onClose: () => void;
}) {
  const [f, setF] = useState<FormatProfileInput>(
    initial ? { ...(initial as FormatProfileInput) } : { ...VUOTO }
  );
  const [busy, setBusy] = useState(false);

  function set<K extends keyof FormatProfileInput>(k: K, v: FormatProfileInput[K]) {
    setF((p) => ({ ...p, [k]: v }));
  }

  async function save() {
    if (!f.nome.trim() || f.larghezza_px <= 0 || f.altezza_px <= 0) return;
    setBusy(true);
    try {
      await onSave(f);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <h2>{initial ? "Modifica formato" : "Nuovo formato"}</h2>

        <div className="field">
          <label>Nome / etichetta</label>
          <input value={f.nome} onChange={(e) => set("nome", e.target.value)} placeholder="es. Card prodotto" />
        </div>

        <div className="row">
          <div className="field">
            <label>Larghezza (px)</label>
            <input
              type="number"
              value={f.larghezza_px}
              onChange={(e) => set("larghezza_px", parseInt(e.target.value) || 0)}
            />
          </div>
          <div className="field">
            <label>Altezza (px)</label>
            <input
              type="number"
              value={f.altezza_px}
              onChange={(e) => set("altezza_px", parseInt(e.target.value) || 0)}
            />
          </div>
          <div className="field">
            <label>Aspect ratio</label>
            <input value={f.larghezza_px > 0 && f.altezza_px > 0 ? arLabel(f.larghezza_px, f.altezza_px) : "-"} disabled />
          </div>
        </div>

        <div className="row">
          <div className="field">
            <label>Formato file</label>
            <select value={f.formato_file} onChange={(e) => set("formato_file", e.target.value as FormatProfileInput["formato_file"])}>
              <option value="jpg">JPG</option>
              <option value="png">PNG</option>
              <option value="webp">WEBP</option>
            </select>
          </div>
          <div className="field">
            <label>Qualità (jpg/webp)</label>
            <input
              type="number"
              min={1}
              max={100}
              value={f.qualita}
              onChange={(e) => set("qualita", parseInt(e.target.value) || 85)}
            />
          </div>
          <div className="field">
            <label>Suffisso naming</label>
            <input value={f.suffisso_naming} onChange={(e) => set("suffisso_naming", e.target.value)} placeholder="_card" />
          </div>
        </div>

        <div className="row">
          <div className="field">
            <label>Strategia di crop</label>
            <select value={f.strategia_crop} onChange={(e) => set("strategia_crop", e.target.value as FormatProfileInput["strategia_crop"])}>
              <option value="saliency">Saliency (contenuto principale)</option>
              <option value="entropy">Entropy</option>
              <option value="center">Centrato (geometrico)</option>
              <option value="manual_anchor">Ancora manuale</option>
            </select>
          </div>
          <div className="field">
            <label>Se servirebbe outpainting (Fase 1)</label>
            <select value={f.fallback_no_ai} onChange={(e) => set("fallback_no_ai", e.target.value as FormatProfileInput["fallback_no_ai"])}>
              <option value="crop">Crop forzato (centrato sul soggetto)</option>
              <option value="letterbox">Letterbox (bande)</option>
            </select>
          </div>
        </div>

        <p className="hint">
          L'outpainting AI arriverà in Fase 2. Per i formati che richiederebbero scena aggiuntiva (es. ledwall),
          questa scelta decide il comportamento locale senza AI.
        </p>

        <div className="toolbar" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button onClick={onClose}>Annulla</button>
          <button className="primary" onClick={save} disabled={busy || !f.nome.trim()}>
            {busy ? "Salvataggio…" : "Salva"}
          </button>
        </div>
      </div>
    </div>
  );
}
