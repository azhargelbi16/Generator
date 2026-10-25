"""Penyimpanan draf laporan sebagai JSON di folder draf (8, 19).

Teks sumber hanya hidup di berkas draf ini, tidak pernah masuk database.
Isi draf dienkripsi menggunakan Windows DPAPI (CryptProtectData) agar teks sumber
tidak tersimpan polos di disk. Fallback polos tersedia bila DPAPI tidak aktif.
Draf lama (JSON polos) tetap kompatibel dan dapat dibaca kembali.
`done` berisi `uid` kalimat (bukan nomor posisi) supaya tanda selesai tetap
menempel pada kalimat yang benar walau urutan berubah; `sections` menyimpan
`uid`, `origin`, dan `citation` tiap kalimat agar asal dan identitasnya bisa
dibangun ulang persis saat draf dimuat kembali.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths
from .atomic import write_text as write_text_atomic
from .textutil import sanitize_filename

log = logging.getLogger("generator.drafts")

# Autosave UI bisa beriringan dengan penyimpanan dari thread generasi;
# di Windows, os.replace pada berkas yang sedang dibaca thread lain bisa
# melempar PermissionError sesaat. Satu kunci global menjaga baca-tulis
# draf menjadi atomik antar-thread.
_IO_LOCK = threading.Lock()

_DRAFT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _dpapi_protect(data: bytes) -> bytes | None:
    """Enkripsi bytes menggunakan Windows DPAPI CryptProtectData."""
    if not hasattr(ctypes, "windll"):
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        data_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)),
        )
        data_out = _DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(data_in),
            "draft_protection",
            None,
            None,
            None,
            0,
            ctypes.byref(data_out),
        ):
            return None
        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            kernel32.LocalFree(data_out.pbData)
    except Exception as exc:
        log.warning("Enkripsi DPAPI gagal: %s", exc)
        return None


def _dpapi_unprotect(data: bytes) -> bytes | None:
    """Dekripsi bytes menggunakan Windows DPAPI CryptUnprotectData."""
    if not hasattr(ctypes, "windll"):
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        data_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)),
        )
        data_out = _DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(data_out),
        ):
            return None
        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            kernel32.LocalFree(data_out.pbData)
    except Exception as exc:
        log.warning("Dekripsi DPAPI gagal: %s", exc)
        return None


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
    with _IO_LOCK:
        paths.ensure_dirs()
        path = _path(state.draft_id)
        raw_json = json.dumps(asdict(state), ensure_ascii=False, indent=2)
        raw_bytes = raw_json.encode("utf-8")

        encrypted_blob = _dpapi_protect(raw_bytes)
        if encrypted_blob is not None:
            envelope = {
                "version": 2,
                "encrypted": True,
                "payload": base64.b64encode(encrypted_blob).decode("ascii"),
            }
            write_text_atomic(path, json.dumps(envelope, indent=2))
        else:
            # Fallback polos hanya bila DPAPI tidak tersedia, catat di log tanpa isi data
            log.warning("DPAPI tidak tersedia; menyimpan draf dalam format polos.")
            write_text_atomic(path, raw_json)
        return path


def load_draft(draft_id: str) -> DraftState | None:
    """Baca draf; kembalikan None bila tidak ada atau rusak."""
    with _IO_LOCK:
        return _load_draft_unlocked(draft_id)


def _load_draft_unlocked(draft_id: str) -> DraftState | None:
    path = _path(draft_id)
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        raw = json.loads(content)
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None

    # Dekripsi draf bila berformat terenkripsi
    if raw.get("encrypted") and "payload" in raw:
        try:
            enc_bytes = base64.b64decode(raw["payload"])
            dec_bytes = _dpapi_unprotect(enc_bytes)
            if dec_bytes is None:
                log.error("Gagal mendekripsi draf dengan DPAPI.")
                return None
            raw = json.loads(dec_bytes.decode("utf-8"))
        except Exception as exc:
            log.error("Gagal membaca draf terenkripsi: %s", exc)
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


# --- Rekonsiliasi draf: kebijakan merge/preserve/clear/archive terpusat ------
#
# Tab Laporan memiliki fields+sources; Tab Review memiliki sections+done.
# Keduanya mengirim payload parsial ke draf yang sama, sehingga arti
# "hilang/kosong" harus ditafsirkan di SATU tempat yang bisa diuji langsung
# (dulu tersebar di ApiBridge.save_active_draft dan mudah salah tafsir).


def _iter_sentences(state: DraftState):
    for section in state.sections:
        for paragraph in section.get("paragraphs", []) if isinstance(section, dict) else []:
            for sentence in paragraph.get("sentences", []) or []:
                yield sentence


def has_content(state: DraftState) -> bool:
    """True bila draf menyimpan sesuatu yang layak diarsipkan sebelum dihapus:
    ada kalimat, sumber, atau judul."""
    return bool(
        any(_iter_sentences(state))
        or state.sources
        or (state.fields.get("JUDUL") or "").strip()
    )


def has_review_progress(state: DraftState) -> bool:
    """True bila draf punya kemajuan review yang akan hilang bila ditimpa
    hasil generasi baru: ada tanda selesai (done) atau kalimat hasil suntingan
    manual (origin "edit"). Draf yang baru digenerate tanpa disentuh tidak
    dihitung — regenerate tidak menumpuk arsip."""
    if state.done:
        return True
    return any(sentence.get("origin") == "edit" for sentence in _iter_sentences(state))


def archive_draft(state: DraftState, *, prefix: str) -> Path | None:
    """Simpan salinan draf sebagai arsip bertanda waktu `arsip_{prefix}_…`.

    Nama arsip memakai judul laporan (dibersihkan, maks 30 karakter) agar
    mudah dikenali di folder draf. Kembalikan path arsip.
    """
    judul = sanitize_filename(state.fields.get("JUDUL") or "draf", max_len=30)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = DraftState(
        draft_id=f"{prefix}_{stamp}_{judul or 'draf'}",
        fields=dict(state.fields),
        sources=list(state.sources),
        sections=list(state.sections),
        done=list(state.done),
    )
    return save_draft(archive)


def reconcile_draft(draft_id: str, incoming: dict) -> DraftState:
    """Gabungkan payload parsial `incoming` ke draf tersimpan lalu simpan.

    Kebijakan (dipertahankan persis agar draf JSON lama dan perilaku UI
    tidak berubah):

    - ``sections`` hilang → pertahankan; ada → pakai apa adanya; kosong
      TANPA kunci ``clear_sections`` → pertahankan yang tersimpan; kosong
      DENGAN ``clear_sections`` → benar-benar dibersihkan.
    - ``done`` → kebijakan sama dengan ``sections``.
    - ``fields`` → dict digabung per-kunci di atas yang tersimpan; kunci
      lain di payload tidak menghapus apa pun.
    - ``sources`` hilang → pertahankan; ada → pakai apa adanya; kosong
      dan payload TIDAK membawa ``fields`` → pertahankan (pola payload
      Tab Review yang tidak mengelola sumber); kosong dengan ``fields``
      → dibersihkan (payload Studio berhak menghapus sumber eksplisit).
    """
    existing = load_draft(draft_id)

    incoming_sections = incoming.get("sections")
    if incoming_sections is None or (
        len(incoming_sections) == 0
        and existing
        and existing.sections
        and not incoming.get("clear_sections")
    ):
        sections = list(existing.sections) if existing else []
    else:
        sections = incoming_sections or []

    incoming_done = incoming.get("done")
    if incoming_done is None or (
        len(incoming_done) == 0
        and existing
        and existing.done
        and not incoming.get("clear_sections")
    ):
        done = list(existing.done) if existing else []
    else:
        done = list(incoming_done)

    fields = dict(existing.fields) if existing and existing.fields else {}
    incoming_fields = incoming.get("fields")
    if isinstance(incoming_fields, dict):
        fields.update(incoming_fields)

    incoming_sources = incoming.get("sources")
    if incoming_sources is None or ("fields" not in incoming and not incoming_sources):
        sources = list(existing.sources) if existing else []
    else:
        sources = list(incoming_sources)

    merged = DraftState(
        draft_id=draft_id,
        fields=fields,
        sources=sources,
        sections=sections,
        done=done,
    )
    save_draft(merged)
    return merged
