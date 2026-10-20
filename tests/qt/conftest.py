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


@pytest.fixture()
def db_tmp(tmp_path, monkeypatch):
    """Database di folder tempfile; seluruh path data diarahkan ke sana."""
    from generator import database, paths

    monkeypatch.setattr(paths, "DATA_DIR", tmp_path)
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path / "logos")
    monkeypatch.setattr(paths, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(paths, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(paths, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(paths, "LOG_PATH", tmp_path / "app.log")
    for name in ("logos", "templates", "drafts"):
        (tmp_path / name).mkdir(exist_ok=True)
    db = database.Database(paths.DB_PATH)
    db.init_schema()
    yield db
    db.close()


@pytest.fixture()
def cfg_default():
    from generator.config import default_config

    return default_config()

