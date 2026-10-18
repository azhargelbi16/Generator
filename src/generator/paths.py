"""Lokasi folder data aplikasi, dengan fallback bila folder utama tidak bisa dipakai (12.8)."""

from __future__ import annotations

from pathlib import Path


class PathsError(Exception):
    """Folder data tidak bisa dibuat atau dipakai."""


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"
LOGOS_DIR = DATA_DIR / "logos"
TEMPLATES_DIR = DATA_DIR / "templates"
DRAFTS_DIR = DATA_DIR / "drafts"
OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "app.log"


def ensure_dirs() -> None:
    """Buat semua folder data. Lempar `PathsError` bila gagal."""
    for folder in (DATA_DIR, LOGOS_DIR, TEMPLATES_DIR, DRAFTS_DIR, OUTPUT_DIR):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PathsError(f"Folder data tidak bisa dibuat: {folder}") from exc


def set_data_dir(base: Path) -> None:
    """Pindahkan semua path data ke `base` (dipakai saat folder utama tak bisa ditulis)."""
    global DATA_DIR, DB_PATH, LOGOS_DIR, TEMPLATES_DIR, DRAFTS_DIR, CONFIG_PATH, LOG_PATH
    base = Path(base)
    DATA_DIR = base
    DB_PATH = base / "app.db"
    LOGOS_DIR = base / "logos"
    TEMPLATES_DIR = base / "templates"
    DRAFTS_DIR = base / "drafts"
    CONFIG_PATH = base / "config.json"
    LOG_PATH = base / "app.log"
