"""Pembaca PDF: deteksi lapisan teks, ekstraksi, fallback OCR, dan metadata (12.1)."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from . import ocr
from .errors import SourceReadError

__all__ = [
    "SourceReadError",
    "has_text_layer",
    "extract_text",
    "extract_text_or_ocr",
    "extract_metadata",
    "extract_text_and_metadata",
]

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _open(pdf_path: Path) -> PdfReader:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise SourceReadError(f"Berkas PDF tidak ditemukan: {pdf_path}")
    try:
        return PdfReader(str(pdf_path))
    except Exception as exc:
        raise SourceReadError(f"PDF tidak bisa dibuka, mungkin rusak: {pdf_path}") from exc


def _page_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def has_text_layer(pdf_path: Path) -> bool:
    reader = _open(pdf_path)
    return any(_page_text(page).strip() for page in reader.pages)


def extract_text(pdf_path: Path) -> str:
    reader = _open(pdf_path)
    text = "\n".join(_page_text(page) for page in reader.pages).strip()
    if not text:
        raise SourceReadError(
            "PDF tidak punya teks. Tempel teks manual atau pakai berkas lain."
        )
    return text


def extract_text_or_ocr(pdf_path: Path) -> str:
    if has_text_layer(pdf_path):
        return extract_text(pdf_path)
    try:
        return ocr.ocr_pdf(pdf_path)
    except ocr.OcrError as exc:
        raise SourceReadError("OCR gagal, tempel teks manual.") from exc


def extract_metadata(pdf_path: Path) -> dict[str, str]:
    reader = _open(pdf_path)
    meta = reader.metadata or {}
    result: dict[str, str] = {}
    for key, field in (("/Author", "author"), ("/Title", "title"), ("/CreationDate", "date")):
        value = meta.get(key)
        if value:
            result[field] = str(value)
    pages = reader.pages
    if pages:
        match = _DOI_RE.search(_page_text(pages[0]))
        if match:
            result["doi"] = match.group(0)
    return result


def extract_text_and_metadata(pdf_path: Path) -> tuple[str, dict[str, str]]:
    """Ekstrak teks dan metadata PDF dalam SATU kali baca file (single-pass).

    Mencegah membaca dan mem-parsing berkas PDF berkali-kali untuk mempercepat
    proses penambahan sumber referensi secara drastis.
    """
    reader = _open(pdf_path)
    meta = reader.metadata or {}
    result: dict[str, str] = {}
    for key, field in (("/Author", "author"), ("/Title", "title"), ("/CreationDate", "date")):
        value = meta.get(key)
        if value:
            result[field] = str(value)

    pages = reader.pages
    page_texts: list[str] = []
    has_text = False
    for i, page in enumerate(pages):
        pt = _page_text(page)
        if pt.strip():
            has_text = True
        page_texts.append(pt)
        if i < 2 and "doi" not in result:
            match = _DOI_RE.search(pt)
            if match:
                result["doi"] = match.group(0)

    if has_text:
        text = "\n".join(page_texts).strip()
    else:
        try:
            text = ocr.ocr_pdf(pdf_path)
        except ocr.OcrError as exc:
            raise SourceReadError("OCR gagal, tempel teks manual.") from exc

    return text, result

