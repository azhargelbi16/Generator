"""Kesalahan bersama saat membaca sumber, dipakai pdf_reader dan web_reader."""

from __future__ import annotations


class SourceReadError(Exception):
    """Sumber tidak bisa dibaca (PDF rusak, pindaian gagal di-OCR, atau situs menolak)."""
