"""Review Hasil ala MS Word: dokumen dengan span kalimat bergaris (addendum D.1).

Tiap paragraf adalah satu QTextBlock; span kalimat disimpan di QTextBlockUserData
sehingga `uid_at(pos)` tidak butuh pemindaian teks. Kalimat "tidak_terverifikasi"
diberi SpellCheckUnderline merah. Render penuh hanya saat struktur berubah;
seleksi dan suntingan inline hanya menyentuh blok yang bersangkutan.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QTextBlockFormat,
    QTextBlockUserData,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import config, paths, report
from ..ai import content
from ..ai.client import AIClient
from ..sources.records import record_to_source
from ..verification import (
    STATUS_NON_FACTUAL,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    verify_sentence,
)

_STATUS_LABELS = {
    STATUS_VERIFIED: "terverifikasi",
    STATUS_UNVERIFIED: "belum terverifikasi",
    STATUS_NON_FACTUAL: "bukan klaim faktual",
}
_STATUS_COLORS = {
    STATUS_VERIFIED: "#1a7f37",
    STATUS_UNVERIFIED: "#cf222e",
    STATUS_NON_FACTUAL: "#6e7781",
}
_UNVERIFIED_RED = QColor("#ff0000")
_SELECTED_BG = QColor("#fff3bf")
_FONT_FAMILY = "Times New Roman"

_NAV_KEYS = (
    Qt.Key.Key_Left,
    Qt.Key.Key_Right,
    Qt.Key.Key_Up,
    Qt.Key.Key_Down,
    Qt.Key.Key_Home,
    Qt.Key.Key_End,
    Qt.Key.Key_PageUp,
    Qt.Key.Key_PageDown,
)


class _BlockData(QTextBlockUserData):
    """Span kalimat per blok: daftar {start, end, uid, status} relatif ke blok."""

    def __init__(self, spans=None, heading: bool = False, section_index: int = -1):
        super().__init__()
        self.spans: list[dict] = spans or []
        self.heading = heading
        self.section_index = section_index


class _DocView(QTextEdit):
    """QTextEdit dokumen; klik kalimat memilih span, ketikan dibatasi span aktif."""

    def __init__(self, page: "ReviewPage"):
        super().__init__()
        self._page = page
        self.setReadOnly(True)
        self.setFont(QFont(_FONT_FAMILY, 12))

    def mouseReleaseEvent(self, event) -> None:
        cursor = self.cursorForPosition(event.pos())
        uid = self._page.uid_at(cursor.position())
        if uid:
            self._page.select(uid)
            self._page.sentenceActivated.emit(uid)
        else:
            self._page.select(None)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        page = self._page
        edit = page._active_edit
        if edit is None or self.isReadOnly():
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return  # kalimat satu baris; Enter akan membelah tampilan dokumen
        if key in _NAV_KEYS or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().keyPressEvent(event)
            return
        block = edit["block"]
        if not block.isValid():
            return
        span = edit["span"]
        lo = block.position() + span["start"]
        hi = block.position() + span["end"]
        cursor = self.textCursor()
        if cursor.hasSelection():
            if cursor.selectionStart() < lo or cursor.selectionEnd() > hi:
                return
        elif not (lo <= cursor.position() <= hi):
            return
        if key == Qt.Key.Key_Backspace and cursor.position() <= lo:
            return  # menghapus karakter sebelum kalimat aktif
        if key == Qt.Key.Key_Delete and cursor.position() >= hi:
            return  # menghapus karakter sesudah kalimat aktif
        super().keyPressEvent(event)


class ReviewPage(QWidget):
    """Halaman Review Hasil: dokumen, toolbar melayang, navigasi, status bar."""

    sentenceActivated = Signal(str)  # uid kalimat yang diklik/diaktifkan
    exportRequested = Signal()  # tombol Simpan DOCX (jalur ekspor di fase 5)

    def __init__(self, state, cfg: config.Config | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._cfg = cfg or config.load_config(paths.CONFIG_PATH)
        self._client_factory = lambda: AIClient(config.load_config(paths.CONFIG_PATH))
        self._selected: tuple[int, str] | None = None  # (block_number, uid)
        self._selected_uid: str | None = None
        self._active_edit: dict | None = None
        self._labels: dict[int, str] = {}
        self._thread = None
        self._worker = None

        layout = QHBoxLayout(self)
        dokumen_box = QWidget()
        dokumen_layout = QVBoxLayout(dokumen_box)
        dokumen_layout.setContentsMargins(0, 0, 0, 0)
        self._controls = self._build_controls()
        dokumen_layout.addWidget(self._controls)
        self._document = _DocView(self)
        self._document.document().contentsChange.connect(self._on_contents_change)
        dokumen_layout.addWidget(self._document, stretch=1)
        self._status_bar = QLabel("Belum ada isi.")
        dokumen_layout.addWidget(self._status_bar)
        self._info = QLabel("")
        dokumen_layout.addWidget(self._info)
        layout.addWidget(dokumen_box, stretch=3)
        nav_box = QWidget()
        nav_layout = QVBoxLayout(nav_box)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(QLabel("Navigasi bab"))
        self._nav = QListWidget()
        self._nav.itemClicked.connect(self._on_nav_clicked)
        nav_layout.addWidget(self._nav)
        layout.addWidget(nav_box, stretch=1)
        self._section_positions: dict[int, int] = {}
        self.exportRequested.connect(self._export_docx)
        # Referensi kuat data blok: PySide6 tidak memindahkan kepemilikan
        # QTextBlockUserData, jadi bila wrapper Python di-GC objek C++ ikut
        # terhapus dan dokumen menyimpan pointer liar (crash heap saat teardown).
        self._block_data_refs: list[_BlockData] = []
        self._toolbar = self._build_toolbar()

    # ------------------------------------------------------------ kontrol

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        tombol_para = QPushButton("✔ Tandai paragraf selesai")
        tombol_para.clicked.connect(self._mark_paragraph_done)
        row.addWidget(tombol_para)
        tombol_nonfakta = QPushButton("☑ Tandai semua bukan klaim selesai")
        tombol_nonfakta.clicked.connect(self._mark_all_nonfactual_done)
        row.addWidget(tombol_nonfakta)
        self._approve_button = QPushButton("")
        self._approve_button.clicked.connect(self._approve_all_verified)
        row.addWidget(self._approve_button)
        tombol_docx = QPushButton("💾 Simpan DOCX")
        tombol_docx.clicked.connect(lambda: self.exportRequested.emit())
        row.addWidget(tombol_docx)
        row.addStretch(1)
        return bar

    def _export_docx(self) -> None:
        from .preflight_dialog import export_report

        try:
            path = export_report(self.state)
        except Exception as error:  # jalur lengkap butuh state penuh (db, template)
            self._info.setText(f"Penyimpanan DOCX gagal: {error}")
            return
        if path is None:
            self._info.setText("Simpan dibatalkan.")
        else:
            self._info.setText(f"DOCX tersimpan: {path}")

    def _build_toolbar(self) -> QWidget:
        bar = QWidget(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        bar.setObjectName("toolbarAksi")
        row = QHBoxLayout(bar)
        row.setContentsMargins(6, 4, 6, 4)
        self._toolbar_status = QLabel("")
        row.addWidget(self._toolbar_status)
        for text, handler in (
            ("✒ Parafrase", self._paraphrase),
            ("✔ Tandai selesai", self._mark_done),
            ("↩ Pulihkan sitasi", self._restore_citation_action),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row.addWidget(button)
        self._source_button = QToolButton()
        self._source_button.setText("Sumber ▾")
        self._source_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._source_menu = QMenu(self._source_button)
        self._source_button.setMenu(self._source_menu)
        row.addWidget(self._source_button)
        bar.hide()
        return bar

    def _position_toolbar(self, block, span) -> None:
        cursor = QTextCursor(block)
        cursor.setPosition(block.position() + span["start"])
        rect = self._document.cursorRect(cursor)
        global_pos = self._document.viewport().mapToGlobal(rect.topLeft())
        self._toolbar.move(global_pos + QPoint(0, rect.height() + 2))

    def _update_toolbar_status(self, uid: str) -> None:
        status = self._uid_status(uid)
        label = _STATUS_LABELS.get(status, status)
        if uid in self.state.done:
            label += " · sudah ditandai selesai"
        self._toolbar_status.setText("● " + label)
        self._toolbar_status.setStyleSheet(f"color: {_STATUS_COLORS.get(status, '#000')};")
        self._source_menu.clear()
        sentence = self._sentence_by_uid(uid)
        if sentence is not None:
            for index in sentence.source_ids:
                title = ""
                if index < len(self.state.sources):
                    title = self.state.sources[index].get("title") or "tanpa judul"
                citation = self._labels.get(index, f"[{index + 1}]")
                self._source_menu.addAction(f"{citation} — {title}")

    # -------------------------------------------------------------- render

    @staticmethod
    def _base_format(status: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setFont(QFont(_FONT_FAMILY, 12))
        if status == STATUS_UNVERIFIED:
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            fmt.setUnderlineColor(_UNVERIFIED_RED)
        else:
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
        return fmt

    def render_document(self) -> None:
        """Bangun ulang dokumen dari state; dipanggil saat struktur berubah."""
        self._active_edit = None
        self._document.setReadOnly(True)
        self._toolbar.hide()
        self.select(None)
        self._section_positions = {}
        self._block_data_refs = []
        document = self._document.document()
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()

        self._labels = report.labels_for(
            [record_to_source(r) for r in self.state.sources],
            report.cited_ids(self.state.statuses),
            style=self._cfg.citation_style,
        )
        status_by_uid = {item.sentence.uid: item.status for item in self.state.statuses}

        title_block = QTextBlockFormat()
        title_block.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading_block = QTextBlockFormat()
        heading_block.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_block = QTextBlockFormat()

        judul = (self.state.fields or {}).get("judul", "").strip()
        cursor.setBlockFormat(title_block)
        if judul:
            title_fmt = QTextCharFormat()
            title_fmt.setFont(QFont(_FONT_FAMILY, 16, QFont.Weight.Bold))
            cursor.insertText(judul, title_fmt)

        total_sentences = 0
        for section_index, section in enumerate(self.state.sections):
            cursor.insertBlock(heading_block)
            self._section_positions[section_index] = cursor.block().position()
            heading_fmt = QTextCharFormat()
            heading_fmt.setFont(QFont(_FONT_FAMILY, 14, QFont.Weight.Bold))
            cursor.insertText(section.title, heading_fmt)
            heading_data = _BlockData(heading=True, section_index=section_index)
            self._block_data_refs.append(heading_data)
            cursor.block().setUserData(heading_data)
            for paragraph in section.paragraphs:
                cursor.insertBlock(body_block)
                self._render_block_content(cursor.block(), paragraph, status_by_uid)
                total_sentences += len(paragraph.sentences)
        if not total_sentences:
            placeholder = QTextCharFormat()
            placeholder.setFont(QFont(_FONT_FAMILY, 14, QFont.Weight.Bold))
            cursor.insertText(
                "Belum ada isi. Isi outline, tambahkan sumber, lalu klik Generate isi laporan.",
                placeholder,
            )
        self._update_nav()
        self._update_status_bar()
        self._update_controls()

    def _render_block_content(self, block, paragraph, status_by_uid) -> None:
        """Isi ulang satu blok paragraf dari objek Paragraph; scroll dipertahankan."""
        scroll = self._document.verticalScrollBar().value()
        document = self._document.document()
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        block_start = block.position()
        spans = []
        data = block.userData()
        section_index = data.section_index if data is not None else -1
        for sentence in paragraph.sentences:
            start = cursor.position() - block_start
            cursor.insertText(report.display_text(sentence, self._labels))
            end = cursor.position() - block_start
            cursor.insertText(" ")
            spans.append(
                {
                    "start": start,
                    "end": end,
                    "uid": sentence.uid,
                    "status": status_by_uid.get(sentence.uid, STATUS_UNVERIFIED),
                }
            )
        for span in spans:
            self._apply_span_format(block, span, self._base_format(span["status"]))
        block_data = _BlockData(spans=spans, section_index=section_index)
        self._block_data_refs.append(block_data)
        block.setUserData(block_data)
        self._document.verticalScrollBar().setValue(scroll)

    # --------------------------------------------------------- pemetaan uid

    def uid_at(self, pos: int) -> str | None:
        """Uid kalimat pada posisi dokumen, atau None bila di luar span."""
        block = self._document.document().findBlock(pos)
        if not block.isValid():
            return None
        data = block.userData()
        if data is None or not data.spans:
            return None
        offset = pos - block.position()
        for span in data.spans:
            if span["start"] <= offset < span["end"]:
                return span["uid"]
        return None

    # ------------------------------------------------------- state helpers

    def _iter_sentences(self):
        for section in self.state.sections:
            for paragraph in section.paragraphs:
                yield from paragraph.sentences

    def _sentence_by_uid(self, uid: str):
        for sentence in self._iter_sentences():
            if sentence.uid == uid:
                return sentence
        return None

    def _swap_sentence(self, uid: str, replacements: list) -> bool:
        """Ganti satu kalimat ber-uid dengan daftar kalimat baru di paragraf asalnya."""
        for section in self.state.sections:
            for paragraph in section.paragraphs:
                for index, sentence in enumerate(paragraph.sentences):
                    if sentence.uid == uid:
                        paragraph.sentences[index : index + 1] = replacements
                        return True
        return False

    def _source_texts_by_id(self) -> dict[int, str]:
        return {index: record.get("text", "") for index, record in enumerate(self.state.sources)}

    def _reverify_one(self, sentence) -> str:
        """Verifikasi ulang satu kalimat dan sinkronkan entri statuses."""
        status = verify_sentence(sentence, self._source_texts_by_id())
        for index, item in enumerate(self.state.statuses):
            if item.sentence.uid == sentence.uid:
                self.state.statuses[index] = type(item)(item.index, sentence, status)
                return status
        return status

    def _reverify_all(self) -> None:
        from ..verification import verify_sections

        self.state.statuses = verify_sections(self.state.sections, self._source_texts_by_id())

    def _status_by_uid(self) -> dict[str, str]:
        return {item.sentence.uid: item.status for item in self.state.statuses}

    def _uid_status(self, uid: str) -> str:
        return self._status_by_uid().get(uid, STATUS_UNVERIFIED)

    def _after_structure_change(self, message: str) -> None:
        self._reverify_all()
        self._labels = report.labels_for(
            [record_to_source(r) for r in self.state.sources],
            report.cited_ids(self.state.statuses),
            style=self._cfg.citation_style,
        )
        self.render_document()
        self._save_draft()
        self._info.setText(message)

    def _save_draft(self) -> None:
        save = getattr(self.state, "_save_draft", None)
        if callable(save):
            save()

    # -------------------------------------------------------------- seleksi

    def select(self, uid: str | None) -> None:
        """Sorot span kalimat dan tampilkan toolbar; None melepas semuanya."""
        if self._active_edit is not None and (
            uid is None or self._active_edit["uid"] != uid
        ):
            self._commit_inline_edit()
        self._clear_selection_format()
        self._selected_uid = uid
        if uid is None:
            self._document.setReadOnly(True)
            self._toolbar.hide()
            return
        block = self._document.document().firstBlock()
        while block.isValid():
            data = block.userData()
            if data is not None:
                for span in data.spans:
                    if span["uid"] == uid:
                        fmt = self._base_format(span["status"])
                        fmt.setBackground(_SELECTED_BG)
                        self._apply_span_format(block, span, fmt)
                        self._selected = (block.blockNumber(), uid)
                        teks_asli = block.text()[span["start"] : span["end"]]
                        self._active_edit = {
                            "uid": uid,
                            "block": block,
                            "span": dict(span),
                            "text_asli": teks_asli,
                        }
                        self._document.setReadOnly(False)
                        self._position_toolbar(block, span)
                        self._toolbar.show()
                        self._update_toolbar_status(uid)
                        self._update_selection_info(uid)
                        return
            block = block.next()

    def select_none(self) -> None:
        self.select(None)

    def _clear_selection_format(self) -> None:
        if self._selected is None:
            return
        block_number, uid = self._selected
        block = self._document.document().findBlockByNumber(block_number)
        self._selected = None
        if not block.isValid():
            return
        data = block.userData()
        if data is None:
            return
        for span in data.spans:
            if span["uid"] == uid:
                self._apply_span_format(block, span, self._base_format(span["status"]))
                return

    @staticmethod
    def _apply_span_format(block, span, fmt) -> None:
        cursor = QTextCursor(block)
        cursor.setPosition(block.position() + span["start"])
        cursor.setPosition(block.position() + span["end"], QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(fmt)

    def _update_selection_info(self, uid: str) -> None:
        status = self._uid_status(uid)
        selesai = (
            "sudah ditandai selesai" if uid in self.state.done else "belum ditandai selesai"
        )
        block = self._document.document().firstBlock()
        para_uids: list[str] = []
        while block.isValid():
            data = block.userData()
            if data is not None and any(s["uid"] == uid for s in data.spans):
                para_uids = [s["uid"] for s in data.spans]
                break
            block = block.next()
        sudah = sum(1 for u in para_uids if u in self.state.done)
        judul_bab = ""
        for section in self.state.sections:
            if any(s.uid == uid for p in section.paragraphs for s in p.sentences):
                judul_bab = section.title
                break
        self._info.setText(
            f"[{judul_bab}] paragraf ini {sudah}/{len(para_uids)} "
            f"kalimat selesai; kalimat yang diklik {status} ({selesai})."
        )

    # --------------------------------------------------------- sunting inline

    def _on_contents_change(self, pos: int, chars_removed: int, chars_added: int) -> None:
        """Geser span aktif mengikuti ketikan; span lain tak terpengaruh (diedit di commit)."""
        edit = self._active_edit
        if edit is None or (chars_removed == 0 and chars_added == 0):
            return
        block = edit["block"]
        if not block.isValid() or pos < block.position():
            return
        data = block.userData()
        if data is None:
            return
        rel = pos - block.position()
        delta = chars_added - chars_removed
        for span in data.spans:
            if span["uid"] == edit["uid"]:
                if rel < span["start"]:
                    span["start"] += delta
                    span["end"] += delta
                elif rel <= span["end"]:
                    span["end"] += delta
                edit["span"] = dict(span)
                return

    def _commit_inline_edit(self) -> None:
        """Simpan ketikan di span kalimat aktif sebagai suntingan manual; kosong diabaikan."""
        edit = self._active_edit
        if edit is None:
            return
        self._active_edit = None
        self._document.setReadOnly(True)
        block = edit["block"]
        if not block.isValid():
            return
        data = block.userData()
        span = None
        if data is not None:
            for candidate in data.spans:
                if candidate["uid"] == edit["uid"]:
                    span = candidate
                    break
        if span is None:
            return
        teks_baru = " ".join(block.text()[span["start"] : span["end"]].split())
        if teks_baru and teks_baru != " ".join(edit["text_asli"].split()):
            sentence = self._sentence_by_uid(edit["uid"])
            if sentence is None:
                return
            new_sentence = report.apply_manual_edit(sentence, teks_baru)
            self._swap_sentence(edit["uid"], [new_sentence])
            self._reverify_one(new_sentence)
            paragraph = self._paragraph_of(edit["uid"])
            if paragraph is not None:
                self._render_block_content(block, paragraph, self._status_by_uid())
            self._save_draft()
            self._update_nav()
            self._update_status_bar()
            self._info.setText(
                "Kalimat disunting langsung di dokumen; berstatus belum terverifikasi "
                "sampai ditandai selesai."
            )

    def _paragraph_of(self, uid: str):
        for section in self.state.sections:
            for paragraph in section.paragraphs:
                if any(sentence.uid == uid for sentence in paragraph.sentences):
                    return paragraph
        return None

    # -------------------------------------------------------------- aksi

    def _selected_or_info(self, pesan: str) -> str | None:
        if self._selected_uid is None:
            self._info.setText(pesan)
            return None
        return self._selected_uid

    def _mark_done(self) -> None:
        uid = self._selected_or_info("Klik dulu kalimat yang ingin ditandai selesai.")
        if uid is None:
            return
        self.state.done.add(uid)
        self._save_draft()
        self._update_nav()
        self._update_selection_info(uid)
        self._info.setText("Kalimat ditandai selesai.")

    def _mark_paragraph_done(self) -> None:
        uid = self._selected_or_info(
            "Klik dulu salah satu kalimat pada paragraf yang ingin ditandai."
        )
        if uid is None:
            return
        paragraph = self._paragraph_of(uid)
        if paragraph is None:
            return
        uids = [sentence.uid for sentence in paragraph.sentences]
        self.state.done.update(uids)
        self._save_draft()
        self._update_nav()
        self._update_selection_info(uid)
        self._info.setText(f"Paragraf ditandai selesai ({len(uids)} kalimat).")

    def _mark_all_nonfactual_done(self) -> None:
        uids = report.non_factual_uids(self.state.statuses)
        self.state.done.update(uids)
        self._save_draft()
        self._update_nav()
        self._update_status_bar()
        self._info.setText(f"{len(uids)} kalimat bukan klaim faktual ditandai selesai.")

    def _approve_all_verified(self) -> None:
        uids = [
            item.sentence.uid for item in self.state.statuses if item.status == STATUS_VERIFIED
        ]
        self.state.done.update(uids)
        self._save_draft()
        self._update_nav()
        self._update_controls()
        self._update_status_bar()
        self._info.setText(f"{len(uids)} kalimat terverifikasi ditandai selesai.")

    def _restore_citation_action(self) -> None:
        uid = self._selected_or_info("Klik dulu kalimat yang sitasinya ingin dipulihkan.")
        if uid is None:
            return
        sentence = self._sentence_by_uid(uid)
        if sentence is None:
            self._info.setText("Kalimat tidak ditemukan lagi.")
            return
        if sentence.citation:
            self._info.setText("Sitasi kalimat ini sudah aktif.")
            return
        self._swap_sentence(uid, [report.restore_citation(sentence)])
        self._after_structure_change("Sitasi kalimat dipulihkan.")

    def _paraphrase(self) -> None:
        uid = self._selected_or_info("Klik dulu kalimat yang ingin diparafrase.")
        if uid is None:
            return
        sentence = self._sentence_by_uid(uid)
        if sentence is None:
            self._info.setText("Kalimat tidak ditemukan lagi.")
            return
        sources = [record_to_source(record) for record in self.state.sources]
        texts = [record.get("text", "") for record in self.state.sources]
        self._info.setText("Memparafrase kalimat terpilih...")

        def work():
            return content.paraphrase(content.Paragraph([sentence]), sources, texts, self._client_factory())

        from .workers import run_in_thread

        self._thread, self._worker = run_in_thread(self, work)
        self._worker.result.connect(lambda paragraph: self._on_paraphrased(sentence.uid, paragraph))
        self._worker.error.connect(lambda _e: self._info.setText("Parafrase gagal."))

    def _on_paraphrased(self, uid: str, paragraph) -> None:
        new_sentences = list(paragraph.sentences)
        if not new_sentences:
            self._info.setText("Parafrase tidak mengubah apa pun.")
            return
        self._swap_sentence(uid, new_sentences)
        self._after_structure_change("Parafrase selesai; kalimat baru dihitung ulang statusnya.")

    # ------------------------------------------------------------ navigasi

    def _on_nav_clicked(self, item) -> None:
        row = self._nav.row(item)
        pos = self._section_positions.get(row)
        if pos is None:
            return
        cursor = self._document.textCursor()
        cursor.setPosition(pos)
        self._document.setTextCursor(cursor)
        self._document.ensureCursorVisible()
        block_layout = cursor.block().layout()
        self._document.verticalScrollBar().setValue(int(block_layout.position().y()))

    def _update_nav(self) -> None:
        self._nav.clear()
        status_by_uid = self._status_by_uid()
        for section_index, section in enumerate(self.state.sections):
            uids = [
                sentence.uid
                for paragraph in section.paragraphs
                for sentence in paragraph.sentences
            ]
            hijau = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_VERIFIED)
            merah = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_UNVERIFIED)
            abu = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_NON_FACTUAL)
            selesai = sum(1 for uid in uids if uid in self.state.done)
            parts = []
            if hijau:
                parts.append(f"✓ {hijau}")
            if merah:
                parts.append(f"⚠ {merah}")
            if abu:
                parts.append(f"{abu} bukan klaim")
            if selesai:
                parts.append(f"{selesai} selesai")
            self._nav.addItem(f"{section.title}: " + " · ".join(parts))

    # ------------------------------------------------------------ status bar

    def counts(self) -> dict:
        """Ringkasan status kalimat AI + jumlah selesai (parity chip Tk)."""
        dari_ai = [item for item in self.state.statuses if item.sentence.origin == "ai"]
        hijau = sum(1 for item in dari_ai if item.status == STATUS_VERIFIED)
        merah = sum(1 for item in dari_ai if item.status == STATUS_UNVERIFIED)
        abu = sum(1 for item in dari_ai if item.status == STATUS_NON_FACTUAL)
        semua_uid = {item.sentence.uid for item in self.state.statuses}
        selesai = len(set(self.state.done) & semua_uid)
        persen = round(100 * hijau / len(dari_ai)) if dari_ai else 0
        return {
            "total": len(dari_ai),
            "terverifikasi": hijau,
            "belum": merah,
            "bukan_klaim": abu,
            "selesai": selesai,
            "persen": persen,
        }

    def _update_status_bar(self) -> None:
        c = self.counts()
        if not c["total"]:
            self._status_bar.setText("Belum ada isi.")
            return
        self._status_bar.setText(
            f"{c['total']} kalimat · ✓ {c['terverifikasi']} · ⚠ {c['belum']} · "
            f"{c['bukan_klaim']} bukan klaim · terverifikasi {c['persen']}%"
        )

    def _update_controls(self) -> None:
        n = sum(1 for item in self.state.statuses if item.status == STATUS_VERIFIED)
        self._approve_button.setText(f"Setujui semua terverifikasi ({n})")
        self._approve_button.setEnabled(n > 0)
