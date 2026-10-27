/**
 * Formal API Contract between Frontend (React) and Backend (pywebview Python)
 * API Version: 2.0.0
 *
 * Diselaraskan (slice arsitektur 5) dengan tanda tangan & amplop respons
 * AKTUAL dari ApiBridge (lihat src/generator/web/contract.py) — bukan bentuk
 * yang diharapkan. Perubahan kunci vs versi lama:
 * - Sumber: kunci respons adalah `record` (bukan `source`); add_manual_source
 *   menerima `text: string`.
 * - start_generation menerima SATU objek request; progres lewat event gen_*.
 * - verify_document mengembalikan ARRAY status (bukan map), urutan argumen
 *   (sections, sources).
 * - compute_citations_and_references: labels berkunci string + label_forms +
 *   cited_ids; get_document_analytics mengembalikan analitik langsung.
 * - run_preflight: { checks, issues, can_export_directly }.
 * - load_active_draft: { has_draft, ... }.
 */

import type {
  AppConfig,
  Profile,
  Dosen,
  MataKuliah,
  Logo,
  TemplateItem,
  SourceRecord,
  Section,
  Sentence,
  SentenceStatus,
  FormatVariant,
  DocumentAnalytics,
  SavedDraftItem,
} from './api';

export const API_VERSION = "2.0.0";

/** Status payload persis seperti verify_document backend. */
export type SentenceStatusPayload = SentenceStatus & { reason: string };

/** Amplop sitasi dari compute_citations_and_references / snapshot. */
export interface CitationPayload {
  labels: Record<string, string>;
  label_forms: Record<string, [string, string]>;
  references: string[];
  cited_ids: number[];
}

export interface PreflightCheck {
  label: string;
  ok: boolean;
  detail: string;
}

export interface PreflightIssue {
  kind: string;
  message: string;
}

export interface DosenNote {
  section_title: string;
  sentence_uid: string;
  severity: string;
  comment: string;
}

export interface ActiveDraftPayload {
  has_draft: boolean;
  draft_id?: string;
  fields: Record<string, string>;
  sources: SourceRecord[];
  sections: Section[];
  done: string[];
}

export interface DraftStatePayload {
  draft_id?: string;
  fields: Record<string, string>;
  sources: SourceRecord[];
  sections: Section[];
  done?: string[];
}

export interface ExportReportPayload {
  sources: SourceRecord[];
  sections: any[];
  fields: Record<string, string>;
  template_id?: number | null;
  open_word?: boolean;
}

export interface ApiContractMetadata {
  version: string;
  total_endpoints: number;
  endpoints: Record<string, {
    description: string;
    params: Array<{ name: string; type: string; optional?: boolean }>;
    returns: string;
  }>;
}

export interface PyWebViewApiContract {
  // Versioning & Contract
  get_api_version(): Promise<string>;
  get_api_contract(): Promise<ApiContractMetadata>;

  // Configuration
  get_config(): Promise<AppConfig>;
  save_config(cfg: Partial<AppConfig>): Promise<{ success: boolean; error?: string }>;
  test_ai_connection(baseUrl?: string, apiKey?: string, model?: string): Promise<{ ok: boolean; message: string }>;
  fetch_models(baseUrl?: string, apiKey?: string): Promise<{ ok: boolean; models: string[]; error?: string }>;

