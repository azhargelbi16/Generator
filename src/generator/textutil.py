"""Perbaikan teks mojibake dari respons AI (desain seksi 4).

Mojibake terjadi ketika UTF-8 terbaca sebagai latin-1 lalu disimpan ulang,
mis. "Neményi" menjadi "NemÃ©nyi". Perbaikan hanya diterima bila hasilnya
bersih; teks rusak berlapis dibiarkan apa adanya ketimbang ditebak.
"""
from __future__ import annotations

import re

_SUSPECT = ("Ã", "Â", "â€")


def has_mojibake(text: str) -> bool:
    """True bila teks memuat penanda khas mojibake UTF-8/latin-1."""
    return any(marker in text for marker in _SUSPECT)


def repair_mojibake(text: str) -> str:
    """Kembalikan teks yang sudah dibersihkan, atau teks asli bila tak yakin.

    Perbaikan diterima hanya bila hasil decode lolos UTF-8, bebas penanda
    mojibake, dan panjangnya wajar (0,5x-2x teks asli).
    """
    if not has_mojibake(text):
        return text
    try:
        candidate = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if has_mojibake(candidate):
        return text
    if not (0.5 * len(text) <= len(candidate) <= 2 * len(text)):
        return text
    return candidate

# --- Nama berkas aman Windows (dipakai ekspor DOCX dan penamaan arsip draf) --

_CONTROL_FILENAME = re.compile(r"[\x00-\x1f\x7f]")
_ILLEGAL_FILENAME = re.compile(r'[<>:"/\\|?*]')
_UNDERSCORE_RUN = re.compile(r"_{2,}")


def sanitize_filename(judul: str, max_len: int = 80) -> str:
    """Nama berkas aman untuk Windows: tanpa karakter ilegal atau kontrol, titik
    diganti garis bawah ("4.0" -> "4_0"), spasi digarisbawahi, rapatkan garis
    bawah, potong `max_len`, fallback "laporan" bila kosong."""
    text = _CONTROL_FILENAME.sub("", judul)
    text = _ILLEGAL_FILENAME.sub("", text)
    text = text.replace(".", "_")
    text = "_".join(text.split())
    text = _UNDERSCORE_RUN.sub("_", text).strip("_")
    text = text[:max_len] or "laporan"
    if text.upper() in _RESERVED_WIN_NAMES:
        text += "_"
    return text


_RESERVED_WIN_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
