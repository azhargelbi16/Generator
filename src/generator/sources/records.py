"""Rekord sumber netral (tanpa GUI): konversi Source <-> dict draf, metadata.

Dipakai gui/tab_report.py (Tk) dan qt/report_controller.py (Qt); ditaruh di
sini supara modul Qt tidak perlu mengimpor tkinter.
"""

from __future__ import annotations

import re

from ..ai.citation import Author, Source

DRAFT_ACTIVE_ID = "aktif"

# Ambang cakupan isi sumber (karakter). Di bawah ini, teks yang tersimpan
# kemungkinan besar hanya abstrak/metadata — AI tidak punya bahan dari
# "isi dalam" jurnal untuk dikutip (masukan UAT: sumber harus berisi jurnal,
# bukan sekadar abstrak).
_FULLTEXT_MIN_CHARS = 1800
_ABSTRACT_MAX_CHARS = 600


def content_status(kind: str, text: str) -> str:
    """Klasifikasi cakupan isi sumber: fulltext | partial | abstract | metadata_only."""
    n = len((text or "").strip())
    if kind == "doi" and n < 250:
        # DOI tanpa abstrak CrossRef: hanya kalimat judul, tidak ada isi kutipan.
        return "metadata_only"
    if n >= _FULLTEXT_MIN_CHARS:
        return "fulltext"
    if n > _ABSTRACT_MAX_CHARS:
        return "partial"
    return "abstract"


def normalize_metadata(doc: dict[str, str]) -> dict[str, str]:
    """Samakan kunci metadata dokumen dengan yang dibaca `merge_metadata`.

    Pembaca PDF dan web memancarkan `date` (sering berupa tanggal lengkap atau
    format internal PDF seperti D:20231019120000), sedangkan penggabungan
    mengharapkan `year`; ambil 4 digit yang masuk akal sebagai tahun bila ada,
    tanpa menghapus nilai asli.
    """
    result = dict(doc or {})
    date = result.get("date")
    if date and not result.get("year"):
        kandidat = re.findall(r"\d{4}", str(date))
        pilihan = next(
            (k for k in kandidat if 1900 <= int(k) <= 2100),
            kandidat[0] if kandidat else None,
        )
        result["year"] = pilihan if pilihan else str(date)
    return result


def source_to_record(source: Source, text: str, kind: str) -> dict:
    """Ubah hasil AI menjadi dict draf; penulis disalin apa adanya sebagai usulan."""
    return {
        "kind": kind,
        "content_status": content_status(kind, text),
        "title": source.title,
        "year": source.year,
        "container": source.container,
        "doi": source.doi,
        "url": source.url,
        # Data bibliografis CrossRef (APA 7); kosong pada sumber lama.
        "volume": getattr(source, "volume", "") or "",
        "issue": getattr(source, "issue", "") or "",
        "pages": getattr(source, "pages", "") or "",
        "authors": [
            {
                "family": author.family,
                "given": author.given,
                "is_org": bool(author.is_org),
                "abbrev": author.abbrev,
            }
            for author in source.authors
        ],
        "text": text,
    }


def record_to_source(record: dict) -> Source:
    """Bangun ulang `Source` dari dict draf untuk pemakaian modul AI."""
    return Source(
        authors=[
            Author(
                author.get("family", ""),
                author.get("given", ""),
                bool(author.get("is_org", False)),
                author.get("abbrev", ""),
            )
            for author in record.get("authors", [])
        ],
        year=record.get("year", ""),
        title=record.get("title", ""),
        container=record.get("container", ""),
        doi=record.get("doi", ""),
        url=record.get("url", ""),
        volume=str(record.get("volume", "") or ""),
        issue=str(record.get("issue", "") or ""),
        pages=str(record.get("pages", "") or ""),
    )
