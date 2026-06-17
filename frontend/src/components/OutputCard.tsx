import { api } from "../api";
import type { OutputItem } from "../types";
import AuthImg from "./AuthImg";

const STATO_TAG: Record<string, { cls: string; label: string }> = {
  queued: { cls: "muted", label: "in coda" },
  processing: { cls: "warn", label: "in corso" },
  done: { cls: "ok", label: "pronto" },
  approved: { cls: "ok", label: "approvato" },
  error: { cls: "err", label: "errore" },
  discarded: { cls: "muted", label: "scartato" },
};

export default function OutputCard({
  output,
  label,
  sublabel,
  filename,
  onChanged,
  onRecrop,
  onRegenerate,
  onZoom,
}: {
  output: OutputItem;
  label: string;
  sublabel: string;
  filename: string;
  onChanged: () => void;
  onRecrop: () => void;
  onRegenerate: () => void;
  onZoom: () => void;
}) {
  const tag = STATO_TAG[output.stato] ?? { cls: "muted", label: output.stato };
  const ready = output.stato === "done" || output.stato === "approved";
  const isCompose = output.kind === "compose";

  return (
    <div className="output-card">
      {ready ? (
        <AuthImg
          loader={() => api.mediaOutput(output.id)}
          depKey={output.id + (output.storage_path ?? "")}
          alt={label}
          onClick={onZoom}
        />
      ) : (
        <div style={{ height: 130, display: "grid", placeItems: "center", background: "#f0f1f3", color: "#9aa0aa", fontSize: 13 }}>
          {output.stato === "error" ? "✕" : output.stato === "processing" ? "…" : "—"}
        </div>
      )}
      <div className="body">
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div className="muted">{sublabel}</div>
        <div style={{ marginTop: 6, display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
          <span className={`tag ${tag.cls}`}>{tag.label}</span>
          {output.is_ai && <span className="tag" style={{ background: "#f3e8ff", color: "#7e22ce", borderColor: "#e3ccfb" }}>🟣 Generato con AI</span>}
          {output.needs_outpaint && !isCompose && <span className="tag warn">AI in Fase 2</span>}
        </div>
        {output.error_msg && <div className="hint" style={{ color: "var(--err)" }}>{output.error_msg}</div>}
      </div>
      {ready && (
        <div className="actions">
          {output.stato !== "approved" && (
            <button className="small primary" onClick={async () => { await api.approveOutput(output.id); onChanged(); }}>
              Approva
            </button>
          )}
          {isCompose ? (
            <button className="small" onClick={onRegenerate}>Rigenera</button>
          ) : (
            <button className="small" onClick={onRecrop}>Ritaglia</button>
          )}
          <button className="small" onClick={() => api.downloadOutput(output.id, filename)}>Scarica</button>
          <button className="small danger" onClick={async () => { await api.discardOutput(output.id); onChanged(); }}>
            Scarta
          </button>
        </div>
      )}
    </div>
  );
}
