"""Perbaikan teks mojibake dari respons AI (desain seksi 4).

Mojibake terjadi ketika UTF-8 terbaca sebagai latin-1 lalu disimpan ulang,
mis. "Neményi" menjadi "NemÃ©nyi". Perbaikan hanya diterima bila hasilnya
bersih; teks rusak berlapis dibiarkan apa adanya ketimbang ditebak.
"""
from __future__ import annotations

import hashlib
import re

_SUSPECT = ("Ã", "Â", "â€")


def has_mojibake(text: str) -> bool:
    """True bila teks memuat penanda khas mojibake UTF-8/latin-1."""
    return any(marker in text for marker in _SUSPECT)


def repair_mojibake(text: str) -> str:
    """Kembalikan teks yang sudah dibersihkan, atau teks asli bila tak yakin.

    Perbaikan diterima hanya bila hasil decode lolos UTF-8, bebas penanda
    mojibake, dan panjangnya wajar (0,5x-2x teks asli).
    Juga membersihkan replacement character (\ufffd) dan tanda kutip rusak.
    """
    if not text:
        return ""
    text = re.sub(r"(\w+s)[\ufffd](\s|$)", r"\1'\2", text, flags=re.I)
    text = re.sub(r"(\w+)[\ufffd](s|d|t|re|ve|ll|m)\b", r"\1'\2", text, flags=re.I)
    text = text.replace("\ufffd", "").replace("", "")
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
_FILENAME_HASH_LEN = 8


def _title_hash(text: str) -> str:
    """Penanda pendek deterministik (8 karakter hex) dari judul yang dipotong."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:_FILENAME_HASH_LEN]


def _truncate_word_boundary(text: str, budget: int) -> str:
    """Potong ``text`` maksimal ``budget`` karakter PADA BATAS KATA.

    Kata pada nama berkas dipisah garis bawah; bila titik potong jatuh di tengah
    kata, potongan kata terakhir dibuang supaya tidak ada nama menggantung.
    """
    if budget <= 0:
        return ""
    if len(text) <= budget:
        return text
    cut = text[:budget]
    if "_" in cut and text[budget : budget + 1] != "_":
        cut = cut[: cut.rfind("_")]
    return cut.rstrip("_")


def sanitize_filename(judul: str, max_len: int = 80) -> str:
    """Nama berkas aman untuk Windows: tanpa karakter ilegal/kontrol, titik
    diganti garis bawah ("4.0" -> "4_0"), spasi digarisbawahi, rapatkan garis
    bawah, fallback "laporan" bila kosong.

    Bila hasil lebih panjang dari ``max_len``, nama dipotong pada BATAS KATA lalu
    ditambah penanda hash 8 karakter dari judul lengkap: hasilnya tetap unik,
    tidak melebihi batas, dan tidak berakhir sebagai potongan kata menggantung.
    """
    text = _CONTROL_FILENAME.sub("", judul)
    text = _ILLEGAL_FILENAME.sub("", text)
    text = text.replace(".", "_")
    text = "_".join(text.split())
    text = _UNDERSCORE_RUN.sub("_", text).strip("_")
    if not text:
        return "laporan"
    if len(text) > max_len:
        suffix = "_" + _title_hash(text)
        budget = max_len - len(suffix)
        body = _truncate_word_boundary(text, budget)
        if body:
            text = f"{body}{suffix}"
        else:
            # Batas terlalu kecil untuk pemisah kata: potong keras, tanpa penanda.
            hard = text[:budget] if budget > 0 else text
            text = (hard + (suffix if budget > 0 else ""))[:max_len]
    if text.upper() in _RESERVED_WIN_NAMES:
        text += "_"
    return text


_RESERVED_WIN_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
