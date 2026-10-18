"""Tab Kelola Template: unggah DOCX, validasi penanda, hapus (9.3, putaran 6).

Status validasi tidak pernah disimpan di database; ia dihitung ulang dari
berkas setiap kali daftar ditampilkan.
"""

from __future__ import annotations

import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import paths
from ..database import Database, Template
from ..document.template import TemplateError, validate_template


class TemplateTab(ttk.Frame):
    """Daftar template dengan status validasi hitung-ulang, Tambah, dan Hapus."""

    def __init__(self, parent, db: Database):
        super().__init__(parent, padding=12)
        self._db = db

        buttons = ttk.Frame(self)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="Tambah template (.docx)...", command=self._add).pack(
            side="left", padx=4
        )
        ttk.Button(buttons, text="Hapus", command=self._delete).pack(side="left", padx=4)
        self._status = ttk.Label(buttons, text="")
        self._status.pack(side="left", padx=12)

        list_frame = ttk.LabelFrame(self, text="Daftar template")
        list_frame.pack(side="top", fill="both", expand=True)
        self._listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        self._listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar = ttk.Scrollbar(list_frame, command=self._listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=scrollbar.set)

        self._items: list[Template] = []
        self.refresh()

    def refresh(self) -> None:
        """Baca ulang daftar dan hitung status validasi dari berkasnya."""
        self._listbox.delete(0, "end")
        self._items = self._db.list_template()
        for item in self._items:
            self._listbox.insert("end", f"{item.nama}  —  {self._status_text(item)}")

    def _status_text(self, item: Template) -> str:
        path = Path(item.path)
        if not path.is_file():
            return "berkas hilang"
        try:
            result = validate_template(path)
        except TemplateError:
            return "rusak atau bukan .docx valid"
        problems = []
        if result.missing:
            problems.append(f"kurang {len(result.missing)} penanda wajib")
        if result.not_standalone:
            problems.append(f"{len(result.not_standalone)} penanda tidak berdiri sendiri")
        if result.unknown:
            problems.append(f"penanda tak dikenal: {', '.join(result.unknown)}")
        if not problems:
            return "lengkap"
        return "tidak lengkap (" + "; ".join(problems) + ")"

    def _add(self) -> None:
        src = filedialog.askopenfilename(
            title="Pilih berkas template",
            filetypes=[("Dokumen Word", "*.docx"), ("Semua berkas", "*.*")],
        )
        if not src:
            return
        self._import_template(Path(src))

    def _import_template(self, src: Path, nama: str | None = None, deskripsi: str = "") -> bool:
        """Validasi, salin ke folder template, dan simpan metadata. Soket dialog
        metadata dilewatkan lewat argumen agar bisa diuji tanpa dialog."""
        try:
            result = validate_template(src)
        except TemplateError as error:
            messagebox.showerror("Template tidak valid", str(error))
            return False

        if result.missing or result.not_standalone or result.unknown:
            lines = []
            if result.missing:
                lines.append("Penanda wajib yang kurang: " + ", ".join(result.missing))
            if result.not_standalone:
                lines.append(
                    "Penanda khusus yang tidak berdiri sendiri: "
                    + ", ".join(result.not_standalone)
                )
            if result.unknown:
                lines.append("Penanda tak dikenal: " + ", ".join(result.unknown))
            lines.append("Template tetap disimpan dengan status tidak lengkap.")
            messagebox.showwarning("Template tidak lengkap", "\n".join(lines))

        if nama is None:
            asked = self._ask_metadata(src.stem)
            if asked is None:
                return False
            nama, deskripsi = asked

        target = self._copy_into_templates_dir(src)
        if target is None:
            return False
        self._db.add_template(Template(0, nama.strip(), deskripsi.strip(), str(target)))
        self.refresh()
        self._status.config(text=f"Template '{nama.strip()}' disimpan.")
        return True

    def _copy_into_templates_dir(self, src: Path) -> Path | None:
        paths.ensure_dirs()
        target = paths.TEMPLATES_DIR / src.name
        counter = 1
        while target.exists():
            target = paths.TEMPLATES_DIR / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        try:
            shutil.copy2(src, target)
        except OSError as error:
            messagebox.showerror("Gagal menyalin", f"Berkas template tidak bisa disalin: {error}")
            return None
        return target

    def _ask_metadata(self, default_nama: str) -> tuple[str, str] | None:
        """Dialog kecil untuk nama dan deskripsi; kembalikan None bila dibatalkan."""
        dialog = tk.Toplevel(self)
        dialog.title("Metadata template")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        nama_var = tk.StringVar(value=default_nama)
        deskripsi_var = tk.StringVar()
        ttk.Label(dialog, text="Nama:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(dialog, textvariable=nama_var, width=44).grid(row=0, column=1, padx=8, pady=4)
        ttk.Label(dialog, text="Deskripsi:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(dialog, textvariable=deskripsi_var, width=44).grid(row=1, column=1, padx=8, pady=4)

        chosen: list[tuple[str, str] | None] = [None]

        def confirm() -> None:
            chosen[0] = (nama_var.get().strip(), deskripsi_var.get().strip())
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=confirm).grid(row=2, column=0, columnspan=2, pady=8)
        dialog.wait_window()
        if not chosen[0] or not chosen[0][0]:
            return None
        return chosen[0]

    def _delete(self) -> None:
        selection = self._listbox.curselection()
        if not selection:
            self._status.config(text="Pilih template yang akan dihapus.")
            return
        item = self._items[selection[0]]
        if not messagebox.askyesno(
            "Hapus template", f"Hapus template '{item.nama}' dari daftar?"
        ):
            return
        self._db.delete_template(item.id)
        self.refresh()
        self._status.config(text=f"Template '{item.nama}' dihapus.")
