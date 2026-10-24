/**
 * Formal API Contract between Frontend (React) and Backend (pywebview Python)
 * API Version: 2.0.0
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
  Paragraph,
  SentenceStatus,
  FormatVariant,
  DocumentAnalytics,
  SavedDraftItem,
} from './api';

export const API_VERSION = "2.0.0";

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
  list_templates(): Promise<TemplateItem[]>;
  upload_template(): Promise<{ success: boolean; template?: TemplateItem; error?: string }>;
  delete_template(id: number): Promise<{ success: boolean }>;
  open_template(id: number): Promise<{ success: boolean; error?: string }>;
  open_templates_folder(): Promise<{ success: boolean; error?: string }>;
  create_default_template(): Promise<{ success: boolean; template?: TemplateItem; error?: string }>;

  // Source Ingestion
  pick_pdf_source(): Promise<{ success: boolean; source?: SourceRecord; error?: string }>;
  add_web_source(url: string): Promise<{ success: boolean; source?: SourceRecord; error?: string }>;
  resolve_doi_source(doi: string): Promise<{ success: boolean; source?: SourceRecord; error?: string }>;
  add_manual_source(data: SourceRecord): Promise<{ success: boolean; source: SourceRecord }>;

  // Generation & Report
  get_format_variants(): Promise<FormatVariant[]>;
  suggest_outline(topic: string, sources: SourceRecord[]): Promise<{ success: boolean; outline: string[]; error?: string }>;
  generate_title_from_sources(sources: SourceRecord[]): Promise<{ success: boolean; title: string; error?: string }>;
  start_generation(topic: string, outline: string[], sources: SourceRecord[], variant?: string): Promise<{ success: boolean; error?: string }>;
  cancel_generation(): Promise<{ success: boolean }>;
  compute_citations_and_references(sources: SourceRecord[]): Promise<{ success: boolean; labels: Record<number, string>; references: string[] }>;
  verify_document(sources: SourceRecord[], sections: Section[]): Promise<{ success: boolean; statuses: Record<string, SentenceStatus> }>;
  paraphrase_sentence(sources: SourceRecord[], paragraph: Paragraph): Promise<{ success: boolean; paragraph: Paragraph; error?: string }>;
  request_dosen_review(topic: string, sections: Section[]): Promise<{ success: boolean; review: string; error?: string }>;
  export_report(data: ExportReportPayload): Promise<{ success: boolean; output_path: string; error?: string }>;
  get_document_analytics(sections: Section[], sources: SourceRecord[]): Promise<{ success: boolean; analytics: DocumentAnalytics }>;
  open_output_folder(): Promise<{ success: boolean; path: string; error?: string }>;
  run_preflight(data: any): Promise<{ success: boolean; passed: boolean; issues: string[] }>;

  // Drafts
  load_active_draft(): Promise<DraftStatePayload | null>;
  save_active_draft(state: DraftStatePayload): Promise<{ success: boolean }>;
  clear_active_draft(): Promise<{ success: boolean }>;
  list_saved_drafts(): Promise<SavedDraftItem[]>;
  save_named_draft(draftId: string, state: DraftStatePayload): Promise<{ success: boolean; error?: string }>;
  load_named_draft(draftId: string): Promise<DraftStatePayload | null>;
  delete_named_draft(draftId: string): Promise<{ success: boolean }>;
}
