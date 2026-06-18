import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { FormatProfile, Job, JobPiano, OutputItem, SourceImage, TemplateProfile } from "../types";
import AuthImg from "../components/AuthImg";
import OutputCard from "../components/OutputCard";
import RecropModal from "../components/RecropModal";

function slugName(srcName: string, suffisso: string, ext: string): string {
  const base = srcName.replace(/\.[^.]+$/, "").replace(/[^\w-]+/g, "-");
  return `${base}${suffisso || ""}.${ext}`;
}

const STRAT_TAG: Record<string, string> = {
  crop_leggero: "ok",
  crop_aggressivo: "warn",
  needs_outpaint: "err",
  compose: "muted",
};

export default function Batch() {
  const [formats, setFormats] = useState<FormatProfile[]>([]);
  const [templates, setTemplates] = useState<TemplateProfile[]>([]);
  const [selFmt, setSelFmt] = useState<Set<string>>(new Set());
  const [selTpl, setSelTpl] = useState<Set<string>>(new Set());
  const [sources, setSources] = useState<SourceImage[]>([]);
  const [piano, setPiano] = useState<JobPiano | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [costoOk, setCostoOk] = useState(false);
  const [recrop, setRecrop] = useState<OutputItem | null>(null);
  const [regen, setRegen] = useState<OutputItem | null>(null);
  const [regenPrompt, setRegenPrompt] = useState("");
  const [zoom, setZoom] = useState<OutputItem | null>(null);
  const [dlFormat, setDlFormat] = useState<string>(""); // "" = formato del profilo; jpg|png|webp = ri-codifica
  const fileRef = useRef<HTMLInputElement>(null);

  const fmtById = useMemo(() => new Map(formats.map((f) => [f.id, f])), [formats]);
  const tplById = useMemo(() => new Map(templates.map((t) => [t.id, t])), [templates]);

  useEffect(() => {
    Promise.all([api.listFormats(), api.listTemplates()]).then(([f, t]) => {
      setFormats(f);
      setTemplates(t);
      setSelFmt(new Set(f.map((x) => x.id)));
    });
  }, []);

  // Traccia il job attivo così il logout ("Esci") può cancellarne i file.
  useEffect(() => {
    if (job) localStorage.setItem("fia_active_job", job.id);
  }, [job?.id]);

  useEffect(() => {
    if (!job || job.stato !== "running") return;
    const i = setInterval(async () => {
      try {
        setJob(await api.getJob(job.id));
      } catch {
        /* ignore */
      }
    }, 1000);
    return () => clearInterval(i);
  }, [job?.id, job?.stato]);

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    setBusy(true);
    setError("");
    try {
      const up = await api.upload(Array.from(files));
      setSources((s) => [...s, ...up]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggle(set: Set<string>, setter: (s: Set<string>) => void, id: string) {
    const n = new Set(set);
    n.has(id) ? n.delete(id) : n.add(id);
    setter(n);
  }

  async function creaPiano() {
    setBusy(true);
    setError("");
    setCostoOk(false);
    try {
      const p = await api.createJob(
        sources.map((s) => s.id),
        [...selFmt],
        [...selTpl]
      );
      setPiano(p);
      setJob(await api.getJob(p.job_id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function avvia() {
    if (!job) return;
    setBusy(true);
    try {
      setJob(await api.runJob(job.id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function refreshJob() {
    if (job) setJob(await api.getJob(job.id));
  }

  async function reset() {
    // A fine batch: cancella master + output del job corrente (la config resta).
    if (job) {
      try {
        await api.deleteJob(job.id);
      } catch {
        /* best-effort */
      }
      localStorage.removeItem("fia_active_job");
    }
    setPiano(null);
    setJob(null);
    setSources([]);
    setCostoOk(false);
  }

  async function doRegen() {
    if (!regen) return;
    setBusy(true);
    try {
      await api.regenerateOutput(regen.id, regenPrompt || undefined);
      setRegen(null);
      setRegenPrompt("");
      refreshJob();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const outputs = job?.outputs ?? [];
  const done = outputs.filter((o) => o.stato === "done" || o.stato === "approved").length;
  const errored = outputs.filter((o) => o.stato === "error").length;
  const total = outputs.length;
  const approved = outputs.filter((o) => o.stato === "approved").length;
  const started = job && job.stato !== "created";
  const totalSel = selFmt.size + selTpl.size;

  const bySource = useMemo(() => {
    const m = new Map<string, OutputItem[]>();
    for (const o of outputs) {
      if (!m.has(o.source_image_id)) m.set(o.source_image_id, []);
      m.get(o.source_image_id)!.push(o);
    }
    return m;
  }, [outputs]);
  const srcById = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources]);

  function metaOf(o: OutputItem): { label: string; sublabel: string; filename: string } {
    const src = srcById.get(o.source_image_id);
    const srcName = src?.original_filename ?? "master";
    if (o.kind === "compose") {
      const t = o.template_profile_id ? tplById.get(o.template_profile_id) : undefined;
      return {
        label: t?.nome ?? "Template",
        sublabel: t ? `${t.larghezza_px}×${t.altezza_px} · PSD` : "",
        filename: slugName(srcName, t?.suffisso_naming ?? "", t?.formato_file ?? "jpg"),
      };
    }
    const f = o.format_profile_id ? fmtById.get(o.format_profile_id) : undefined;
    return {
      label: f?.nome ?? "Formato",
      sublabel: f ? `${f.larghezza_px}×${f.altezza_px} · ${f.formato_file.toUpperCase()}` : "",
      filename: slugName(srcName, f?.suffisso_naming ?? "", f?.formato_file ?? "jpg"),
    };
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      {!piano && (
        <div className="panel">
          <h2>1 · Carica gli scatti master</h2>
          <div
            className={`dropzone ${drag ? "drag" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
            onClick={() => fileRef.current?.click()}
            style={{ cursor: "pointer" }}
          >
            {busy ? "Caricamento…" : "Trascina qui le immagini, oppure clicca per selezionarle"}
            <div className="hint">Formati accettati: JPG, PNG, WEBP, TIFF</div>
          </div>
          <input ref={fileRef} type="file" multiple accept=".jpg,.jpeg,.png,.webp,.tif,.tiff"
            style={{ display: "none" }} onChange={(e) => handleFiles(e.target.files)} />

          {sources.length > 0 && (
            <>
              <p className="muted small" style={{ marginTop: 14 }}>{sources.length} immagini caricate</p>
              <div className="grid-thumbs">
                {sources.map((s) => (
                  <div className="thumb" key={s.id}>
                    <AuthImg loader={() => api.mediaSource(s.id)} depKey={s.id} alt={s.original_filename} />
                    <button className="rm small danger" onClick={() => setSources((a) => a.filter((x) => x.id !== s.id))}>✕</button>
                    <div className="meta">
                      <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.original_filename}</div>
                      <span className="muted">{s.width}×{s.height}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {!piano && (
        <div className="panel">
          <h2>2 · Scegli formati e template</h2>
          {formats.length === 0 && templates.length === 0 ? (
            <p className="muted">Niente configurato. Vai in <b>Impostazioni</b> per creare formati o template.</p>
          ) : (
            <>
              {formats.length > 0 && (
                <>
                  <h3 className="small" style={{ marginTop: 4 }}>Formati (crop, gratuito)</h3>
                  {formats.map((f) => (
                    <label className="checkline" key={f.id}>
                      <input type="checkbox" checked={selFmt.has(f.id)} onChange={() => toggle(selFmt, setSelFmt, f.id)} />
                      <b>{f.nome}</b> <span className="muted">{f.larghezza_px}×{f.altezza_px} · {f.strategia_crop}</span>
                    </label>
                  ))}
                </>
              )}
              {templates.length > 0 && (
                <>
                  <h3 className="small" style={{ marginTop: 14 }}>Template PSD (composizione AI)</h3>
                  {templates.map((t) => (
                    <label className="checkline" key={t.id}>
                      <input type="checkbox" checked={selTpl.has(t.id)} onChange={() => toggle(selTpl, setSelTpl, t.id)} />
                      <b>{t.nome}</b>{" "}
                      <span className="muted">{t.larghezza_px}×{t.altezza_px}</span>{" "}
                      <span className="tag muted">{t.engine === "photoshop" ? "Photoshop AI" : "stub locale"}</span>
                      {!t.psd_storage_path && t.engine === "photoshop" && <span className="tag warn">PSD mancante</span>}
                    </label>
                  ))}
                </>
              )}
            </>
          )}
          <div className="toolbar" style={{ marginTop: 14 }}>
            <button className="primary" disabled={busy || sources.length === 0 || totalSel === 0} onClick={creaPiano}>
              Calcola il piano →
            </button>
            <span className="muted small">{sources.length} immagini × {totalSel} output-type = {sources.length * totalSel} output</span>
          </div>
        </div>
      )}

      {piano && !started && (
        <div className="panel">
          <h2>3 · Piano di esecuzione</h2>
          <p className="small">
            <span className={piano.operazioni_ai_previste > 0 ? "tag warn" : "tag ok"}>
              {piano.operazioni_ai_previste} operazioni AI
            </span>{" "}
            <span className="muted">Costo stimato: € {piano.costo_stimato.toFixed(2)}</span>
          </p>
          <table>
            <thead>
              <tr><th>Immagine</th><th>Destinazione</th><th>Tipo</th><th>Note</th></tr>
            </thead>
            <tbody>
              {piano.voci.map((v, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.source_filename}</td>
                  <td>{v.format_label}</td>
                  <td>
                    <span className={`tag ${STRAT_TAG[v.strategia] ?? "muted"}`}>{v.strategia}</span>{" "}
                    {v.is_ai && <span className="tag" style={{ background: "#f3e8ff", color: "#7e22ce", borderColor: "#e3ccfb" }}>AI</span>}
                  </td>
                  <td className="muted small">{v.nota}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {piano.costo_stimato > 0 && (
            <label className="checkline" style={{ marginTop: 12 }}>
              <input type="checkbox" checked={costoOk} onChange={(e) => setCostoOk(e.target.checked)} />
              Confermo di voler eseguire <b>{piano.operazioni_ai_previste}</b> operazioni AI a pagamento (≈ € {piano.costo_stimato.toFixed(2)})
            </label>
          )}

          <div className="toolbar" style={{ marginTop: 14 }}>
            <button className="primary" onClick={avvia} disabled={busy || (piano.costo_stimato > 0 && !costoOk)}>
              Avvia elaborazione
            </button>
            <button onClick={reset}>Annulla</button>
          </div>
        </div>
      )}

      {started && (
        <div className="panel">
          <div className="toolbar">
            <h2 style={{ margin: 0, flex: 1 }}>4 · Risultati</h2>
            {errored > 0 && (
              <button onClick={async () => { await api.retryFailed(job!.id); refreshJob(); }}>Riprova falliti ({errored})</button>
            )}
            <label className="small muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              Formato:
              <select value={dlFormat} onChange={(e) => setDlFormat(e.target.value)} style={{ width: "auto" }}>
                <option value="">come da profilo</option>
                <option value="webp">WEBP</option>
                <option value="jpg">JPG</option>
                <option value="png">PNG</option>
              </select>
            </label>
            <button className="primary" disabled={approved === 0} onClick={() => api.downloadZip(job!.id, true, dlFormat || undefined)}>
              Scarica ZIP approvati ({approved})
            </button>
            <button disabled={done === 0} onClick={() => api.downloadZip(job!.id, false, dlFormat || undefined)}>ZIP tutti i completati</button>
            <button onClick={reset}>Nuovo batch</button>
          </div>

          <div className="progressbar"><div style={{ width: `${total ? (done / total) * 100 : 0}%` }} /></div>
          <p className="small muted" style={{ marginTop: 6 }}>
            {done}/{total} completati{errored ? ` · ${errored} errori` : ""}{job!.stato === "running" ? " · elaborazione in corso…" : ""}
          </p>

          {Array.from(bySource.entries()).map(([sid, items]) => (
            <div className="source-group" key={sid}>
              <h3>{srcById.get(sid)?.original_filename ?? sid}</h3>
              <div className="outputs-grid">
                {items.map((o) => {
                  const m = metaOf(o);
                  return (
                    <OutputCard
                      key={o.id}
                      output={o}
                      label={m.label}
                      sublabel={m.sublabel}
                      filename={m.filename}
                      dlFormat={dlFormat || undefined}
                      onChanged={refreshJob}
                      onRecrop={() => setRecrop(o)}
                      onRegenerate={() => { setRegen(o); setRegenPrompt(o.prompt_usato ?? ""); }}
                      onZoom={() => setZoom(o)}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {recrop && (
        <RecropModal
          output={recrop}
          formatLabel={metaOf(recrop).label}
          onClose={() => setRecrop(null)}
          onSaved={refreshJob}
        />
      )}

      {regen && (
        <div className="modal-backdrop" onClick={() => setRegen(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
            <h3>Rigenera con prompt — {metaOf(regen).label}</h3>
            <p className="muted small">Lascia vuoto per estendere lo sfondo esistente, oppure descrivi la scena.</p>
            <textarea rows={3} value={regenPrompt} onChange={(e) => setRegenPrompt(e.target.value)}
              placeholder="es. estendi la tovaglia di lino chiaro e il piano in legno, luce morbida da sinistra" />
            <div className="toolbar" style={{ justifyContent: "flex-end", marginTop: 12 }}>
              <button onClick={() => setRegen(null)}>Annulla</button>
              <button className="primary" onClick={doRegen} disabled={busy}>{busy ? "Rigenero…" : "Rigenera"}</button>
            </div>
          </div>
        </div>
      )}

      {zoom && (
        <div className="modal-backdrop" onClick={() => setZoom(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ textAlign: "center" }}>
            <h3>{metaOf(zoom).label}</h3>
            <AuthImg loader={() => api.mediaOutput(zoom.id)} depKey={zoom.id + (zoom.storage_path ?? "")}
              style={{ maxWidth: "100%", maxHeight: "75vh", borderRadius: 8 }} />
          </div>
        </div>
      )}
    </>
  );
}
