"""Cangkang aplikasi Qt: QMainWindow dengan 5 tab (addendum A.7).

Startup meniru gui/app.py: ensure_dirs_or_ask (fallback dialog folder data),
setup_logging, init_schema, load_config, peringatan API key kosong di status bar.
Modul aman diimpor tanpa display; widget hanya dibuat di build_main_window().
"""

from __future__ import annotations

import sys

from .. import config as config_mod
from .. import database, logging_setup, paths

_API_KEY_HINT = "API key belum diisi; buka tab Pengaturan untuk mengisi endpoint dan API key."


def _ensure_dirs_or_ask() -> bool:
    """Siapkan folder data; bila gagal, minta user memilih folder lain (12.8)."""
    try:
        paths.ensure_dirs()
        return True
    except paths.PathsError:
        pass
    from PySide6.QtWidgets import QApplication, QFileDialog

    app = QApplication.instance() or QApplication([])
    chosen = QFileDialog.getExistingDirectory(
        None,
        "Folder data bawaan tidak bisa ditulis. Pilih folder penyimpanan data.",
    )
    if not chosen:
        return False
    try:
        paths.set_data_dir(chosen)
        paths.ensure_dirs()
    except paths.PathsError:
        return False
    return True


def build_main_window(db, app_config) -> "QMainWindow":
    """Bangun jendela utama; tab Laporan/Review Hasil placeholder sampai fase 3-4."""
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget

    app = QApplication.instance()
    from .theme import apply_theme

    apply_theme(app)

    window = QMainWindow()
    window.setWindowTitle("Generator Laporan")
    window.resize(980, 720)

    tabs = QTabWidget()
    tabs.setDocumentMode(True)
    tabs.addTab(QWidget(), "Data")  # diganti DataTab pada Task 2.3
    tabs.addTab(QWidget(), "Template")  # diganti TemplateTab pada Task 2.4
    tabs.addTab(QWidget(), "Laporan")  # setup + Panggung pada Task 3.x
    tabs.addTab(QWidget(), "Review Hasil")  # ReviewPage pada Task 4.x
    tabs.addTab(QWidget(), "Pengaturan")  # SettingsTab pada Task 2.5
    window.setCentralWidget(tabs)
    window.tabs = tabs

    if not app_config.ai_api_key:
        window.statusBar().showMessage(_API_KEY_HINT)

    window._db = db
    window._app_config = app_config
    return window


def main() -> int:
    if not _ensure_dirs_or_ask():
        print("Folder data tidak tersedia. Aplikasi berhenti.")
        return 1
    logging_setup.setup_logging(paths.LOG_PATH)

    db = database.Database(paths.DB_PATH)
    db.init_schema()

    app_config = config_mod.load_config(paths.CONFIG_PATH)

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = build_main_window(db, app_config)
    window.show()
    code = app.exec()
    db.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
