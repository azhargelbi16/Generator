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

from ..sources.intake import source_from_crossref_message
from ..sources.records import source_to_record

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

    src = source_from_crossref_message(doi, msg)

    # Abstrak sebagai teks sumber awal jika ada
    abstract = str(msg.get("abstract", "") or "").strip()
    clean_abstract = re.sub(r"<[^>]+>", "", abstract).strip()
    source_text = clean_abstract or (
        f"{src.title}. Diterbitkan di {src.container} ({src.year}). DOI: {src.doi}"
    )
    return source_to_record(src, source_text, kind="doi")
