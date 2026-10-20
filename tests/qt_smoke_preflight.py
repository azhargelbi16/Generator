"""Smoke nyata Pemeriksaan Akhir Qt: dialog muncul saat ada temuan, diisi via klik QTest.

Dijalankan sebagai subprocess oleh tests/qt/test_qt_smoke_preflight.py.
TIDAK boleh offscreen — butuh sesi bermonitor. `os.startfile` di-patch agar
Word sungguhan tidak dibuka; `paths.OUTPUT_DIR`/`DRAFTS_DIR` diarahkan ke
folder temp sehingga `data\` tidak tersentuh.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from docx import Document

from generator import config, paths, report
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.document import template as template_mod
from generator.qt import preflight_dialog as pd
from generator.qt.review_page import ReviewPage
from generator.sources.records import source_to_record
from generator.verification import verify_sections

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"


def _make_docx(path, markers):
    doc = Document()
    for marker in markers:
        doc.add_paragraph(marker)
    doc.save(path)


class _State:
    def __init__(self, tmp: Path):
        self.sources = [
            source_to_record(
                Source([Author("NemÃ©nyi", "Gábor")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        self.done = set()
        self.fields = {"judul": 'Laporan: "Smoke" Dosen?', "dosen": "Dr. A", "matkul": "Agro", "logo": ""}
        kalimat = [
            Sentence(text="Kalimat pertama smoke preflight.", quote=QUOTED, source_ids=[0]),
            Sentence(text="Kalimat kedua smoke preflight.", quote=QUOTED, source_ids=[0]),
        ]
        self.sections = [Section(1, "Bab Smoke", [Paragraph(kalimat)])]
        self.statuses = verify_sections(self.sections, {0: SOURCE_TEXT})
        template_path = tmp / "tpl.docx"
        _make_docx(template_path, template_mod.REQUIRED_PLACEHOLDERS)
        self.template = SimpleNamespace(path=str(template_path))
        self._logo_list = []  # logo belum dipilih -> temuan
        self._db = SimpleNamespace(
            get_profil=lambda: SimpleNamespace(nama="Budi", nim="123", prodi="Agro")
        )
        self._config_path = tmp / "config.json"


def main() -> int:
    app = QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp(prefix="gen-smoke-preflight-"))
    paths.OUTPUT_DIR = tmp / "output"
    paths.DRAFTS_DIR = tmp / "drafts"
    config.save_config(config.default_config(), tmp / "config.json")

    state = _State(tmp)
    page = ReviewPage(state, cfg=config.default_config())
    page.render_document()
    window = QMainWindow()
    window.setWindowTitle("Smoke Preflight")
    window.setCentralWidget(page)
    window.resize(1100, 700)
    window.show()
    QTest.qWait(100)

    dibuka = []
    pd.os.startfile = lambda p: dibuka.append(p)  # jangan buka Word sungguhan
    nama_berkas_holder: list[str] = []

    def _isi_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, pd.PreflightDialog), f"dialog aktif: {type(dialog)}"
        assert dialog._fix_button.isVisible(), "tombol perbaiki nama tidak tampil"
        dialog._fix_button.click()
        assert "Neményi" in dialog._names_label.text()
        dialog._tidy_button.click()
        nama_berkas_holder.append(dialog.filename)
        assert dialog.filename, "nama berkas kosong setelah dirapikan"
        dialog._save_open_button.click()

    QTimer.singleShot(1000, _isi_dialog)

    tombol = next(
        b for b in page._controls.findChildren(QPushButton) if "Simpan DOCX" in b.text()
    )
    QTest.mouseClick(tombol, Qt.MouseButton.LeftButton, pos=tombol.rect().center())
    QTest.qWait(200)

    assert nama_berkas_holder, "dialog tidak pernah terisi"
    hasil = paths.OUTPUT_DIR / f"{nama_berkas_holder[0]}.docx"
    assert hasil.is_file(), f"DOCX tidak ada: {hasil}"
    assert dibuka == [hasil], f"opener={dibuka}"
    assert "DOCX tersimpan" in page._info.text()
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
