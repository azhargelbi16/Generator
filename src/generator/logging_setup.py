"""Penyiapan log ke berkas tanpa pernah mencatat API key (15)."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_MAX_BYTES = 1_000_000
_BACKUPS = 3

_REDACTIONS = (
    (re.compile(r"sk-[A-Za-z0-9_-]{6,}"), "sk-***"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{4,}=*"), r"\1***"),
    (re.compile(r"(?i)((?:api[_-]?key|token)\s*[=:]\s*)[^\s,;]+"), r"\1***"),
)


class _RedactFilter(logging.Filter):
    """Ganti token rahasia di pesan log sebelum ditulis ke berkas."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            text = record.getMessage()
        except (TypeError, ValueError):
            text = str(record.msg)
        for pattern, replacement in _REDACTIONS:
            text = pattern.sub(replacement, text)
        record.msg = text
        record.args = ()
        return True


def setup_logging(log_path: Path) -> None:
    """Pasang handler berkas pada root logger, ganti handler lama agar tidak menggandakan."""
    log_path = Path(log_path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    handler = RotatingFileHandler(
        log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(_RedactFilter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
