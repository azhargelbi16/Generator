"""Cangkang aplikasi: Notebook dengan tab Data, Template, Laporan, dan Pengaturan (Task 13).

Modul ini aman diimpor tanpa membuat jendela; Tk hanya dibuat di `build_app()`.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config, database, logging_setup, paths


def _ensure_dirs_or_ask() -> bool:
    """Siapkan folder data; bila gagal, minta user memilih folder lain (12.8)."""
    try:
        paths.ensure_dirs()
        return True
    except paths.PathsError:
        pass
    root = tk.Tk()
    root.withdraw()
    chosen = filedialog.askdirectory(
        title="Folder data bawaan tidak bisa ditulis. Pilih folder penyimpanan data."
    )
    root.destroy()
    if not chosen:
        return False
    try:
        paths.set_data_dir(chosen)
        paths.ensure_dirs()
    except paths.PathsError:
        return False
    return True


def _show_startup_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Generator Laporan", message)
    root.destroy()


def build_app() -> tk.Tk | None:
    """Bangun jendela utama; kembalikan None bila startup dibatalkan user."""
    if not _ensure_dirs_or_ask():
        _show_startup_error("Folder data tidak tersedia. Aplikasi berhenti.")
        return None
    logging_setup.setup_logging(paths.LOG_PATH)

    db = database.Database(paths.DB_PATH)
    db.init_schema()

    app_config = config.load_config(paths.CONFIG_PATH)

    root = tk.Tk()
    root.title("Generator Laporan")
    import sv_ttk

    from .feedback import siapkan_gaya

    sv_ttk.set_theme("light", root)
    siapkan_gaya(root)
    # Sesuaikan tinggi jendela dengan layar agar tombol di bagian bawah tidak
    # pernah terpotong taskbar pada layar kecil atau scaling tinggi.
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    width = min(980, int(screen_w * 0.9))
    height = min(720, int(screen_h * 0.92))
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 3)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(720, 420)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    from . import tab_data, tab_report, tab_settings, tab_template

    notebook.add(tab_data.DataTab(notebook, db), text="Data")
    notebook.add(tab_template.TemplateTab(notebook, db), text="Template")
    laporan_setup = ttk.Frame(notebook)
    laporan_review = ttk.Frame(notebook)
    notebook.add(laporan_setup, text="Laporan")
    notebook.add(laporan_review, text="Review Hasil")
    pengendali = tab_report.ReportController(laporan_setup, laporan_review, notebook, db)
    laporan_setup.controller = pengendali
    laporan_review.controller = pengendali
    notebook.add(tab_settings.SettingsTab(notebook, paths.CONFIG_PATH), text="Pengaturan")

    hint = "API key belum diisi; buka tab Pengaturan untuk mengisi endpoint dan API key."
    if not app_config.ai_api_key:
        status = tk.Label(root, text=hint, fg="#8a6d3b", anchor="w")
        status.pack(fill="x", side="bottom")

    def _close() -> None:
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _close)
    return root


def main() -> None:
    root = build_app()
    if root is None:
        return
    root.mainloop()


if __name__ == "__main__":
    main()
