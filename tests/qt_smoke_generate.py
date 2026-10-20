"""Smoke nyata Panggung Generate Qt: jendela sesungguhnya, klik Batal via QTest.

Dijalankan sebagai subprocess oleh tests/qt/test_qt_smoke_generate.py.
TIDAK boleh offscreen — smoke ini butuh sesi bermonitor.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow

from generator.qt.stage_page import StagePage

SOURCE_TEXT = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah secara berkelanjutan untuk masa depan"
)
TEKS_PELENGKAP = (
    "pengelolaan lahan sawah memerlukan perhatian serius dari semua pihak "
    "terkait hingga tingkat daerah di seluruh nusantara ini sekarang"
)
GOOD_QUOTE = "pertanian organik di indonesia sangat penting bagi petani"


def _bab_json(sentences):
    return json.dumps(
        {
            "sections": [
                {
                    "level": 1,
                    "title": "Bab",
                    "paragraphs": [
                        {
                            "sentences": [
                                {
                                    "text": text,
                                    "quote": GOOD_QUOTE,
                                    "source_ids": [0],
                                    "is_factual": True,
                                }
                                for text in sentences
                            ]
                        }
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )


class _State:
    def __init__(self):
        from generator.ai.citation import Author, Source

        self._sources = [
            Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal"),
            Source([Author("Manurung", "Ana")], "2021", "Judul Dua", "Jurnal"),
        ]
        self._texts = [SOURCE_TEXT, TEKS_PELENGKAP]

    def generate_plan(self):
        return ("Topik Laporan", ["Bab Satu", "Bab Dua"], self._sources, self._texts)


class FakeStreamClient:
    """chat_stream lambat supaya sempat menekan Batal selesai."""

    def __init__(self, payloads, delay=0.02):
        self._payloads = list(payloads)
        self._delay = delay
        self._calls = 0

    def chat_stream(self, messages, json_mode=False, cancel=None):
        payload = self._payloads[self._calls % len(self._payloads)]
        self._calls += 1
        for i in range(0, len(payload), 6):
            if cancel is not None and cancel.is_set():
                return
            time.sleep(self._delay)
            yield payload[i : i + 6]


def main() -> int:
    app = QApplication(sys.argv)
    stage = StagePage()
    stage._client_factory = lambda: FakeStreamClient(
        [
            _bab_json(["Kalimat pertama terlahir.", "Kalimat kedua terlahir.", "Kalimat ketiga terlahir."]),
            _bab_json(["Kalimat keempat terlahir.", "Kalimat kelima terlahir.", "Kalimat keenam terlahir."]),
        ]
    )
    window = QMainWindow()
    window.setWindowTitle("Smoke Panggung")
    window.setCentralWidget(stage)
    window.resize(900, 600)
    window.show()

    finished = []
    stage.finished.connect(lambda cancelled: finished.append(cancelled))
    stage.start_generate(_State(), max_prompt_chars=200)

    deadline = time.monotonic() + 20
    while stage._document.toPlainText().count("[") < 3 and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(20)
    assert stage._document.toPlainText().count("[") >= 1, "tidak ada kalimat tampil sebelum batal"

    QTest.mouseClick(stage._cancel_button, Qt.MouseButton.LeftButton)

    deadline = time.monotonic() + 20
    while not finished and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(20)
    assert finished == [True], f"finished={finished}"

    # Jendela tetap responsif setelah batal: event loop sehat, widget bisa diajak bicara.
    window.setWindowTitle("responsif")
    app.processEvents()
    assert window.windowTitle() == "responsif"
    QTest.qWait(100)
    app.processEvents()

    tampil = stage._document.toPlainText().count("[")
    assert 1 <= tampil < 6, f"kalimat tampil={tampil}"
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