  // Master Data & Academic
  get_profile(): Promise<Profile>;
  save_profile(profile: Profile): Promise<{ success: boolean }>;
  list_dosen(): Promise<Dosen[]>;
  add_dosen(data: Dosen): Promise<{ success: boolean; id?: number }>;
  update_dosen(data: Dosen): Promise<{ success: boolean }>;
  delete_dosen(id: number): Promise<{ success: boolean }>;
  list_matkul(): Promise<MataKuliah[]>;
  add_matkul(data: MataKuliah): Promise<{ success: boolean; id?: number }>;
  update_matkul(data: MataKuliah): Promise<{ success: boolean }>;
  delete_matkul(id: number): Promise<{ success: boolean }>;
  list_logos(): Promise<Logo[]>;
  upload_logo(): Promise<{ success: boolean; logo?: Logo; error?: string }>;
  delete_logo(id: number): Promise<{ success: boolean }>;
  open_logos_folder(): Promise<{ success?: boolean; error?: string }>;
  list_templates(): Promise<TemplateItem[]>;
  upload_template(): Promise<{ success: boolean; template?: TemplateItem; error?: string }>;
  delete_template(id: number): Promise<{ success: boolean }>;
  open_template(id: number): Promise<{ success: boolean; error?: string }>;
  open_templates_folder(): Promise<{ success: boolean; error?: string }>;
  create_default_template(): Promise<{ success: boolean; template?: TemplateItem; error?: string }>;

  // Source Ingestion — kunci `record` sesuai backend
  pick_pdf_source(): Promise<{
    success: boolean;
    record?: SourceRecord;
    records?: SourceRecord[];
    errors?: string[];
    count?: number;
    warning?: string;
    error?: string;
    cancelled?: boolean;
  }>;
  add_web_source(url: string): Promise<{ success: boolean; record?: SourceRecord; error?: string }>;
  resolve_doi_source(doi: string): Promise<{ success: boolean; record?: SourceRecord; error?: string }>;
  add_manual_source(text: string): Promise<{ success: boolean; record?: SourceRecord; error?: string }>;

  // Generation & Report
  get_format_variants(): Promise<FormatVariant[]>;
  suggest_outline(topic: string, sources: SourceRecord[]): Promise<{ success: boolean; outline?: string[]; error?: string }>;
  generate_title_from_sources(sources: SourceRecord[]): Promise<{ success: boolean; title?: string; error?: string }>;
  start_generation(request: { topic: string; outline: string[]; sources: SourceRecord[]; variant?: string }): Promise<{ started?: boolean; error?: string }>;
  cancel_generation(): Promise<{ success: boolean }>;
  compute_citations_and_references(sources: SourceRecord[], sections: Section[], style?: string): Promise<CitationPayload>;
  verify_document(sections: Section[], sources: SourceRecord[]): Promise<SentenceStatusPayload[]>;
  paraphrase_sentence(sentence: Sentence, sources: SourceRecord[]): Promise<{ success: boolean; sentence?: Sentence; error?: string }>;
  request_dosen_review(sections: Section[], sources: SourceRecord[]): Promise<{ success: boolean; notes?: DosenNote[]; error?: string }>;
  export_report(state: ExportReportPayload): Promise<{ success: boolean; output_path?: string; error?: string }>;
  get_document_analytics(sections: Section[], sources: SourceRecord[]): Promise<DocumentAnalytics>;
  open_output_folder(): Promise<{ success: boolean; error?: string }>;
  run_preflight(state: { sources: SourceRecord[]; sections: Section[]; done: string[]; fields: Record<string, string> }): Promise<{ checks: PreflightCheck[]; issues: PreflightIssue[]; can_export_directly: boolean }>;
  get_reviewed_snapshot(sections: Section[], sources: SourceRecord[], style?: string): Promise<{ statuses: SentenceStatusPayload[]; citations: CitationPayload; analytics: DocumentAnalytics }>;
  mark_non_factual_done(sections: Section[], currentDone: string[]): Promise<{ success: boolean; done: string[] }>;

  // Drafts
  load_active_draft(): Promise<ActiveDraftPayload>;
  save_active_draft(state: DraftStatePayload): Promise<{ success: boolean }>;
  clear_active_draft(): Promise<{ success: boolean }>;
  list_saved_drafts(): Promise<SavedDraftItem[]>;
  save_named_draft(draftId: string, state: DraftStatePayload): Promise<{ success: boolean; error?: string }>;
  load_named_draft(draftId: string): Promise<DraftStatePayload | null>;
  delete_named_draft(draftId: string): Promise<{ success: boolean }>;
  delete_named_drafts(draftIds: string[]): Promise<{ success: boolean }>;
}
