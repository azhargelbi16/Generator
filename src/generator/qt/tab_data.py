"""Tab Data Qt: profil mahasiswa, dosen, mata kuliah, dan logo (parity gui/tab_data.py).

Baru dibanding Tk: daftar sebagai QTableWidget dengan QLineEdit filter
real-time, dan pratinjau logo langsung (QLabel + QPixmap).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from ..database import Database, Dosen, Logo, MataKuliah, Profil

_PREVIEW_MAX = (200, 150)


class _ProfilForm(QWidget):
    """Form satu baris: setiap simpan menimpa profil yang ada."""

    def __init__(self, db: Database):
        super().__init__()
        self._db = db
        self._vars = {key: QLineEdit() for key in ("nama", "nim", "prodi")}
        labels = {"nama": "Nama", "nim": "NIM", "prodi": "Program Studi"}
        form = QFormLayout()
        for key in ("nama", "nim", "prodi"):
            form.addRow(labels[key], self._vars[key])
        save = QPushButton("Simpan")
        save.clicked.connect(self._save)
        form.addRow(save)
        self._status = QLabel("")
        form.addRow(self._status)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)
        self._load()

    def _load(self) -> None:
        profil = self._db.get_profil()
        self._vars["nama"].setText(profil.nama)
        self._vars["nim"].setText(profil.nim)
        self._vars["prodi"].setText(profil.prodi)

    def _save(self) -> None:
        profil = Profil(
            nama=self._vars["nama"].text().strip(),
            nim=self._vars["nim"].text().strip(),
            prodi=self._vars["prodi"].text().strip(),
        )
        self._db.set_profil(profil)
        self._status.setText("Profil tersimpan.")


class _CrudPanel(QWidget):
    """Panel umum: tabel + filter + entri + Tambah/Ubah/Hapus untuk satu tabel."""

    def __init__(self, title: str, fields: list[tuple[str, str]], browsable: bool = False):
        super().__init__()
        self._fields = fields
        self._browsable = browsable
        self._items: list = []
        self._vars = {key: QLineEdit() for key, _ in fields}

        layout = QVBoxLayout(self)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Cari...")
        self._filter.setClearButtonEnabled(True)
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        self._table = QTableWidget(0, len(fields))
        self._table.setHorizontalHeaderLabels([label for _, label in fields])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self._table, stretch=1)

        form_box = QGroupBox("Data")
        form = QFormLayout(form_box)
        for key, label in fields:
            row = QHBoxLayout()
            row.addWidget(self._vars[key], stretch=1)
            if browsable and key == fields[-1][0]:
                browse = QPushButton("Pilih berkas...")
                browse.clicked.connect(self._browse)
                row.addWidget(browse)
            form.addRow(label, row)
        layout.addWidget(form_box)

        if browsable:
            self._preview = QLabel("Pratinjau")
            self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._preview.setMinimumHeight(_PREVIEW_MAX[1])
            self._preview.setStyleSheet("border: 1px solid #d9d9d9;")
            layout.addWidget(self._preview)
            self._vars[fields[-1][0]].textChanged.connect(self._update_preview)

        buttons = QHBoxLayout()
        for text, handler in (("Tambah", self._add), ("Ubah", self._update), ("Hapus", self._delete)):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        buttons.addStretch(1)
        self._status = QLabel("")
        buttons.addWidget(self._status)
        layout.addLayout(buttons)

    # API yang diisi turunan
    def _row_text(self, item) -> str:
        raise NotImplementedError

    def _new_item(self, item_id: int):
        raise NotImplementedError

    def _list(self) -> list:
        raise NotImplementedError

    def _create(self, item) -> int:
        raise NotImplementedError

    def _apply_update(self, item) -> None:
        raise NotImplementedError

    def _remove(self, item_id: int) -> None:
        raise NotImplementedError

    # Perilaku umum
    def refresh(self) -> None:
        self._items = self._list()
        self._table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            for col, (key, _label) in enumerate(self._fields):
                cell = QTableWidgetItem(str(getattr(item, key) or ""))
                cell.setData(Qt.ItemDataRole.UserRole, row)
                self._table.setItem(row, col, cell)
        self._clear_entries()
        self._apply_filter()

    def _clear_entries(self) -> None:
        for var in self._vars.values():
            var.clear()

    def _selected(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _on_select(self) -> None:
        item = self._selected()
        if item is None:
            return
        for key, _label in self._fields:
            self._vars[key].setText(getattr(item, key))

    def _apply_filter(self) -> None:
        query = self._filter.text().strip().lower()
        for row in range(self._table.rowCount()):
            joined = " ".join(
                self._table.item(row, col).text().lower()
                for col in range(self._table.columnCount())
                if self._table.item(row, col) is not None
            )
            self._table.setRowHidden(row, bool(query) and query not in joined)

    def _browse(self) -> None:
        chosen, _selected_filter = QFileDialog.getOpenFileName(
            self, "Pilih berkas", "", "Gambar (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if chosen:
            self._vars[self._fields[-1][0]].setText(chosen)

    def _update_preview(self) -> None:
        if not hasattr(self, "_preview"):
            return
        path = self._vars[self._fields[-1][0]].text().strip()
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self._preview.setPixmap(QPixmap())
            self._preview.setText("Pratinjau")
            return
        self._preview.setText("")
        self._preview.setPixmap(
            pixmap.scaled(
                _PREVIEW_MAX[0],
                _PREVIEW_MAX[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _add(self) -> None:
        values = [self._vars[key].text().strip() for key, _ in self._fields]
        if not any(values):
            self._status.setText("Isi minimal satu kolom.")
            return
        self._create(self._new_item(0))
        self._status.setText("Ditambahkan.")
        self.refresh()

    def _update(self) -> None:
        item = self._selected()
        if item is None:
            self._status.setText("Pilih baris dulu.")
            return
        for key, _label in self._fields:
            setattr(item, key, self._vars[key].text().strip())
        self._apply_update(item)
        self._status.setText("Diubah.")
        self.refresh()

    def _delete(self) -> None:
        item = self._selected()
        if item is None:
            self._status.setText("Pilih baris dulu.")
            return
        self._remove(item.id)
        self._status.setText("Dihapus.")
        self.refresh()


class _DosenPanel(_CrudPanel):
    def __init__(self, db: Database):
        self._db = db
        super().__init__(
            "Daftar dosen", [("nama", "Nama"), ("gelar", "Gelar"), ("identitas", "NIDN/NIP")]
        )
        self.refresh()

    def _new_item(self, item_id: int) -> Dosen:
        return Dosen(
            item_id,
            self._vars["nama"].text().strip(),
            self._vars["gelar"].text().strip(),
            self._vars["identitas"].text().strip(),
        )

    def _list(self):
        return self._db.list_dosen()

    def _create(self, item) -> int:
        return self._db.add_dosen(item)

    def _apply_update(self, item) -> None:
        self._db.update_dosen(item)

    def _remove(self, item_id: int) -> None:
        self._db.delete_dosen(item_id)


class _MataKuliahPanel(_CrudPanel):
    def __init__(self, db: Database):
        self._db = db
        super().__init__("Daftar mata kuliah", [("nama", "Nama"), ("kode", "Kode")])
        self.refresh()

    def _new_item(self, item_id: int) -> MataKuliah:
        return MataKuliah(
            item_id, self._vars["nama"].text().strip(), self._vars["kode"].text().strip()
        )

    def _list(self):
        return self._db.list_mata_kuliah()

    def _create(self, item) -> int:
        return self._db.add_mata_kuliah(item)

    def _apply_update(self, item) -> None:
        self._db.update_mata_kuliah(item)

    def _remove(self, item_id: int) -> None:
        self._db.delete_mata_kuliah(item_id)


class _LogoPanel(_CrudPanel):
    def __init__(self, db: Database):
        self._db = db
        super().__init__(
            "Daftar logo", [("nama", "Nama"), ("path", "Berkas")], browsable=True
        )
        self.refresh()

    def _new_item(self, item_id: int) -> Logo:
        return Logo(item_id, self._vars["nama"].text().strip(), self._vars["path"].text().strip())

    def _list(self):
        return self._db.list_logo()

    def _create(self, item) -> int:
        return self._db.add_logo(item)

    def _apply_update(self, item) -> None:
        self._db.update_logo(item)

    def _remove(self, item_id: int) -> None:
        self._db.delete_logo(item_id)


class DataTab(QWidget):
    """Wadah empat sub-tab data (parity judul Tk)."""

    def __init__(self, db: Database):
        super().__init__()
        self._db = db
        self.inner = QTabWidget()
        self.profil_form = _ProfilForm(db)
        self.dosen_panel = _DosenPanel(db)
        self.matkul_panel = _MataKuliahPanel(db)
        self.logo_panel = _LogoPanel(db)
        self.inner.addTab(self.profil_form, "Profil Mahasiswa")
        self.inner.addTab(self.dosen_panel, "Dosen")
        self.inner.addTab(self.matkul_panel, "Mata Kuliah")
        self.inner.addTab(self.logo_panel, "Logo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.inner)

    def refresh_all(self) -> None:
        self.dosen_panel.refresh()
        self.matkul_panel.refresh()
        self.logo_panel.refresh()
