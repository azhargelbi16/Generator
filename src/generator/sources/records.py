"""Rekord sumber netral (tanpa GUI): konversi Source <-> dict draf, metadata.

Dipakai gui/tab_report.py (Tk) dan qt/report_controller.py (Qt); ditaruh di
sini supara modul Qt tidak perlu mengimpor tkinter.
"""

from __future__ import annotations

import re

from ..ai.citation import Author, Source

DRAFT_ACTIVE_ID = "aktif"


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
        "title": source.title,
        "year": source.year,
        "container": source.container,
        "doi": source.doi,
        "url": source.url,
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
    )
