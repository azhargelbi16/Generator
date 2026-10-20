"""Review Hasil ala MS Word: dokumen dengan span kalimat bergaris (addendum D.1).

Tiap paragraf adalah satu QTextBlock; span kalimat disimpan di QTextBlockUserData
sehingga `uid_at(pos)` tidak butuh pemindaian teks. Kalimat "tidak_terverifikasi"
diberi SpellCheckUnderline merah. Render penuh hanya saat struktur berubah;
seleksi hanya menimpa format span yang bersangkutan.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import config, paths, report
from ..sources.records import record_to_source
from ..verification import (
    STATUS_NON_FACTUAL,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
)

_UNVERIFIED_RED = QColor("#ff0000")
_SELECTED_BG = QColor("#fff3bf")
_FONT_FAMILY = "Times New Roman"


class _BlockData(QTextBlockUserData):
    """Span kalimat per blok: daftar {start, end, uid, status} relatif ke blok."""

    def __init__(self, spans=None, heading: bool = False, section_index: int = -1):
        super().__init__()
        self.spans: list[dict] = spans or []
        self.heading = heading
        self.section_index = section_index


class _DocView(QTextEdit):
    """QTextEdit dokumen; klik kalimat memilih span dan memancarkan aktivasi."""

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


class ReviewPage(QWidget):
    """Halaman Review Hasil: dokumen, panel navigasi bab, status bar."""

    sentenceActivated = Signal(str)  # uid kalimat yang diklik/diaktifkan

    def __init__(self, state, cfg: config.Config | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._cfg = cfg or config.load_config(paths.CONFIG_PATH)
        self._selected: tuple[int, str] | None = None  # (block_number, uid)

        layout = QHBoxLayout(self)
        dokumen_box = QWidget()
        dokumen_layout = QVBoxLayout(dokumen_box)
        dokumen_layout.setContentsMargins(0, 0, 0, 0)
        self._document = _DocView(self)
        dokumen_layout.addWidget(self._document, stretch=1)
        self._status_bar = QLabel("Belum ada isi.")
        dokumen_layout.addWidget(self._status_bar)
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
        # Referensi kuat data blok: PySide6 tidak memindahkan kepemilikan
        # QTextBlockUserData, jadi bila wrapper Python di-GC objek C++ ikut
        # terhapus dan dokumen menyimpan pointer liar (crash heap saat teardown).
        self._block_data_refs: list[_BlockData] = []

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
        self.select(None)
        self._section_positions = {}
        self._block_data_refs = []
        document = self._document.document()
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()

        labels = report.labels_for(
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
                block_start = cursor.position()
                spans = []
                for sentence in paragraph.sentences:
                    start = cursor.position() - block_start
                    text = report.display_text(sentence, labels)
                    cursor.insertText(text)
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
                    total_sentences += 1
                for span in spans:
                    fmt_cursor = QTextCursor(document)
                    fmt_cursor.setPosition(block_start + span["start"])
                    fmt_cursor.setPosition(
                        block_start + span["end"], QTextCursor.MoveMode.KeepAnchor
                    )
                    fmt_cursor.setCharFormat(self._base_format(span["status"]))
                block_data = _BlockData(spans=spans, section_index=section_index)
                self._block_data_refs.append(block_data)
                cursor.block().setUserData(block_data)
        if not total_sentences:
            placeholder = QTextCharFormat()
            placeholder.setFont(QFont(_FONT_FAMILY, 14, QFont.Weight.Bold))
            cursor.insertText(
                "Belum ada isi. Isi outline, tambahkan sumber, lalu klik Generate isi laporan.",
                placeholder,
            )
        self._update_nav()
        self._update_status_bar()

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

    # -------------------------------------------------------------- seleksi

    def select(self, uid: str | None) -> None:
        """Sorot span kalimat (background kuning); None melepas sorotan."""
        self._clear_selection_format()
        self._selected_uid = uid
        if uid is None:
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
        status_by_uid = {item.sentence.uid: item.status for item in self.state.statuses}
        for section_index, section in enumerate(self.state.sections):
            uids = [
                sentence.uid
                for paragraph in section.paragraphs
                for sentence in paragraph.sentences
            ]
            hijau = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_VERIFIED)
            merah = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_UNVERIFIED)
            abu = sum(1 for uid in uids if status_by_uid.get(uid) == STATUS_NON_FACTUAL)
            parts = []
            if hijau:
                parts.append(f"✓ {hijau}")
            if merah:
                parts.append(f"⚠ {merah}")
            if abu:
                parts.append(f"{abu} bukan klaim")
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
