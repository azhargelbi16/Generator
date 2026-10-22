"""Penyelesai DOI (Digital Object Identifier) otomatis via CrossRef API.

Menghubungi CrossRef API secara gratis dan tanpa API key untuk mengunduh
metadata bibliografi resmi: judul, daftar penulis, tahun publikasi,
nama jurnal/container, dan DOI.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from ..ai.citation import Author, Source
from ..sources.records import source_to_record
from ..textutil import repair_mojibake

log = logging.getLogger("generator.sources.doi")

DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)
CROSSREF_API_URL = "https://api.crossref.org/works/{doi}"
TIMEOUT = 10
HEADERS = {
    "User-Agent": "GeneratorLaporan/2.0 (mailto:academic@generator-laporan.local)",
    "Accept": "application/json",
}


def extract_doi(text: str) -> str | None:
    """Ekstrak DOI murni dari teks input atau URL (mis. https://doi.org/10.1016/...)."""
    match = DOI_REGEX.search(text.strip())
    if match:
        return match.group(0).rstrip(".,;")
    return None


def fetch_doi_metadata(doi_or_url: str) -> dict[str, Any]:
    """Ambil metadata dari CrossRef API; kembalikan record sumber yang siap dipakai."""
    doi = extract_doi(doi_or_url)
    if not doi:
        raise ValueError(
            "Format DOI tidak valid. Masukkan format seperti '10.1016/...' atau tautan 'https://doi.org/10.1016/...'"
        )

    url = CROSSREF_API_URL.format(doi=doi)
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ConnectionError(f"Gagal menghubungi server CrossRef: {exc}") from exc

    if response.status_code == 404:
        raise ValueError(f"DOI '{doi}' tidak ditemukan di basis data CrossRef.")
    if response.status_code >= 400:
        raise ConnectionError(f"CrossRef merespons HTTP {response.status_code}.")

    try:
        data = response.json()
    except Exception as exc:
        raise ValueError(f"Format respons CrossRef tidak valid: {exc}") from exc

    msg = data.get("message", {})

    # 1. Judul
    titles = msg.get("title") or []
    title = repair_mojibake(titles[0] if titles else "Tanpa Judul")

    # 2. Penulis
    authors: list[Author] = []
    raw_authors = msg.get("author") or []
    for a in raw_authors:
        if not isinstance(a, dict):
            continue
        family = repair_mojibake(str(a.get("family", "")).strip())
        given = repair_mojibake(str(a.get("given", "")).strip())
        name = repair_mojibake(str(a.get("name", "")).strip())

        if family:
            authors.append(Author(family=family, given=given, is_org=False))
        elif name:
            authors.append(Author(family=name, given="", is_org=True))

    # 3. Tahun
    year = ""
    date_parts = msg.get("issued", {}).get("date-parts") or msg.get("published-print", {}).get("date-parts") or msg.get("published-online", {}).get("date-parts")
    if date_parts and isinstance(date_parts, list) and len(date_parts) > 0 and len(date_parts[0]) > 0:
        val = date_parts[0][0]
        if val is not None:
            year = str(val)

    # 4. Container / Nama Jurnal
    containers = msg.get("container-title") or []
    container = repair_mojibake(containers[0] if containers else "")

    # 5. URL
    doi_val = msg.get("DOI", doi)
    canonical_url = msg.get("URL", f"https://doi.org/{doi_val}")

    # 6. Abstrak sebagai teks sumber awal jika ada
    abstract = str(msg.get("abstract", "") or "").strip()
    # Bersihkan tag XML/HTML jika ada
    clean_abstract = re.sub(r"<[^>]+>", "", abstract).strip()
    source_text = clean_abstract or f"{title}. Diterbitkan di {container} ({year}). DOI: {doi_val}"

    src = Source(
        authors=authors,
        year=year,
        title=title,
        container=container,
        doi=doi_val,
        url=canonical_url,
    )
    return source_to_record(src, source_text, kind="doi")
