import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AppSettings, FormatProfile, FormatProfileInput, TemplateProfile } from "../types";
import FormatEditor, { arLabel } from "../components/FormatEditor";
import TemplateEditor from "../components/TemplateEditor";

export default function Formati() {
  const [formats, setFormats] = useState<FormatProfile[]>([]);
  const [templates, setTemplates] = useState<TemplateProfile[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [editing, setEditing] = useState<FormatProfile | "new" | null>(null);
  const [editingTpl, setEditingTpl] = useState<TemplateProfile | "new" | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const [f, s, t] = await Promise.all([api.listFormats(), api.getSettings(), api.listTemplates()]);
      setFormats(f);
      setSettings(s);
      setTemplates(t);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function save(data: FormatProfileInput) {
    if (editing === "new") await api.createFormat(data);
    else if (editing) await api.updateFormat(editing.id, data);
    setEditing(null);
    load();
  }

  async function patchSettings(patch: Partial<AppSettings>) {
    const s = await api.updateSettings(patch);
    setSettings(s);
  }

  async function exportJson() {
    const data = await api.exportFormats();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "formati.json";
    a.click();
  }

  async function importJson(file: File) {
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      await api.importFormats(payload);
      load();
    } catch (e) {
      setError("Import fallito: " + String(e));
    }
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>Profili di formato</h2>
          <button className="primary" onClick={() => setEditing("new")}>
            + Nuovo formato
          </button>
          <button onClick={exportJson} disabled={!formats.length}>
            Esporta JSON
          </button>
          <button onClick={() => fileRef.current?.click()}>Importa JSON</button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json"
            style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && importJson(e.target.files[0])}
          />
        </div>

        {formats.length === 0 ? (
          <p className="muted">Nessun formato. Creane uno per iniziare (consigliati: card, modale, social, ledwall…).</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Dimensioni</th>
                <th>Aspect ratio</th>
                <th>Strategia</th>
                <th>File</th>
                <th>Suffisso</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {formats.map((f) => (
                <tr key={f.id}>
                  <td>{f.nome}</td>
                  <td>{f.larghezza_px}×{f.altezza_px}</td>
                  <td className="muted">{arLabel(f.larghezza_px, f.altezza_px)}</td>
                  <td><span className="tag muted">{f.strategia_crop}</span></td>
                  <td>{f.formato_file.toUpperCase()}</td>
                  <td className="muted">{f.suffisso_naming || "—"}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="small" onClick={() => setEditing(f)}>Modifica</button>{" "}
                    <button className="small" onClick={async () => { await api.duplicateFormat(f.id); load(); }}>Duplica</button>{" "}
                    <button
                      className="small danger"
                      onClick={async () => {
                        if (confirm(`Eliminare il formato "${f.nome}"?`)) {
                          await api.deleteFormat(f.id);
                          load();
                        }
                      }}
                    >
                      Elimina
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>Template PSD (Fase 2 · prodotto finito con AI)</h2>
          <button className="primary" onClick={() => setEditingTpl("new")}>+ Nuovo template</button>
        </div>
        <p className="muted small" style={{ marginTop: -6 }}>
          I template compongono il prodotto finito dal PSD (smart object + sfondo generato con Adobe).
          Senza credenziali Adobe viene usato lo stub locale (anteprima a costo zero).
        </p>
        {templates.length === 0 ? (
          <p className="muted">Nessun template. Carica i tuoi PSD (card/modale/ledwall) per la composizione AI.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Nome</th><th>Dimensioni</th><th>Motore</th><th>Smart object</th><th>PSD</th><th></th></tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id}>
                  <td>{t.nome}</td>
                  <td>{t.larghezza_px}×{t.altezza_px}</td>
                  <td><span className="tag muted">{t.engine === "photoshop" ? "Photoshop AI" : "stub locale"}</span></td>
                  <td className="muted">{t.smart_object_layer || "—"}</td>
                  <td>{t.psd_storage_path ? <span className="tag ok">caricato</span> : <span className="tag warn">manca</span>}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="small" onClick={() => setEditingTpl(t)}>Modifica</button>{" "}
                    <button
                      className="small danger"
                      onClick={async () => {
                        if (confirm(`Eliminare il template "${t.nome}"?`)) {
                          await api.deleteTemplate(t.id);
                          load();
                        }
                      }}
                    >
                      Elimina
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {settings && (
        <div className="panel">
          <h2>Impostazioni generali</h2>
          <div className="row">
            <div className="field">
              <label>Pattern di naming</label>
              <input
                value={settings.naming_pattern}
                onChange={(e) => setSettings({ ...settings, naming_pattern: e.target.value })}
                onBlur={(e) => patchSettings({ naming_pattern: e.target.value })}
              />
              <div className="hint">Placeholder: {"{nome} {suffisso} {formato} {larghezza} {altezza} {ext}"}</div>
            </div>
            <div className="field">
              <label>Struttura zip</label>
              <select
                value={settings.zip_structure}
                onChange={(e) => patchSettings({ zip_structure: e.target.value as AppSettings["zip_structure"] })}
              >
                <option value="per_formato">Cartelle per formato</option>
                <option value="per_immagine">Cartelle per immagine</option>
                <option value="flat">Tutto in radice</option>
              </select>
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>Tolleranza crop (oltre → serve outpainting): {Math.round(settings.tolleranza_crop * 100)}%</label>
              <input
                type="range"
                min={0}
                max={90}
                value={Math.round(settings.tolleranza_crop * 100)}
                onChange={(e) => setSettings({ ...settings, tolleranza_crop: parseInt(e.target.value) / 100 })}
                onMouseUp={(e) => patchSettings({ tolleranza_crop: parseInt((e.target as HTMLInputElement).value) / 100 })}
              />
            </div>
            <div className="field">
              <label>Dimensione max file (MB)</label>
              <input
                type="number"
                value={settings.max_file_mb}
                onChange={(e) => setSettings({ ...settings, max_file_mb: parseInt(e.target.value) || 40 })}
                onBlur={(e) => patchSettings({ max_file_mb: parseInt(e.target.value) || 40 })}
              />
            </div>
          </div>
        </div>
      )}

      {editing && (
        <FormatEditor
          initial={editing === "new" ? undefined : editing}
          onSave={save}
          onClose={() => setEditing(null)}
        />
      )}

      {editingTpl && (
        <TemplateEditor
          initial={editingTpl === "new" ? undefined : editingTpl}
          onSaved={load}
          onClose={() => setEditingTpl(null)}
        />
      )}
    </>
  );
}
