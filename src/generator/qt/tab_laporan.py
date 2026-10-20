"""Tab Laporan Qt: setup sumber/outline + Panggung Penuh bertumpuk (integrasi).

Selama generate, tampilan berpindah ke StagePage (dokumen menulis dirinya,
parity perilaku Tk); selesai/batal -> hasil kembali ke ReportController
(state review), tampilan kembali ke setup, sinyal `generateFinished` memicu
pemuatan ulang halaman Review.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from ..database import Database
from .report_controller import ReportController
from .stage_page import StagePage


class TabLaporan(QWidget):
    """Tab "Laporan": kolom sumber + pengaturan; state di ReportController."""

    generateFinished = Signal()

    def __init__(self, db: Database, config_path: Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = ReportController(db, config_path, self)
        self.stage = StagePage()
        self._stack = QStackedWidget()
        self._stack.addWidget(self.controller.setup_page)
        self._stack.addWidget(self.stage)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self.controller.generateRequested.connect(self._mulai_generate)
        self.stage.finished.connect(self._selesai_generate)

    def shutdown(self) -> None:
        """Batalkan generate yang berjalan sebelum jendela ditutup."""
        self.stage.shutdown()

    def _mulai_generate(self) -> None:
        self._stack.setCurrentWidget(self.stage)
        self.stage.start_generate(self.controller)

    def _selesai_generate(self, cancelled: bool) -> None:
        """Hasil (parsial bila batal) kembali ke controller; review siap dimuat ulang."""
        if self.stage.result_sections is not None:
            self.controller.sections = self.stage.result_sections
            self.controller._reverify()
            self.controller._save_draft()
        self._stack.setCurrentWidget(self.controller.setup_page)
        self.generateFinished.emit()
