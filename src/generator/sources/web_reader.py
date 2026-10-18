"""Pembaca konten web (12.2)."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from .errors import SourceReadError

__all__ = ["SourceReadError", "fetch_text", "fetch_metadata"]

TIMEOUT = 30


def _content_type(response) -> str:
    for key, value in getattr(response, "headers", {}).items():
        if key.lower() == "content-type":
            return str(value).lower()
    return ""


def _parser(_content_type_value: str) -> str:
    return "html.parser"


def _soup(url: str) -> BeautifulSoup:
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SourceReadError(
            f"Situs tidak bisa diakses (diblokir atau butuh JavaScript): {url}"
        ) from exc
    return BeautifulSoup(response.text, _parser(_content_type(response)))


def fetch_text(url: str) -> str:
    soup = _soup(url)
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def fetch_metadata(url: str) -> dict[str, str]:
    soup = _soup(url)
    result: dict[str, str] = {}
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()
    meta_map = {
        "citation_author": "author",
        "citation_title": "title",
        "citation_publication_date": "date",
        "citation_journal_title": "container",
        "citation_doi": "doi",
    }
    for name, field in meta_map.items():
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            result[field] = tag["content"].strip()
    return result
