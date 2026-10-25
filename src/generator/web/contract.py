"""Definisi kontrak formal API pywebview antara Python backend dan React frontend."""

from __future__ import annotations

from typing import Any, Dict

API_VERSION = "2.0.0"

API_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "get_api_version": {
        "description": "Mengembalikan nomor versi API backend",
        "params": [],
        "returns": "string",
    },
    "get_api_contract": {
        "description": "Mengembalikan metadata lengkap kontrak API",
        "params": [],
        "returns": "object",
    },
    # Config & AI
    "get_config": {
        "description": "Membaca konfigurasi aplikasi saat ini",
        "params": [],
        "returns": "AppConfig",
    },
    "save_config": {
        "description": "Menyimpan preferensi konfigurasi aplikasi",
        "params": [{"name": "cfg", "type": "Partial<AppConfig>"}],
        "returns": "{ success: boolean, error?: string }",
    },
    "test_ai_connection": {
        "description": "Menguji koneksi ke endpoint LLM",
        "params": [
            {"name": "base_url", "type": "string", "optional": True},
            {"name": "api_key", "type": "string", "optional": True},
            {"name": "model", "type": "string", "optional": True},
        ],
        "returns": "{ ok: boolean, message: string }",
    },
    "fetch_models": {
        "description": "Mengambil daftar model yang tersedia dari endpoint AI",
        "params": [
            {"name": "base_url", "type": "string", "optional": True},
            {"name": "api_key", "type": "string", "optional": True},
        ],
        "returns": "{ ok: boolean, models: string[], error?: string }",
    },
    # Profile & Academic Master Data
    "get_profile": {
        "description": "Mendapatkan profil mahasiswa",
        "params": [],
        "returns": "Profile",
    },
    "save_profile": {
        "description": "Menyimpan profil mahasiswa",
        "params": [{"name": "profile", "type": "Profile"}],
        "returns": "{ success: boolean }",
    },
    "list_dosen": {
        "description": "Daftar dosen pembimbing",
        "params": [],
        "returns": "Dosen[]",
    },
    "add_dosen": {
        "description": "Menambah dosen baru",
        "params": [{"name": "data", "type": "Dosen"}],
        "returns": "{ success: boolean, id?: number }",
    },
    "update_dosen": {
        "description": "Memperbarui data dosen",
        "params": [{"name": "data", "type": "Dosen"}],
        "returns": "{ success: boolean }",
    },
    "delete_dosen": {
        "description": "Menghapus dosen",
        "params": [{"name": "id", "type": "number"}],
        "returns": "{ success: boolean }",
    },
    "list_matkul": {
        "description": "Daftar mata kuliah",
        "params": [],
        "returns": "MataKuliah[]",
    },
    "add_matkul": {
        "description": "Menambah mata kuliah baru",
        "params": [{"name": "data", "type": "MataKuliah"}],
        "returns": "{ success: boolean, id?: number }",
    },
    "update_matkul": {
        "description": "Memperbarui mata kuliah",
        "params": [{"name": "data", "type": "MataKuliah"}],
        "returns": "{ success: boolean }",
    },
    "delete_matkul": {
        "description": "Menghapus mata kuliah",
        "params": [{"name": "id", "type": "number"}],
        "returns": "{ success: boolean }",
    },
    "list_logos": {
        "description": "Daftar logo institusi",
        "params": [],
        "returns": "Logo[]",
    },
    "upload_logo": {
        "description": "Mengunggah logo via dialog file",
        "params": [],
        "returns": "{ success: boolean, logo?: Logo, error?: string }",
    },
    "delete_logo": {
        "description": "Menghapus logo",
        "params": [{"name": "id", "type": "number"}],
        "returns": "{ success: boolean }",
    },
    "list_templates": {
        "description": "Daftar template dokumen",
        "params": [],
        "returns": "TemplateItem[]",
    },
    "upload_template": {
        "description": "Mengunggah file DOCX template",
        "params": [],
        "returns": "{ success: boolean, template?: TemplateItem, error?: string }",
    },
    "delete_template": {
        "description": "Menghapus template",
        "params": [{"name": "id", "type": "number"}],
        "returns": "{ success: boolean }",
    },
    "open_template": {
        "description": "Membuka template di Microsoft Word",
        "params": [{"name": "id", "type": "number"}],
        "returns": "{ success: boolean, error?: string }",
    },
    "open_templates_folder": {
        "description": "Membuka folder template di File Explorer",
        "params": [],
        "returns": "{ success: boolean, error?: string }",
    },
    "create_default_template": {
        "description": "Menghasilkan template standar akademik",
        "params": [],
        "returns": "{ success: boolean, template?: TemplateItem, error?: string }",
    },
    # Sources
    "pick_pdf_source": {
        "description": "Membaca file PDF dan mengekstrak teks serta metadata",
        "params": [],
        "returns": "{ success: boolean, record?: SourceRecord, error?: string }",
    },
    "add_web_source": {
        "description": "Mengunduh artikel web dari URL",
        "params": [{"name": "url", "type": "string"}],
        "returns": "{ success: boolean, record?: SourceRecord, error?: string }",
    },
    "resolve_doi_source": {
        "description": "Mengambil metadata publikasi ilmiah via DOI",
        "params": [{"name": "doi", "type": "string"}],
        "returns": "{ success: boolean, record?: SourceRecord, error?: string }",
    },
    "add_manual_source": {
        "description": "Menambah catatan sumber manual (teks mentah; DOI di dalam teks diresolusi cepat)",
        "params": [{"name": "text", "type": "string"}],
        "returns": "{ success: boolean, record?: SourceRecord, error?: string }",
    },
    # Generation & Report
    "get_format_variants": {
        "description": "Mendapatkan pilihan format varian Dikti (A/B/C/Bebas)",
        "params": [],
        "returns": "FormatVariant[]",
    },
    "suggest_outline": {
        "description": "Mengusulkan bab-bab laporan dari AI berdasarkan sumber",
        "params": [
            {"name": "topic", "type": "string"},
            {"name": "sources", "type": "SourceRecord[]"},
        ],
        "returns": "{ success: boolean, outline: string[], error?: string }",
    },
    "generate_title_from_sources": {
        "description": "Menghasilkan usulan judul otomatis",
        "params": [{"name": "sources", "type": "SourceRecord[]"}],
        "returns": "{ success: boolean, title: string, error?: string }",
    },
    "start_generation": {
        "description": "Memulai penulisan laporan secara streaming (thread latar; progres via event gen_*)",
        "params": [
            {"name": "request_data", "type": "{ topic: string, outline: string[], sources: SourceRecord[], variant?: string }"},
        ],
        "returns": "{ started: boolean } | { error: string }",
    },
    "cancel_generation": {
        "description": "Membatalkan proses penulisan laporan",
        "params": [],
        "returns": "{ success: boolean }",
    },
    "compute_citations_and_references": {
        "description": "Menghitung label sitasi in-text dan daftar pustaka APA 7",
        "params": [
            {"name": "sources_data", "type": "SourceRecord[]"},
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "style", "type": "string", "optional": True},
        ],
        "returns": "{ labels: Record<string, string>, label_forms: Record<string, [string, string]>, references: string[], cited_ids: number[] }",
    },
    "verify_document": {
        "description": "Memverifikasi klaim faktual tiap kalimat terhadap sumber",
        "params": [
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "sources_data", "type": "SourceRecord[]"},
        ],
        "returns": "Array<{ index: number, uid: string, status: string, reason: string, is_factual: boolean, source_ids: number[] }>",
    },
    "paraphrase_sentence": {
        "description": "Memparafrase satu kalimat dengan menjaga sitasi",
        "params": [
            {"name": "sentence_dict", "type": "Sentence"},
            {"name": "sources_data", "type": "SourceRecord[]"},
        ],
        "returns": "{ success: boolean, sentence?: Sentence, error?: string }",
    },
    "request_dosen_review": {
        "description": "Menjalankan evaluasi persona dosen pembimbing",
        "params": [
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "sources_data", "type": "SourceRecord[]"},
        ],
        "returns": "{ success: boolean, notes: DosenNote[], error?: string }",
    },
    "export_report": {
        "description": "Merender dan mengekspor dokumen DOCX",
        "params": [{"name": "data", "type": "object"}],
        "returns": "{ success: boolean, output_path: string, error?: string }",
    },
    "get_document_analytics": {
        "description": "Menganalisis statistik, readability, dan sebaran kata dokumen",
        "params": [
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "sources_data", "type": "SourceRecord[]"},
        ],
        "returns": "DocumentAnalytics",
    },
    "open_output_folder": {
        "description": "Membuka folder output di File Explorer",
        "params": [],
        "returns": "{ success: boolean, error?: string }",
    },
    "run_preflight": {
        "description": "Memeriksa kesiapan data sebelum ekspor dokumen",
        "params": [
            {"name": "state", "type": "{ sources: SourceRecord[], sections: Section[], done: string[], fields: Record<string, string> }"},
        ],
        "returns": "{ checks: PreflightCheck[], issues: PreflightIssue[], can_export_directly: boolean }",
    },
    "mark_non_factual_done": {
        "description": "Tandai semua kalimat bukan-klaim faktual sebagai selesai",
        "params": [
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "current_done", "type": "string[]"},
        ],
        "returns": "{ success: boolean, done: string[] }",
    },
    "get_reviewed_snapshot": {
        "description": "Satu panggilan untuk layar review: status kalimat + sitasi + analitik",
        "params": [
            {"name": "sections_dicts", "type": "Section[]"},
            {"name": "sources_data", "type": "SourceRecord[]"},
            {"name": "style", "type": "string", "optional": True},
        ],
        "returns": "{ statuses: SentenceStatusPayload[], citations: CitationPayload, analytics: DocumentAnalytics }",
    },
    # Drafts
    "load_active_draft": {
        "description": "Memuat draf aktif terakhir",
        "params": [],
        "returns": "{ has_draft: boolean, draft_id?: string, fields: Record<string, string>, sources: SourceRecord[], sections: Section[], done: string[] }",
    },
    "save_active_draft": {
        "description": "Menyimpan autosave draf aktif",
        "params": [{"name": "state", "type": "DraftState"}],
        "returns": "{ success: boolean }",
    },
    "clear_active_draft": {
        "description": "Menghapus draf aktif",
        "params": [],
        "returns": "{ success: boolean }",
    },
    "list_saved_drafts": {
        "description": "Daftar riwayat draf tersimpan",
        "params": [],
        "returns": "SavedDraftItem[]",
    },
    "save_named_draft": {
        "description": "Menyimpan draf dengan nama tertentu",
        "params": [
            {"name": "draft_id", "type": "string"},
            {"name": "state", "type": "DraftState"},
        ],
        "returns": "{ success: boolean, error?: string }",
    },
    "load_named_draft": {
        "description": "Memuat draf tertentu berdasarkan ID",
        "params": [{"name": "draft_id", "type": "string"}],
        "returns": "DraftState | null",
    },
    "delete_named_draft": {
        "description": "Menghapus draf dari disk",
        "params": [{"name": "draft_id", "type": "string"}],
        "returns": "{ success: boolean }",
    },
}


def get_contract_metadata() -> Dict[str, Any]:
    """Mengembalikan payload kontrak API untuk dikonsumsi klien."""
    return {
        "version": API_VERSION,
        "total_endpoints": len(API_ENDPOINTS),
        "endpoints": API_ENDPOINTS,
    }

