// API Client communicating with Python backend via pywebview.api

declare global {
  interface Window {
    pywebview?: {
      api: Record<string, (...args: any[]) => Promise<any>>;
    };
  }
}

export interface Profile {
  nama: string;
  nim: string;
  prodi: string;
}

export interface Dosen {
  id?: number;
  nama: string;
  gelar: string;
  identitas: string;
}

export interface MataKuliah {
  id?: number;
  nama: string;
  kode: string;
}

export interface Logo {
  id: number;
  nama: string;
  path: string;
  exists: boolean;
}

export interface TemplateSpec {
  paper: string;
  margin: string;
  font: string;
  spacing: string;
}

export interface TemplateItem {
  id: number;
  nama: string;
  deskripsi: string;
  path: string;
  status: string;
  missing: string[];
  not_standalone: string[];
  unknown: string[];
  placeholders: string[];
  is_default?: boolean;
  spec?: TemplateSpec;
}

export interface AppConfig {
  ai_base_url: string;
  ai_api_key: string;
  ai_model: string;
  ai_temperature: number;
  citation_style: string;
  dosen_review: boolean;
}

export interface Author {
  family: string;
  given: string;
  is_org?: boolean;
  abbrev?: string;
}

export interface SourceRecord {
  authors: Author[];
  year: string;
  title: string;
  container: string;
  doi: string;
  url: string;
  text?: string;
  kind?: string;
}

export interface Sentence {
  uid: string;
  text: string;
  quote: string;
  source_ids: number[];
  is_factual: boolean;
  origin?: string;
  citation?: boolean;
}

export interface Paragraph {
  sentences: Sentence[];
}

export interface Section {
  level: number;
  title: string;
  paragraphs: Paragraph[];
}

export interface SentenceStatus {
  index: number;
  uid: string;
  status: 'terverifikasi' | 'belum_terverifikasi' | 'tidak_terverifikasi' | 'perlu_ditinjau' | 'bukan_klaim' | 'bukan_klaim_faktual';
  reason?: string;
  is_factual: boolean;
  source_ids: number[];
}

export interface FormatVariant {
  code: string;
  name: string;
  description: string;
  skeleton: string[];
  outline_titles: string[];
}

export interface SavedDraftItem {
  draft_id: string;
  title: string;
  sources_count: number;
  sections_count: number;
  sentence_count: number;
  is_active: boolean;
  mtime: number;
}

// Fallback helper for pywebview API
async function callApi<T = any>(method: string, ...args: any[]): Promise<T> {
  if (window.pywebview?.api && typeof window.pywebview.api[method] === 'function') {
    return await window.pywebview.api[method](...args);
  }
  console.warn(`[API Mock] ${method} called without pywebview bridge:`, args);
  return null as any;
}

