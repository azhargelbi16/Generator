"""Kebijakan penerimaan sumber (source intake) untuk semua jalur masuk.

PDF, web, manual, dan DOI dulunya masing-masing meniru keputusan yang sama:
konversi penulis CrossRef, metadata dokumen menang atas usulan AI, judul
fallback, keputusan perlu-tidaknya pengayaan AI, dan format identitas `ref`.
Modul ini memiliki kebijakan itu sekali — pembaca berkas/halaman tetap adapter
yang hanya mengembalikan teks dan metadata mentah, lalu memanggil sini.

Semantik yang dipertahankan:
- Metadata dokumen (PDF/page/DOI resmi) menang atas ekstraksi AI (12.4);
  penulis tidak pernah ditebak pemisahannya dari string mentah.
- ``ref`` berformat ``{kind}-{HHMMSSffffff}-{len(teks)}`` dan dipakai UI untuk
  mencocokkan event ``source_metadata_ready``.
- ``content_status`` dihitung di records.source_to_record (fulltext/partial/
  abstract/metadata_only).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..ai.bibliography import merge_metadata as _ai_merge_metadata
from ..ai.citation import Author, Source
from ..textutil import repair_mojibake
from .records import source_to_record

log = logging.getLogger("generator.sources.intake")


def source_from_doi_record(doi_record: dict[str, Any] | None) -> Source | None:
    """Ubah record hasil resolusi DOI menjadi ``Source``.

    Kembalikan ``None`` bila payload kosong atau tidak membawa judul, sehingga
    pemanggil tahu harus lanjut ke metadata dokumen / AI.
    """
    if not isinstance(doi_record, dict) or not doi_record.get("title"):
        return None
    authors = [
        Author(
            family=str(a.get("family", "")),
            given=str(a.get("given", "")),
            is_org=bool(a.get("is_org", False)),
            abbrev=str(a.get("abbrev", "") or ""),
        )
        for a in doi_record.get("authors", [])
        if isinstance(a, dict)
    ]
    return Source(
        authors=authors,
        year=str(doi_record.get("year", "") or ""),
        title=str(doi_record.get("title", "")),
        container=str(doi_record.get("container", "") or ""),
        doi=str(doi_record.get("doi", "") or ""),
        url=str(doi_record.get("url", "") or ""),
    )


def source_from_crossref_message(doi: str, msg: dict[str, Any]) -> Source:
    """Ubah pesan mentah CrossRef (``works/{doi}``) menjadi ``Source``.

    Dipakai doi_resolver (adapter jaringan) agar konversi tidak pernah
    berbeda antara jalur cepat dan jalur "Cari DOI".
    """
    titles = msg.get("title") or []
    title = repair_mojibake(titles[0] if titles else "Tanpa Judul")

    authors: list[Author] = []
    for a in msg.get("author") or []:
        if not isinstance(a, dict):
            continue
        family = repair_mojibake(str(a.get("family", "")).strip())
        given = repair_mojibake(str(a.get("given", "")).strip())
        name = repair_mojibake(str(a.get("name", "")).strip())
        if family:
            authors.append(Author(family=family, given=given, is_org=False))
        elif name:
            authors.append(Author(family=name, given="", is_org=True))

    year = ""
    date_parts = (
        msg.get("issued", {}).get("date-parts")
        or msg.get("published-print", {}).get("date-parts")
        or msg.get("published-online", {}).get("date-parts")
    )
    if date_parts and isinstance(date_parts, list) and date_parts[0]:
        val = date_parts[0][0]
        if val is not None:
            year = str(val)

    containers = msg.get("container-title") or []
    container = repair_mojibake(containers[0] if containers else "")
    doi_val = msg.get("DOI", doi)
    canonical_url = msg.get("URL", f"https://doi.org/{doi_val}")

    return Source(
        authors=authors,
        year=year,
        title=title,
        container=container,
        doi=doi_val,
        url=canonical_url,
    )


def fast_doi_source(doc_meta: dict[str, str] | None, text_head: str) -> Source | None:
    """Resolusi cepat CrossRef (~0,3 dtk) bila metadata/teks memuat DOI.

    Gagal apa pun (jaringan, tanpa judul, tanpa DOI) mengembalikan ``None``
    dan dicatat — pemanggil lanjut ke metadata dokumen atau AI tanpa error.
    """
    from . import doi_resolver  # impor lokal: hindari siklus impor modul

    doi_val = (doc_meta or {}).get("doi") or doi_resolver.extract_doi(text_head or "")
    if not doi_val:
        return None
    try:
        record = doi_resolver.fetch_doi_metadata(doi_val)
    except Exception as exc:
        log.info("Resolusi cepat DOI dilewati (%s).", exc)
        return None
    source = source_from_doi_record(record)
    if source is None:
        log.info("Resolusi cepat DOI dilewati: CrossRef tidak mengembalikan judul.")
    return source


def merge_metadata(ai_source: Source, doc_meta: dict[str, str] | None) -> Source:
    """Metadata dokumen menang atas usulan AI (12.4)."""
    return _ai_merge_metadata(ai_source, doc_meta or {})


def ensure_title(source: Source, fallback: str) -> Source:
    """Isi judul bila kosong (nama berkas / URL / label) tanpa menimpa yang ada."""
    if not source.title:
        return Source(
            source.authors,
            source.year,
            fallback,
            source.container,
            source.doi,
            source.url,
        )
    return source


def needs_enrichment(source: Source) -> bool:
    """Pengayaan AI perlu dijalankan bila tidak ada penulis sama sekali."""
    return not source.authors


def make_record(source: Source, text: str, kind: str) -> dict[str, Any]:
    """SourceRecord lengkap: cakupan isi + ``ref`` ephemeral untuk event."""
    record = source_to_record(source, text, kind)
    record["ref"] = f"{kind}-{datetime.now().strftime('%H%M%S%f')}-{len(text)}"
    return record
