import type {
  AppSettings,
  FormatProfile,
  FormatProfileInput,
  Job,
  JobPiano,
  OutputItem,
  SourceImage,
  TemplateProfile,
  TemplateProfileInput,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function call<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers = new Headers(opts.headers);
  const res = await fetch(BASE + path, { ...opts, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return res.json();
  return (await res.blob()) as unknown as T;
}

function jsonBody(data: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(data), headers: { "Content-Type": "application/json" } };
}

export const api = {
  // formats
  listFormats: () => call<FormatProfile[]>("/formats"),
  createFormat: (data: FormatProfileInput) => call<FormatProfile>("/formats", jsonBody(data)),
  updateFormat: (id: string, data: FormatProfileInput) =>
    call<FormatProfile>(`/formats/${id}`, { ...jsonBody(data), method: "PUT" }),
  duplicateFormat: (id: string) => call<FormatProfile>(`/formats/${id}/duplicate`, { method: "POST" }),
  deleteFormat: (id: string) => call<void>(`/formats/${id}`, { method: "DELETE" }),
  exportFormats: () => call<{ profili: FormatProfileInput[] }>("/formats/export"),
  importFormats: (payload: { profili: FormatProfileInput[] }) =>
    call<FormatProfile[]>("/formats/import", jsonBody(payload)),

  // templates (Fase 2)
  listTemplates: () => call<TemplateProfile[]>("/templates"),
  createTemplate: (data: TemplateProfileInput) => call<TemplateProfile>("/templates", jsonBody(data)),
  updateTemplate: (id: string, data: TemplateProfileInput) =>
    call<TemplateProfile>(`/templates/${id}`, { ...jsonBody(data), method: "PUT" }),
  deleteTemplate: (id: string) => call<void>(`/templates/${id}`, { method: "DELETE" }),
  async uploadTemplatePsd(id: string, file: File): Promise<TemplateProfile> {
    const fd = new FormData();
    fd.append("file", file);
    return call<TemplateProfile>(`/templates/${id}/psd`, { method: "POST", body: fd });
  },

  // settings
  getSettings: () => call<AppSettings>("/settings"),
  updateSettings: (data: Partial<AppSettings>) =>
    call<AppSettings>("/settings", { ...jsonBody(data), method: "PUT" }),

  // uploads
  async upload(files: File[]): Promise<SourceImage[]> {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return call<SourceImage[]>("/uploads", { method: "POST", body: fd });
  },

  // jobs
  createJob: (source_image_ids: string[], format_ids: string[], template_ids: string[] = []) =>
    call<JobPiano>("/jobs", jsonBody({ source_image_ids, format_ids, template_ids })),
  runJob: (id: string) => call<Job>(`/jobs/${id}/run`, { method: "POST" }),
  retryFailed: (id: string) => call<Job>(`/jobs/${id}/retry-failed`, { method: "POST" }),
  getJob: (id: string) => call<Job>(`/jobs/${id}`),

  // outputs
  previewOutput: (id: string) =>
    call<{ box: { x: number; y: number; w: number; h: number }; master_width: number; master_height: number; needs_outpaint: boolean; nota: string }>(
      `/outputs/${id}/preview`,
      { method: "POST" }
    ),
  recropOutput: (id: string, box: object) => call<OutputItem>(`/outputs/${id}/recrop`, jsonBody({ box })),
  regenerateOutput: (id: string, prompt?: string) =>
    call<OutputItem>(`/outputs/${id}/regenerate`, jsonBody({ prompt: prompt ?? null })),
  approveOutput: (id: string) => call<OutputItem>(`/outputs/${id}/approve`, { method: "POST" }),
  discardOutput: (id: string) => call<OutputItem>(`/outputs/${id}/discard`, { method: "POST" }),

  // media (blob URLs)
  async mediaSource(id: string): Promise<string> {
    const blob = await call<Blob>(`/media/source/${id}`);
    return URL.createObjectURL(blob);
  },
  async mediaOutput(id: string): Promise<string> {
    const blob = await call<Blob>(`/media/output/${id}`);
    return URL.createObjectURL(blob);
  },

  // download (fmt opzionale: 'jpg'|'png'|'webp' per ri-codificare; assente = formato del profilo)
  async downloadOutput(id: string, filename: string, fmt?: string) {
    const q = fmt ? `?fmt=${fmt}` : "";
    const blob = await call<Blob>(`/outputs/${id}/download${q}`);
    triggerDownload(blob, filename);
  },
  async downloadZip(jobId: string, soloApprovati: boolean, fmt?: string) {
    const q = `?solo_approvati=${soloApprovati}${fmt ? `&fmt=${fmt}` : ""}`;
    const blob = await call<Blob>(`/jobs/${jobId}/download.zip${q}`);
    triggerDownload(blob, `batch-${jobId.slice(0, 8)}.zip`);
  },
};

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { ApiError };