export const api = {
  // Config
  getConfig: () => callApi<AppConfig>('get_config'),
  saveConfig: (cfg: Partial<AppConfig>) => callApi<{ success: boolean; config: AppConfig }>('save_config', cfg),
  testAiConnection: (url?: string, key?: string, model?: string) =>
    callApi<{ ok: boolean; message: string }>('test_ai_connection', url, key, model),
  fetchModels: (url?: string, key?: string) =>
    callApi<{ ok: boolean; models: string[]; error?: string }>('fetch_models', url, key),

  // Profile & Entities
  getProfile: () => callApi<Profile>('get_profile'),
  saveProfile: (p: Profile) => callApi<{ success: boolean }>('save_profile', p),

  listDosen: () => callApi<Dosen[]>('list_dosen'),
  addDosen: (d: Dosen) => callApi<{ success: boolean; dosen: Dosen }>('add_dosen', d),
  updateDosen: (d: Dosen) => callApi<{ success: boolean }>('update_dosen', d),
  deleteDosen: (id: number) => callApi<{ success: boolean }>('delete_dosen', id),

  listMatkul: () => callApi<MataKuliah[]>('list_matkul'),
  addMatkul: (m: MataKuliah) => callApi<{ success: boolean; matkul: MataKuliah }>('add_matkul', m),
  updateMatkul: (m: MataKuliah) => callApi<{ success: boolean }>('update_matkul', m),
  deleteMatkul: (id: number) => callApi<{ success: boolean }>('delete_matkul', id),

  listLogos: () => callApi<Logo[]>('list_logos'),
  uploadLogo: () => callApi<{ success?: boolean; logo?: Logo; cancelled?: boolean }>('upload_logo'),
  deleteLogo: (id: number) => callApi<{ success: boolean }>('delete_logo', id),

  // Templates
  listTemplates: () => callApi<TemplateItem[]>('list_templates'),
  uploadTemplate: () => callApi<{ success?: boolean; template?: any; cancelled?: boolean }>('upload_template'),
  deleteTemplate: (id: number) => callApi<{ success: boolean }>('delete_template', id),
  createDefaultTemplate: (options?: { font_name?: string; margin_preset?: string; line_spacing?: number }) =>
    callApi<{ success: boolean; path?: string; error?: string }>('create_default_template', options),
  openTemplate: (id: number) => callApi<{ success: boolean; error?: string }>('open_template', id),
  openTemplatesFolder: () => callApi<{ success: boolean; error?: string }>('open_templates_folder'),

  // Sources
  pickPdfSource: () => callApi<{ success?: boolean; record?: SourceRecord; error?: string; cancelled?: boolean }>('pick_pdf_source'),
  addWebSource: (url: string) => callApi<{ success?: boolean; record?: SourceRecord; error?: string }>('add_web_source', url),
  addManualSource: (text: string) => callApi<{ success?: boolean; record?: SourceRecord; error?: string }>('add_manual_source', text),
  resolveDoiSource: (doi: string) => callApi<{ success?: boolean; record?: SourceRecord; error?: string }>('resolve_doi_source', doi),

  // Formats & Outlines
  getFormatVariants: () => callApi<FormatVariant[]>('get_format_variants'),
  suggestOutline: (topic: string, sources: SourceRecord[]) => callApi<{ success?: boolean; outline?: string[]; error?: string }>('suggest_outline', topic, sources),

  // Drafts & Projects
  loadActiveDraft: () => callApi<{ has_draft: boolean; fields?: any; sources?: SourceRecord[]; sections?: Section[]; done?: string[] }>('load_active_draft'),
  saveActiveDraft: (state: any) => callApi<{ success: boolean }>('save_active_draft', state),
  clearActiveDraft: () => callApi<{ success: boolean }>('clear_active_draft'),
  listSavedDrafts: () => callApi<SavedDraftItem[]>('list_saved_drafts'),
  saveNamedDraft: (name: string, state: any) => callApi<{ success?: boolean; draft_id?: string; error?: string }>('save_named_draft', name, state),
  loadNamedDraft: (draftId: string) => callApi<{ success?: boolean; draft?: any; error?: string }>('load_named_draft', draftId),
  deleteNamedDraft: (draftId: string) => callApi<{ success?: boolean }>('delete_named_draft', draftId),

  // Generation
  startGeneration: (req: { topic: string; outline: string[]; sources: SourceRecord[]; variant: string }) =>
    callApi<{ started?: boolean; error?: string }>('start_generation', req),
  cancelGeneration: () => callApi<{ success: boolean }>('cancel_generation'),

  // Review
  verifyDocument: (sections: Section[], sources: SourceRecord[]) =>
    callApi<SentenceStatus[]>('verify_document', sections, sources),
  paraphraseSentence: (sentence: Sentence, sources: SourceRecord[]) =>
    callApi<{ success?: boolean; sentence?: Sentence; error?: string }>('paraphrase_sentence', sentence, sources),
  requestDosenReview: (sections: Section[], sources: SourceRecord[]) =>
    callApi<{ success?: boolean; notes?: Array<{ section_title: string; sentence_uid: string; severity: string; comment: string }>; error?: string }>('request_dosen_review', sections, sources),
  computeCitations: (sources: SourceRecord[], sections: Section[], style: string) =>
    callApi<{ labels: Record<string, string>; references: string[]; cited_ids: number[] }>('compute_citations_and_references', sources, sections, style),

  // Preflight & Export
  runPreflight: (state: any) =>
    callApi<{ checks: Array<{ label: string; ok: boolean; detail: string }>; issues: Array<{ kind: string; message: string }>; can_export_directly: boolean }>('run_preflight', state),
  exportReport: (state: any) =>
    callApi<{ success?: boolean; output_path?: string; error?: string }>('export_report', state),
};
