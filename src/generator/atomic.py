"""Penulisan berkas atomik: tulis ke berkas sementara lalu ganti nama.

Dipakai untuk data yang tidak boleh setengah jadi (config dan draf): bila
penulisan gagal, berkas lama tetap utuh dan berkas sementara dibersihkan.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Tulis `text` ke `path` secara atomik."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    try:
        Path(temporary).write_text(text, encoding=encoding)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
