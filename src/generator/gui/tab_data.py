"""Tab Data: profil mahasiswa, dosen, mata kuliah, dan logo (Task 13)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..database import Database, Dosen, Logo, MataKuliah, Profil


class _ProfilForm(ttk.Frame):
    """Form satu baris: setiap simpan menimpa profil yang ada."""

    def __init__(self, parent, db: Database):
        super().__init__(parent, padding=12)
        self._db = db
        self._vars = {key: tk.StringVar() for key in ("nama", "nim", "prodi")}
        labels = {"nama": "Nama", "nim": "NIM", "prodi": "Program Studi"}
        for row, key in enumerate(("nama", "nim", "prodi")):
            ttk.Label(self, text=labels[key]).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(self, textvariable=self._vars[key], width=42).grid(row=row, column=1, pady=4)
        ttk.Button(self, text="Simpan", command=self._save).grid(row=3, column=1, sticky="e", pady=10)
        self._status = ttk.Label(self, text="")
        self._status.grid(row=4, column=0, columnspan=2, sticky="w")
        self._load()

    def _load(self) -> None:
        profil = self._db.get_profil()
        self._vars["nama"].set(profil.nama)
        self._vars["nim"].set(profil.nim)
        self._vars["prodi"].set(profil.prodi)

    def _save(self) -> None:
        profil = Profil(
            nama=self._vars["nama"].get().strip(),
            nim=self._vars["nim"].get().strip(),
            prodi=self._vars["prodi"].get().strip(),
        )
        self._db.set_profil(profil)
        self._status.config(text="Profil tersimpan.")


class _CrudPanel(ttk.Frame):
    """Panel umum: listbox + entri + Tambah/Ubah/Hapus untuk satu tabel."""

    def __init__(self, parent, title: str, fields: list[tuple[str, str]], browsable: bool = False):
        super().__init__(parent, padding=12)
        self._fields = fields
        self._browsable = browsable
        self._items: list = []
        self._vars = {key: tk.StringVar() for key, _ in fields}

        # Tombol dan form dikunci lebih dulu ke sisi bawah supaya tidak pernah
        # terpotong saat tinggi jendela kurang; listbox menyerap sisa ruang.
        buttons = ttk.Frame(self)
        buttons.pack(side="bottom", fill="x")
        form = ttk.LabelFrame(self, text="Data")
        form.pack(side="bottom", fill="x", pady=(0, 8))
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            ttk.Entry(form, textvariable=self._vars[key], width=44).grid(row=row, column=1, pady=4)
            if browsable and key == fields[-1][0]:
                ttk.Button(form, text="Pilih berkas...", command=self._browse).grid(
                    row=row, column=2, padx=4
                )
        ttk.Button(buttons, text="Tambah", command=self._add).pack(side="left", padx=4)
        ttk.Button(buttons, text="Ubah", command=self._update).pack(side="left", padx=4)
        ttk.Button(buttons, text="Hapus", command=self._delete).pack(side="left", padx=4)
        self._status = ttk.Label(buttons, text="")
        self._status.pack(side="left", padx=12)

        list_frame = ttk.LabelFrame(self, text=title)
        list_frame.pack(side="top", fill="both", expand=True)
        self._listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        self._listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar = ttk.Scrollbar(list_frame, command=self._listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=scrollbar.set)
        self._listbox.bind("<<ListboxSelect>>", lambda _event: self._on_select())

    # API yang diisi turunan
    def _row_text(self, item) -> str:
        raise NotImplementedError

    def _new_item(self, item_id: int):
        raise NotImplementedError

    def _list(self) -> list:
        raise NotImplementedError

    def _create(self, item) -> int:
        raise NotImplementedError

    def _update(self, item) -> None:
        raise NotImplementedError

    def _delete(self, item_id: int) -> None:
        raise NotImplementedError

    def _browse(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Pilih berkas", filetypes=[("Gambar", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if chosen:
            self._vars[self._fields[-1][0]].set(chosen)

    # Perilaku umum
    def refresh(self) -> None:
        self._items = self._list()
        self._listbox.delete(0, tk.END)
        for item in self._items:
            self._listbox.insert(tk.END, self._row_text(item))
        self._clear_entries()

    def _clear_entries(self) -> None:
        for var in self._vars.values():
            var.set("")

    def _selected(self):
        selection = self._listbox.curselection()
        if not selection:
            return None
        return self._items[selection[0]]

    def _on_select(self) -> None:
        item = self._selected()
        if item is None:
            return
        for key, _ in self._fields:
            self._vars[key].set(getattr(item, key))

    def _add(self) -> None:
        values = [self._vars[key].get().strip() for key, _ in self._fields]
        if not any(values):
            self._status.config(text="Isi minimal satu kolom.")
            return
        self._create(self._new_item(0))
        self._status.config(text="Ditambahkan.")
        self.refresh()

    def _update(self) -> None:
        item = self._selected()
        if item is None:
            self._status.config(text="Pilih baris dulu.")
            return
        for key, _ in self._fields:
            setattr(item, key, self._vars[key].get().strip())
        self._update(item)
        self._status.config(text="Diubah.")
        self.refresh()

    def _delete(self) -> None:
        item = self._selected()
        if item is None:
            self._status.config(text="Pilih baris dulu.")
            return
        self._delete(item.id)
        self._status.config(text="Dihapus.")
        self.refresh()


class _DosenPanel(_CrudPanel):
    def __init__(self, parent, db: Database):
        self._db = db
        super().__init__(parent, "Daftar dosen", [("nama", "Nama"), ("gelar", "Gelar"), ("identitas", "NIDN/NIP")])
        self.refresh()

    def _row_text(self, item) -> str:
        return f"{item.nama} ({item.identitas})"

    def _new_item(self, item_id: int) -> Dosen:
        return Dosen(
            item_id,
            self._vars["nama"].get().strip(),
            self._vars["gelar"].get().strip(),
            self._vars["identitas"].get().strip(),
        )

    def _list(self):
        return self._db.list_dosen()

    def _create(self, item) -> int:
        return self._db.add_dosen(item)

    def _update(self, item) -> None:
        self._db.update_dosen(item)

    def _delete(self, item_id: int) -> None:
        self._db.delete_dosen(item_id)


class _MataKuliahPanel(_CrudPanel):
    def __init__(self, parent, db: Database):
        self._db = db
        super().__init__(parent, "Daftar mata kuliah", [("nama", "Nama"), ("kode", "Kode")])
        self.refresh()

    def _row_text(self, item) -> str:
        return f"{item.kode} - {item.nama}" if item.kode else item.nama

    def _new_item(self, item_id: int) -> MataKuliah:
        return MataKuliah(item_id, self._vars["nama"].get().strip(), self._vars["kode"].get().strip())

    def _list(self):
        return self._db.list_mata_kuliah()

    def _create(self, item) -> int:
        return self._db.add_mata_kuliah(item)

    def _update(self, item) -> None:
        self._db.update_mata_kuliah(item)

    def _delete(self, item_id: int) -> None:
        self._db.delete_mata_kuliah(item_id)


class _LogoPanel(_CrudPanel):
    def __init__(self, parent, db: Database):
        self._db = db
        super().__init__(parent, "Daftar logo", [("nama", "Nama"), ("path", "Berkas")], browsable=True)
        self.refresh()

    def _row_text(self, item) -> str:
        return item.nama

    def _new_item(self, item_id: int) -> Logo:
        return Logo(item_id, self._vars["nama"].get().strip(), self._vars["path"].get().strip())

    def _list(self):
        return self._db.list_logo()

    def _create(self, item) -> int:
        return self._db.add_logo(item)

    def _update(self, item) -> None:
        self._db.update_logo(item)

    def _delete(self, item_id: int) -> None:
        self._db.delete_logo(item_id)


class DataTab(ttk.Frame):
    """Wadah empat sub-tab data."""

    def __init__(self, parent, db: Database):
        super().__init__(parent, padding=8)
        self._db = db
        inner = ttk.Notebook(self)
        inner.pack(fill="both", expand=True)
        inner.add(_ProfilForm(inner, db), text="Profil Mahasiswa")
        inner.add(_DosenPanel(inner, db), text="Dosen")
        inner.add(_MataKuliahPanel(inner, db), text="Mata Kuliah")
        inner.add(_LogoPanel(inner, db), text="Logo")
