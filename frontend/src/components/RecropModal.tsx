import { useEffect, useState } from "react";
import { api } from "../api";
import type { CropBox, OutputItem } from "../types";
import CropBoxOverlay from "./CropBoxOverlay";
import AuthImg from "./AuthImg";

export default function RecropModal({
  output,
  formatLabel,
  onClose,
  onSaved,
}: {
  output: OutputItem;
  formatLabel: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [masterUrl, setMasterUrl] = useState<string | null>(null);
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const [box, setBox] = useState<CropBox | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let url: string | null = null;
    (async () => {
      try {
        const pv = await api.previewOutput(output.id);
        setDims({ w: pv.master_width, h: pv.master_height });
        setBox(output.crop_box ?? pv.box);
        url = await api.mediaSource(output.source_image_id);
        setMasterUrl(url);
      } catch (e) {
        setError(String(e));
      }
    })();
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [output.id, output.source_image_id, output.crop_box]);

  async function save() {
    if (!box) return;
    setBusy(true);
    setError("");
    try {
      await api.recropOutput(output.id, box);
      onSaved();
      onClose();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Ritaglio manuale — {formatLabel}</h2>
        <p className="muted small">Trascina il riquadro per scegliere cosa includere. Le proporzioni del formato sono mantenute.</p>
        {error && <div className="error-banner">{error}</div>}
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div>
            {masterUrl && dims && box ? (
              <CropBoxOverlay
                src={masterUrl}
                masterW={dims.w}
                masterH={dims.h}
                box={box}
                onChange={setBox}
              />
            ) : (
              <div className="muted">Caricamento master…</div>
            )}
          </div>
          <div style={{ minWidth: 200, flex: 1 }}>
            <h3 className="small">Risultato attuale</h3>
            <AuthImg
              loader={() => api.mediaOutput(output.id)}
              depKey={output.id + (output.storage_path ?? "")}
              style={{ width: "100%", maxWidth: 240, border: "1px solid var(--border)", borderRadius: 8, background: "#f0f1f3" }}
            />
            {box && (
              <p className="hint">Box: {box.x},{box.y} · {box.w}×{box.h} px</p>
            )}
          </div>
        </div>
        <div className="toolbar" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button onClick={onClose}>Chiudi</button>
          <button className="primary" onClick={save} disabled={busy || !box}>
            {busy ? "Rigenero…" : "Applica ritaglio"}
          </button>
        </div>
      </div>
    </div>
  );
}
