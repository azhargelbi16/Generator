"""Perbaikan teks mojibake dari respons AI (desain seksi 4).

Mojibake terjadi ketika UTF-8 terbaca sebagai latin-1 lalu disimpan ulang,
mis. "Neményi" menjadi "NemÃ©nyi". Perbaikan hanya diterima bila hasilnya
bersih; teks rusak berlapis dibiarkan apa adanya ketimbang ditebak.
"""
from __future__ import annotations

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
