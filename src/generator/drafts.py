"""Penyimpanan draf laporan sebagai JSON di folder draf (8, 19).

Teks sumber hanya hidup di berkas draf ini, tidak pernah masuk database.
`done` berisi `uid` kalimat (bukan nomor posisi) supaya tanda selesai tetap
menempel pada kalimat yang benar walau urutan berubah; `sections` menyimpan
`uid`, `origin`, dan `citation` tiap kalimat agar asal dan identitasnya bisa
dibangun ulang persis saat draf dimuat kembali.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths
from .atomic import write_text as write_text_atomic

_DRAFT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


@dataclass
class DraftState:
    draft_id: str
    fields: dict
    sources: list[dict]
    sections: list[dict]
    done: list[str] = field(default_factory=list)


def _path(draft_id: str) -> Path:
    if not _DRAFT_ID.fullmatch(draft_id) or draft_id.split(".")[0].upper() in _RESERVED_NAMES:
        raise ValueError(f"draft_id tidak aman: {draft_id!r}")
    return paths.DRAFTS_DIR / f"{draft_id}.json"


def save_draft(state: DraftState) -> Path:
    paths.ensure_dirs()
    path = _path(state.draft_id)
    write_text_atomic(path, json.dumps(asdict(state), ensure_ascii=False, indent=2))
    return path


def load_draft(draft_id: str) -> DraftState | None:
    """Baca draf; kembalikan None bila tidak ada atau rusak."""
    path = _path(draft_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return DraftState(
        draft_id=str(raw.get("draft_id", draft_id)),
        fields=dict(raw.get("fields") or {}),
        sources=list(raw.get("sources") or []),
        sections=list(raw.get("sections") or []),
        done=[str(uid) for uid in (raw.get("done") or [])],
    )


def list_drafts() -> list[str]:
    paths.ensure_dirs()
    return sorted(path.stem for path in paths.DRAFTS_DIR.glob("*.json"))


def delete_draft(draft_id: str) -> None:
    path = _path(draft_id)
    if path.exists():
        path.unlink()
