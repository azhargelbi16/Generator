"""Cangkang aplikasi Qt: QMainWindow dengan 5 tab (addendum A.7).

Startup meniru gui/app.py: ensure_dirs_or_ask (fallback dialog folder data),
setup_logging, init_schema, load_config, peringatan API key kosong di status bar.
Modul aman diimpor tanpa display; widget hanya dibuat di build_main_window().
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QMainWindow

from .. import config as config_mod
from .. import database, logging_setup, paths

_API_KEY_HINT = "API key belum diisi; buka tab Pengaturan untuk mengisi endpoint dan API key."


class MainWindow(QMainWindow):
    """Jendela utama: menutup jendela menghentikan worker yang masih berjalan.

    Tanpa ini QThread yang di-parent ke widget ikut dimusnahkan saat jendela tutup
    dan Qt abort ("QThread: Destroyed while thread is still running").
    """

    def closeEvent(self, event) -> None:
        laporan = getattr(self, "_laporan", None)
        if laporan is not None:
            laporan.shutdown()
            laporan.controller.shutdown()
        super().closeEvent(event)


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
    """Bangun jendela utama dengan kelima tab asli yang sudah ter-wiring."""
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

    app = QApplication.instance()
    from .theme import apply_theme

    apply_theme(app)

    window = MainWindow()
    window.setWindowTitle("Generator Laporan")
    window.resize(980, 720)

    from .review_page import ReviewPage
    from .tab_data import DataTab
    from .tab_laporan import TabLaporan
    from .tab_settings import SettingsTab
    from .tab_template import TemplateTab

    tabs = QTabWidget()
    tabs.setDocumentMode(True)
    tabs.addTab(DataTab(db), "Data")
    tabs.addTab(TemplateTab(db), "Template")
    laporan = TabLaporan(db, paths.CONFIG_PATH)
    tabs.addTab(laporan, "Laporan")
    review = ReviewPage(laporan.controller, cfg=app_config)
    tabs.addTab(review, "Review Hasil")
    tabs.addTab(SettingsTab(paths.CONFIG_PATH), "Pengaturan")
    window.setCentralWidget(tabs)
    window.tabs = tabs

    # Integrasi alur: selesai generate -> muat ulang review (+auto review dosen bila config).
    laporan.generateFinished.connect(review.render_document)
    laporan.generateFinished.connect(review.on_generate_finished)
    window._laporan = laporan
    window._review = review

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
    from . import workers

    if workers.has_lingering():
        # Thread yang tak sempat berhenti dalam batas shutdown: lewati destructor
        # QThread saat interpreter teardown agar Qt tidak abort.
        os._exit(code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
