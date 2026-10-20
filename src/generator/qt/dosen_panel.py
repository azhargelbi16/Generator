"""Panel catatan margin Mode Dosen (addendum D.4).

Panel dock kanan di halaman Review; dikelompokkan per bab, tiap catatan
`DosenNote` tampil [severity] komentar. Klik catatan mengaktifkan kalimat
yang dirujuk (bila sentence_uid ada). Catatan TIDAK masuk DOCX.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..ai.dosen import DosenNote

_ROLE_UID = Qt.ItemDataRole.UserRole


class DosenPanel(QWidget):
    """Daftar catatan dosen per bab; bisa ditutup dan dibuka lagi lewat tombol Review."""

    noteActivated = Signal(str)  # sentence_uid yang dirujuk catatan

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.addWidget(QLabel("Review Dosen"))
        header.addStretch(1)
        close = QPushButton("✕")
        close.setFlat(True)
        close.clicked.connect(self.hide)
        header.addWidget(close)
        layout.addLayout(header)
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)
        self.hide()

    def show_notes(self, notes: list[DosenNote]) -> None:
        """Isi panel; catatan dikelompokkan per judul bab sesuai urutan datang."""
        self._list.clear()
        by_section: dict[str, list[DosenNote]] = {}
        for note in notes:
            by_section.setdefault(note.section_title or "(tanpa bab)", []).append(note)
        for title, group in by_section.items():
            header = QListWidgetItem(title)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            self._list.addItem(header)
            for note in group:
                item = QListWidgetItem(f"[{note.severity}] {note.comment}")
                item.setData(_ROLE_UID, note.sentence_uid or "")
                self._list.addItem(item)
        self.show()

    def note_count(self) -> int:
        return sum(
            1
            for i in range(self._list.count())
            if self._list.item(i).flags() & Qt.ItemFlag.ItemIsEnabled
        )

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        uid = item.data(_ROLE_UID)
        if uid:
            self.noteActivated.emit(uid)
