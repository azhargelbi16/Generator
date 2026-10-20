"""Smoke QTest menyeluruh aplikasi Qt (padanan tests/gui_smoke.py).

Jendela SESUNGGUHNYA (bukan offscreen): tab ada, sub-tab Data benar, tombol
tak terpotong di tiap tab, tambah dosen tersimpan lintas aplikasi (jendela
ditutup lalu dibuka lagi dari database yang sama).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractButton

from generator import config, paths

paths.set_data_dir(tempfile.mkdtemp(prefix="qt-smoke-all-"))
paths.ensure_dirs()
config.save_config(config.default_config(), paths.CONFIG_PATH)

from generator.database import Database, Profil  # noqa: E402
from generator.qt.app import build_main_window  # noqa: E402


def _window(db):
    app_config = config.load_config(paths.CONFIG_PATH)
    window = build_main_window(db, app_config)
    window.resize(1100, 800)
    window.show()
    QTest.qWait(100)
    return window


def _tombol_tidak_terpotong(window, label: str) -> None:
    batas = window.mapToGlobal(window.rect().bottomLeft()).y()
    for widget in window.findChildren(QAbstractButton):
        if not widget.isVisible():
            continue
        bawah = widget.mapToGlobal(widget.rect().bottomLeft()).y()
        assert bawah <= batas + 2, f"Tombol {label} terpotong: {widget.text()!r} ({bawah} > {batas})"


def main() -> int:
    app = QApplication(["smoke-all"])

    db = Database(paths.DB_PATH)
    db.init_schema()
    db.set_profil(Profil(nama="Smoke Qt", nim="2515109999", prodi="Ilmu Tanah"))

    # 1) Jendela pertama: tab + sub-tab + tombol tak terpotong.
    window = _window(db)
    tabs = window.tabs
    names = [tabs.tabText(i) for i in range(tabs.count())]
    assert names == ["Data", "Template", "Laporan", "Review Hasil", "Pengaturan"], names
    assert window.windowTitle() == "Generator Laporan"
    print("1. Lima tab dengan nama Tk terpasang")

    data_tab = tabs.widget(0)
    inner_names = [data_tab.inner.tabText(i) for i in range(data_tab.inner.count())]
    assert inner_names == ["Profil Mahasiswa", "Dosen", "Mata Kuliah", "Logo"], inner_names
    print("2. Sub-tab Data lengkap:", inner_names)

    for i, nama in enumerate(names):
        tabs.setCurrentIndex(i)
        QTest.qWait(50)
        _tombol_tidak_terpotong(window, nama)
    print("3. Tidak ada tombol terpotong di kelima tab")

    # 4) Tambah satu dosen lewat panel GUI.
    data_tab.inner.setCurrentIndex(1)
    QTest.qWait(50)
    panel = data_tab.dosen_panel
    panel._vars["nama"].setText("Siti Aminah")
    panel._vars["gelar"].setText("S.P.")
    panel._vars["identitas"].setText("19900101")
    tombol_tambah = next(b for b in panel.findChildren(QAbstractButton) if b.text() == "Tambah")
    tombol_tambah.click()
    QTest.qWait(50)
    assert panel._table.rowCount() == 1, "Dosen tidak muncul di tabel"
    print("4. Dosen 'Siti Aminah' ditambahkan lewat GUI")

    window.close()
    db.close()

    # 5) Jendela kedua (aplikasi dibuka ulang): dosen tersimpan.
    db2 = Database(paths.DB_PATH)
    window2 = _window(db2)
    data2 = window2.tabs.widget(0)
    data2.inner.setCurrentIndex(1)
    QTest.qWait(50)
    panel2 = data2.dosen_panel
    assert panel2._table.rowCount() == 1, "Dosen hilang setelah aplikasi dibuka ulang"
    assert panel2._table.item(0, 0).text() == "Siti Aminah"
    print("5. Dosen tersimpan lintas aplikasi")
    window2.close()
    db2.close()

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
