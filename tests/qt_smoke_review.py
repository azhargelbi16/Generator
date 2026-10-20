"""Smoke nyata Review Hasil Qt: klik kalimat via QTest pada jendela sesungguhnya.

Dijalankan sebagai subprocess oleh tests/qt/test_qt_smoke_review.py.
TIDAK boleh offscreen — smoke ini butuh sesi bermonitor.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.config import default_config
from generator.qt.review_page import ReviewPage
from generator.sources.records import source_to_record
from generator.verification import verify_sections

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"


class _State:
    def __init__(self):
        self.sources = [
            source_to_record(
                Source([Author("Santoso", "Budi")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        self.done = set()
        self.fields = {"judul": "Smoke Review"}
        kalimat = [
            Sentence(text="Kalimat pertama untuk smoke.", quote=QUOTED, source_ids=[0]),
            Sentence(text="Kalimat kedua untuk smoke.", quote=QUOTED, source_ids=[0]),
            Sentence(
                text="Klaim tanpa dasar untuk smoke.",
                quote="tak ada di sumber",
                source_ids=[0],
            ),
        ]
        self.sections = [Section(1, "Bab Smoke", [Paragraph(kalimat)])]
        self.sentences = kalimat
        self.statuses = verify_sections(self.sections, {0: SOURCE_TEXT})

    def _save_draft(self):
        pass


def main() -> int:
    app = QApplication(sys.argv)
    state = _State()
    page = ReviewPage(state, cfg=default_config())
    page.render_document()
    window = QMainWindow()
    window.setWindowTitle("Smoke Review")
    window.setCentralWidget(page)
    window.resize(1100, 700)
    window.show()
    QTest.qWait(100)

    # Klik kalimat pertama pada posisi teksnya di viewport.
    uid = state.sentences[0].uid
    block = page._document.document().firstBlock()
    span = None
    while block.isValid():
        data = block.userData()
        if data is not None:
            for candidate in data.spans:
                if candidate["uid"] == uid:
                    span = (block, candidate)
                    break
        if span is not None:
            break
        block = block.next()
    assert span is not None
    cursor = QTextCursor(span[0])
    cursor.setPosition(span[0].position() + (span[1]["start"] + span[1]["end"]) // 2)
    rect = page._document.cursorRect(cursor)
    diklik = []
    page.sentenceActivated.connect(lambda u: diklik.append(u))
    QTest.mouseClick(
        page._document.viewport(),
        Qt.MouseButton.LeftButton,
        pos=rect.center(),
    )
    QTest.qWait(50)

    assert diklik == [uid], f"sentenceActivated={diklik}"
    assert page._selected_uid == uid
    assert page._toolbar.isVisible()

    # Klik "Tandai selesai" pada toolbar melayang.
    tombol = next(
        b for b in page._toolbar.findChildren(QPushButton) if "Tandai selesai" in b.text()
    )
    QTest.mouseClick(tombol, Qt.MouseButton.LeftButton, pos=tombol.rect().center())
    QTest.qWait(50)

    assert uid in state.done
    assert page.counts()["selesai"] == 1
    assert page._info.text() == "Kalimat ditandai selesai."
    assert "1 selesai" in page._nav.item(0).text()
    assert "3 kalimat" in page._status_bar.text()

    window.setWindowTitle("responsif")
    app.processEvents()
    assert window.windowTitle() == "responsif"
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
