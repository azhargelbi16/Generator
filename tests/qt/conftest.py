"""Harness pytest untuk GUI Qt: offscreen, tanpa pytest-qt.

`QT_QPA_PLATFORM` dipaksa di module level — sebelum PySide6 pernah diimpor —
supaya tes bisa jalan tanpa layar (CI/mesin tanpa monitor).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()
