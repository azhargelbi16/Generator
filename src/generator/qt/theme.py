"""Tema visual Qt: kertas putih + aksen hijau pita Word (addendum A.6)."""

from __future__ import annotations

PAPER_GREEN = "#217346"

QSS = f"""
QWidget {{
    background-color: #ffffff;
    color: #1f1f1f;
    font-family: "Segoe UI";
    font-size: 9.5pt;
}}
QMainWindow::separator {{
    background: #e6e6e6;
    width: 3px;
    height: 3px;
}}
QTabWidget::pane {{
    border: 1px solid #d9d9d9;
}}
QTabBar::tab {{
    background: #f3f3f3;
    border: 1px solid #d9d9d9;
    border-bottom: none;
    padding: 6px 14px;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    border-bottom: 2px solid {PAPER_GREEN};
}}
QPushButton {{
    background: #ffffff;
    border: 1px solid #bfbfbf;
    border-radius: 3px;
    padding: 5px 12px;
}}
QPushButton:hover {{
    background: #f0f7f2;
    border-color: {PAPER_GREEN};
}}
QPushButton:default {{
    background: {PAPER_GREEN};
    color: #ffffff;
    border: none;
}}
QPushButton:disabled {{
    color: #a0a0a0;
    border-color: #e0e0e0;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    border: 1px solid #bfbfbf;
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: {PAPER_GREEN};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {PAPER_GREEN};
}}
QTableWidget, QTreeWidget, QListWidget {{
    border: 1px solid #d9d9d9;
    gridline-color: #eaeaea;
    selection-background-color: #dcede2;
    selection-color: #1f1f1f;
}}
QHeaderView::section {{
    background: #f3f3f3;
    border: none;
    border-bottom: 1px solid #d9d9d9;
    padding: 4px 6px;
}}
QStatusBar {{
    background: {PAPER_GREEN};
    color: #ffffff;
}}
QStatusBar QLabel {{
    background: transparent;
    color: #ffffff;
}}
QToolTip {{
    background: #1f1f1f;
    color: #ffffff;
    border: none;
    padding: 4px 6px;
}}
"""


def apply_theme(app) -> None:
    """Terapkan QSS ke QApplication."""
    app.setStyleSheet(QSS)
