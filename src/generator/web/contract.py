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
        "returns": "{ success: boolean, source?: SourceRecord, error?: string }",
    },
    "add_web_source": {
        "description": "Mengunduh artikel web dari URL",
        "params": [{"name": "url", "type": "string"}],
        "returns": "{ success: boolean, source?: SourceRecord, error?: string }",
    },
    "resolve_doi_source": {
        "description": "Mengambil metadata publikasi ilmiah via DOI",
        "params": [{"name": "doi", "type": "string"}],
        "returns": "{ success: boolean, source?: SourceRecord, error?: string }",
    },
    "add_manual_source": {
        "description": "Menambah catatan sumber manual",
        "params": [{"name": "data", "type": "SourceRecord"}],
        "returns": "{ success: boolean, source: SourceRecord }",
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
        "description": "Memulai penulisan laporan secara streaming",
        "params": [
            {"name": "topic", "type": "string"},
            {"name": "outline", "type": "string[]"},
            {"name": "sources", "type": "SourceRecord[]"},
            {"name": "variant", "type": "string", "optional": True},
        ],
        "returns": "{ success: boolean, error?: string }",
    },
    "cancel_generation": {
        "description": "Membatalkan proses penulisan laporan",
        "params": [],
        "returns": "{ success: boolean }",
    },
    "compute_citations_and_references": {
        "description": "Menghitung label sitasi in-text dan daftar pustaka APA 7",
        "params": [{"name": "sources", "type": "SourceRecord[]"}],
        "returns": "{ success: boolean, labels: Record<number, string>, references: string[] }",
    },
    "verify_document": {
        "description": "Memverifikasi klaim faktual tiap kalimat terhadap sumber",
        "params": [
            {"name": "sources", "type": "SourceRecord[]"},
            {"name": "sections", "type": "Section[]"},
        ],
        "returns": "{ success: boolean, statuses: Record<string, SentenceStatus> }",
    },
    "paraphrase_sentence": {
        "description": "Memparafrase satu paragraf kalimat",
        "params": [
            {"name": "sources", "type": "SourceRecord[]"},
            {"name": "paragraph", "type": "Paragraph"},
        ],
        "returns": "{ success: boolean, paragraph: Paragraph, error?: string }",
    },
    "request_dosen_review": {
        "description": "Menjalankan evaluasi persona dosen pembimbing",
        "params": [
            {"name": "topic", "type": "string"},
            {"name": "sections", "type": "Section[]"},
        ],
        "returns": "{ success: boolean, review: string, error?: string }",
    },
    "export_report": {
        "description": "Merender dan mengekspor dokumen DOCX",
        "params": [{"name": "data", "type": "object"}],
        "returns": "{ success: boolean, output_path: string, error?: string }",
    },
    "get_document_analytics": {
        "description": "Menganalisis statistik, readability, dan sebaran kata dokumen",
        "params": [
            {"name": "sections", "type": "Section[]"},
            {"name": "sources", "type": "SourceRecord[]"},
        ],
        "returns": "{ success: boolean, analytics: DocumentAnalytics }",
    },
    "open_output_folder": {
        "description": "Membuka folder output di File Explorer",
        "params": [],
        "returns": "{ success: boolean, path: string, error?: string }",
    },
    "run_preflight": {
        "description": "Memeriksa kesiapan data sebelum ekspor dokumen",
        "params": [{"name": "data", "type": "object"}],
        "returns": "{ success: boolean, passed: boolean, issues: string[] }",
    },
    # Drafts
    "load_active_draft": {
        "description": "Memuat draf aktif terakhir",
        "params": [],
        "returns": "DraftState | null",
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

