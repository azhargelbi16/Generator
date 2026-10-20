"""Pengendali halaman setup Laporan Qt (parity ReportController Tk, bagian setup).

State publik minimum untuk fase berikutnya: `sources`, `sections`, `done`,
`statuses`, `fields`, `template`, `unknown_markers`. Dialog Tk (messagebox,
metadata) diganti status label + `_last_message` agar bisa diuji offscreen.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from .. import config, database, drafts, paths, report
from ..ai import bibliography, content
from ..ai.citation import Source
from ..ai.client import AIClient
from ..document.template import TemplateError, validate_template
from ..sources import pdf_reader, web_reader
from ..sources.records import (
    DRAFT_ACTIVE_ID,
    normalize_metadata,
    record_to_source,
    source_to_record,
)
from ..verification import SentenceStatus, verify_sections
from .workers import run_in_thread

_META_KEYS = ("year", "title", "container", "doi", "url")
_META_LABELS = {
    "year": "Tahun",
    "title": "Judul",
    "container": "Publikasi",
    "doi": "DOI",
    "url": "URL",
}


class ReportController(QObject):
    """Halaman "Laporan": sumber + pengaturan; state milik objek ini."""

    generateRequested = Signal()

    def __init__(self, db: database.Database, config_path: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._db = db
        self._config_path = Path(config_path) if config_path else Path(paths.CONFIG_PATH)

        # State publik (dikonsumsi Review fase 4 dan Panggung Task 3.2).
        self.sources: list[dict] = []
        self.sections: list = []
        self.done: set[str] = set()
        self.statuses: list[SentenceStatus] = []
        self.fields: dict = {}
        self.template = None
        self.unknown_markers: list[str] = []

        self._templates = db.list_template()
        self._dosen_list = db.list_dosen()
        self._matkul_list = db.list_mata_kuliah()
        self._logo_list = db.list_logo()
        self._thread = None
        self._worker = None
        self._last_message = ""

        self.setup_page = QWidget()
        self._build_setup_page(self.setup_page)
        self._restore_draft()

    # ------------------------------------------------------------------ UI

    def _build_setup_page(self, page: QWidget) -> None:
        layout = QHBoxLayout(page)

        left = QVBoxLayout()
        layout.addLayout(left, stretch=1)
        source_box = QGroupBox("Sumber")
        source_layout = QVBoxLayout(source_box)
        self._source_list = QListWidget()
        source_layout.addWidget(self._source_list)
        left.addWidget(source_box, stretch=1)

        buttons = QHBoxLayout()
        for text, handler in (
            ("📄 Tambah PDF...", self._add_pdf),
            ("🔗 Tambah Link...", self._add_link),
            ("✍️ Tempel Teks Manual...", self._paste_manual),
            ("🗑 Hapus", self._hapus_source),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        buttons.addStretch(1)
        self._status = QLabel("")
        buttons.addWidget(self._status)
        left.addLayout(buttons)

        corrections = QGroupBox("Koreksi metadata sumber terpilih")
        corrections_layout = QVBoxLayout(corrections)
        meta_form = QFormLayout()
        self._meta_fields = {key: QLineEdit() for key in _META_KEYS}
        for key in _META_KEYS:
            meta_form.addRow(_META_LABELS[key], self._meta_fields[key])
        corrections_layout.addLayout(meta_form)
        self._authors_box = QWidget()
        self._authors_layout = QVBoxLayout(self._authors_box)
        self._authors_layout.setContentsMargins(0, 0, 0, 0)
        corrections_layout.addWidget(self._authors_box)
        apply_button = QPushButton("✔ Terapkan Koreksi")
        apply_button.clicked.connect(self._apply_corrections)
        corrections_layout.addWidget(apply_button)
        left.addWidget(corrections)
        self._source_list.currentRowChanged.connect(self._on_source_select)

        right = QVBoxLayout()
        layout.addLayout(right, stretch=1)
        settings = QGroupBox("Pengaturan laporan")
        settings_layout = QVBoxLayout(settings)

        profil = self._db.get_profil()
        profil_text = (
            f"Profil: {profil.nama} ({profil.nim}), {profil.prodi}"
            if profil and profil.nama
            else "Profil belum diisi di tab Data."
        )
        settings_layout.addWidget(QLabel(profil_text))

        pick_form = QFormLayout()
        self._template_combo = QComboBox()
        self._template_combo.addItems([t.nama for t in self._templates])
        self._template_combo.currentIndexChanged.connect(self._on_template_selected)
        pick_form.addRow("Template", self._template_combo)
        self._pickers: dict[str, QComboBox] = {}
        for key, label, items in (
            ("dosen", "Dosen pembimbing", [d.nama for d in self._dosen_list]),
            ("matkul", "Mata kuliah", [m.nama for m in self._matkul_list]),
            ("logo", "Logo", [l.nama for l in self._logo_list]),
        ):
            combo = QComboBox()
            combo.addItems(items)
            combo.currentIndexChanged.connect(lambda _i: self._save_draft())
            self._pickers[key] = combo
            pick_form.addRow(label, combo)
        self._judul_edit = QLineEdit()
        self._judul_edit.textEdited.connect(lambda _t: self._save_draft())
        pick_form.addRow("Judul laporan", self._judul_edit)
        settings_layout.addLayout(pick_form)

        settings_layout.addWidget(QLabel("Outline bab (satu baris satu bab)"))
        self._outline_edit = QTextEdit()
        self._outline_edit.textChanged.connect(self._on_outline_edited)
        settings_layout.addWidget(self._outline_edit, stretch=1)

        self._suggest_button = QPushButton("💡 Usulkan Outline")
        self._suggest_button.clicked.connect(self._suggest_outline)
        settings_layout.addWidget(self._suggest_button)
        self._generate_button = QPushButton("🚀 Generate isi laporan")
        self._generate_button.setDefault(True)
        self._generate_button.clicked.connect(lambda: self.generateRequested.emit())
        settings_layout.addWidget(self._generate_button)
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        settings_layout.addWidget(self._progress)
        right.addWidget(settings)
        self._update_outline_button()

    # ------------------------------------------------------------- sumber

    def _iter_sentences(self):
        for section in self.sections:
            for paragraph in section.paragraphs:
                yield from paragraph.sentences

    def _refresh_source_list(self) -> None:
        self._source_list.clear()
        for index, record in enumerate(self.sources, start=1):
            year = f" ({record['year']})" if record.get("year") else ""
            self._source_list.addItem(f"{index}. {record.get('title') or 'tanpa judul'}{year}")

    def _selected_index(self) -> int | None:
        row = self._source_list.currentRow()
        return row if 0 <= row < len(self.sources) else None

    def _hapus_source(self) -> None:
        """Buang sumber terpilih; sitasi yang merujuknya dilepas, indeks lain digeser."""
        index = self._selected_index()
        if index is None:
            self._status.setText("Pilih dulu sumbernya di daftar.")
            return
        del self.sources[index]
        for sentence in self._iter_sentences():
            sentence.source_ids = [
                i - 1 if i > index else i for i in sentence.source_ids if i != index
            ]
            if not sentence.source_ids:
                sentence.citation = False
        self._refresh_source_list()
        self._after_structure_change("Sumber dihapus; sitasi yang merujuknya dilepas.")

    def _on_source_select(self) -> None:
        index = self._selected_index()
        while self._authors_layout.count():
            item = self._authors_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._author_rows: list[dict] = []
        if index is None:
            return
        record = self.sources[index]
        for key in self._meta_fields:
            self._meta_fields[key].setText(record.get(key, ""))
        authors = record.get("authors", [])
        if not authors:
            authors = [{"family": "", "given": "", "is_org": False, "abbrev": ""}]
        for number, author in enumerate(authors, start=1):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"Penulis {number}"))
            family = QLineEdit(author.get("family", ""))
            given = QLineEdit(author.get("given", ""))
            abbrev = QLineEdit(author.get("abbrev", ""))
            is_org = QCheckBox("organisasi")
            is_org.setChecked(bool(author.get("is_org", False)))
            row.addWidget(QLabel("keluarga"))
            row.addWidget(family)
            row.addWidget(QLabel("depan"))
            row.addWidget(given)
            row.addWidget(is_org)
            row.addWidget(QLabel("singkatan"))
            row.addWidget(abbrev)
            row.addStretch(1)
            self._authors_layout.addWidget(row_widget)
            self._author_rows.append(
                {"family": family, "given": given, "is_org": is_org, "abbrev": abbrev}
            )

    def _apply_corrections(self) -> None:
        index = self._selected_index()
        if index is None:
            self._status.setText("Pilih sumber di daftar lebih dulu.")
            return
        record = self.sources[index]
        for key in self._meta_fields:
            record[key] = self._meta_fields[key].text().strip()
        record["authors"] = [
            {
                "family": row["family"].text().strip(),
                "given": row["given"].text().strip(),
                "is_org": row["is_org"].isChecked(),
                "abbrev": row["abbrev"].text().strip(),
            }
            for row in self._author_rows
        ]
        record["authors"] = [
            author for author in record["authors"] if author["family"] or author["given"]
        ]
        self._refresh_source_list()
        self._save_draft()
        self._status.setText("Koreksi metadata diterapkan.")

    # ------------------------------------------------- tambah sumber (latar)

    def _ai_client(self) -> AIClient:
        return AIClient(config.load_config(self._config_path))

    def append_source(self, record: dict) -> None:
        """Masukkan rekord sumber jadi (hasil baca PDF/web/manual)."""
        self.sources.append(record)
        self._refresh_source_list()
        self._source_list.setCurrentRow(len(self.sources) - 1)
        self._save_draft()
        self._status.setText(f"Sumber {record['kind']} ditambahkan ({len(self.sources)} total).")

    def _source_failed(self, error: Exception) -> None:
        if isinstance(error, pdf_reader.SourceReadError):
            self._last_message = (
                f"{error}\nGunakan tombol 'Tempel Teks Manual...' untuk sumber ini; "
                "sumber lain tetap bisa diproses."
            )
        else:
            self._last_message = str(error)
        self._status.setText("Penambahan sumber gagal.")

    def _add_pdf(self) -> None:
        chosen, _selected_filter = QFileDialog.getOpenFileName(
            self.setup_page, "Pilih berkas PDF", "", "PDF (*.pdf);;Semua berkas (*.*)"
        )
        if chosen:
            self._add_pdf_core(Path(chosen))

    def _add_pdf_core(self, path: Path) -> None:
        self._status.setText("Membaca PDF (bisa lama bila scan)...")
        client = self._ai_client()

        def work():
            text = pdf_reader.extract_text_or_ocr(path)
            meta = normalize_metadata(pdf_reader.extract_metadata(path))
            try:
                source = bibliography.extract_source(text, client)
            except Exception:
                source = Source([], "", "")
            return source_to_record(bibliography.merge_metadata(source, meta), text, "pdf")

        self._thread, self._worker = run_in_thread(self.setup_page, work)
        self._worker.result.connect(self.append_source)
        self._worker.error.connect(self._source_failed)

    def _add_link(self) -> None:
        url, ok = QInputDialog.getText(self.setup_page, "Tambah Sumber Link", "URL sumber:")
        if not ok or not url.strip():
            return
        self._add_link_core(url.strip())

    def _add_link_core(self, url: str) -> None:
        self._status.setText("Mengambil halaman web...")
        client = self._ai_client()

        def work():
            text, meta = web_reader.fetch(url)
            meta = normalize_metadata(meta)
            try:
                source = bibliography.extract_source(text, client)
            except Exception:
                source = Source([], "", "")
            return source_to_record(bibliography.merge_metadata(source, meta), text, "web")

        self._thread, self._worker = run_in_thread(self.setup_page, work)
        self._worker.result.connect(self.append_source)
        self._worker.error.connect(self._source_failed)

    def _paste_manual(self) -> None:
        text, ok = QInputDialog.getMultiLineText(
            self.setup_page, "Tempel Teks Manual", "Tempel teks sumber di bawah, lalu klik OK."
        )
        if ok and text.strip():
            self._add_manual_text(text.strip())

    def _add_manual_text(self, text: str) -> None:
        self._status.setText("Mengekstrak metadata teks manual...")
        client = self._ai_client()

        def work():
            source = bibliography.extract_source(text, client)
            return source_to_record(bibliography.merge_metadata(source, {}), text, "manual")

        self._thread, self._worker = run_in_thread(self.setup_page, work)
        self._worker.result.connect(self.append_source)
        self._worker.error.connect(self._source_failed)

    # ----------------------------------------------------------- pengaturan

    def _on_template_selected(self) -> None:
        name = self._template_combo.currentText()
        item = next((t for t in self._templates if t.nama == name), None)
        self._last_message = ""
        if item is None:
            self.template = None
            return
        try:
            result = validate_template(Path(item.path))
        except TemplateError as error:
            self._last_message = str(error)
            self.template = None
            self.unknown_markers = []
            self._template_combo.setCurrentIndex(-1)
            return
        if result.missing or result.not_standalone:
            lines = []
            if result.missing:
                lines.append("Penanda wajib yang kurang: " + ", ".join(result.missing))
            if result.not_standalone:
                lines.append(
                    "Penanda khusus yang tidak berdiri sendiri: "
                    + ", ".join(result.not_standalone)
                )
            lines.append("Pilih template lain untuk melanjutkan.")
            self._last_message = "\n".join(lines)
            self.template = None
            self.unknown_markers = []
            self._template_combo.setCurrentIndex(-1)
            return
        self.template = item
        self.unknown_markers = list(result.unknown)
        if result.unknown:
            self._status.setText(
                "Catatan: penanda tak dikenal di template: " + ", ".join(result.unknown)
            )
        self._save_draft()

    def _outline_content(self) -> list[str]:
        raw = self._outline_edit.toPlainText()
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def generate_plan(self):
        """Rangkum rencana generate untuk StagePage: (topik, outline, sources, texts)."""
        sources = [record_to_source(record) for record in self.sources]
        texts = [record.get("text", "") for record in self.sources]
        return (self._judul_edit.text().strip(), self._outline_content(), sources, texts)

    def _update_outline_button(self) -> None:
        self._suggest_button.setVisible(not self._outline_content())

    def _on_outline_edited(self) -> None:
        self._update_outline_button()
        self._save_draft()

    def _suggest_outline(self) -> None:
        topic = self._judul_edit.text().strip()
        if not topic:
            self._last_message = "Isi judul laporan lebih dulu sebagai topik outline."
            return
        self._status.setText("Menyusun usulan outline...")
        client = self._ai_client()
        sources = [record_to_source(record) for record in self.sources]
        texts = [record.get("text", "") for record in self.sources]

        def work():
            return content.suggest_outline(topic, sources, texts, client)

        self._thread, self._worker = run_in_thread(self.setup_page, work)
        self._worker.result.connect(self._on_outline_suggested)
        self._worker.error.connect(self._on_outline_failed)

    def _on_outline_suggested(self, items: list[str]) -> None:
        if not items:
            self._last_message = "AI tidak mengembalikan outline. Tulis outline manual atau coba lagi."
        else:
            self._outline_edit.setPlainText("\n".join(items))
            self._save_draft()
        self._update_outline_button()
        self._status.setText("Usulan outline siap." if items else "Outline tidak tersedia.")

    def _on_outline_failed(self, message: str) -> None:
        self._last_message = f"Gagal menyusun outline: {message}"
        self._status.setText("Penambahan outline gagal.")

    # ---------------------------------------------------------------- draf

    def _source_texts_by_id(self) -> dict[int, str]:
        return {index: record.get("text", "") for index, record in enumerate(self.sources)}

    def _reverify(self) -> None:
        self.statuses = verify_sections(self.sections, self._source_texts_by_id())

    def _after_structure_change(self, message: str) -> None:
        self._reverify()
        self._save_draft()
        self._status.setText(message)

    def _collect_fields(self) -> dict:
        return {
            "judul": self._judul_edit.text(),
            "outline": self._outline_edit.toPlainText().rstrip("\n"),
            "template": self._template_combo.currentText(),
            "dosen": self._pickers["dosen"].currentText(),
            "matkul": self._pickers["matkul"].currentText(),
            "logo": self._pickers["logo"].currentText(),
        }

    def _save_draft(self) -> None:
        self.fields = self._collect_fields()
        state = drafts.DraftState(
            draft_id=DRAFT_ACTIVE_ID,
            fields=self.fields,
            sources=self.sources,
            sections=report.sections_to_dicts(self.sections),
            done=sorted(self.done),
        )
        drafts.save_draft(state)

    def _restore_draft(self) -> None:
        state = drafts.load_draft(DRAFT_ACTIVE_ID)
        if state is None:
            self.fields = self._collect_fields()
            return
        fields = state.fields
        self._judul_edit.setText(fields.get("judul", ""))
        if fields.get("outline"):
            self._outline_edit.setPlainText(fields["outline"])
        for key in ("dosen", "matkul", "logo"):
            if fields.get(key):
                self._pickers[key].setCurrentText(fields[key])
        self.sources = list(state.sources)
        self._refresh_source_list()
        self.sections = report.sections_from_dicts(state.sections)
        self.done = set(state.done)
        if self.sections:
            self._reverify()
        if fields.get("template"):
            self._template_combo.setCurrentText(fields["template"])
            self._on_template_selected()
        self._update_outline_button()
        self.fields = self._collect_fields()
