"""Tab Laporan Qt: wadah halaman setup dari ReportController (Task 3.1)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..database import Database
from .report_controller import ReportController


class TabLaporan(QWidget):
    """Tab "Laporan": kolom sumber + pengaturan; state di ReportController."""

    def __init__(self, db: Database, config_path: Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = ReportController(db, config_path, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.controller.setup_page)
