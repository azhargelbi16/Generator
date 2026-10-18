"""Cangkang aplikasi: Notebook dengan tab Data, Template, Laporan, dan Pengaturan (Task 13).

Modul ini aman diimpor tanpa membuat jendela; Tk hanya dibuat di `build_app()`.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config, database, logging_setup, paths


class _PlaceholderTab(ttk.Frame):
    """Tab yang isinya menyusul di task berikutnya."""

    def __init__(self, parent, label: str):
        super().__init__(parent, padding=12)
        ttk.Label(self, text=f"Tab {label} menyusul pada task berikutnya.").pack(anchor="w")


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
    # Sesuaikan tinggi jendela dengan layar agar tombol di bagian bawah tidak
    # pernah terpotong taskbar pada layar kecil atau scaling tinggi.
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    width = min(980, int(screen_w * 0.9))
    height = min(640, int(screen_h * 0.82))
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 3)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(720, 420)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    from . import tab_data  # import bertahap; tab lain mengikuti di task berikutnya

    notebook.add(tab_data.DataTab(notebook, db), text="Data")
    notebook.add(_PlaceholderTab(notebook, "Template"), text="Template")
    notebook.add(_PlaceholderTab(notebook, "Laporan"), text="Laporan")
    notebook.add(_PlaceholderTab(notebook, "Pengaturan"), text="Pengaturan")

    hint = "API key belum diisi; buka tab Pengaturan nanti setelah tab tersebut tersedia."
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
