"""Ekstraksi bibliografi via AI, penggabungan metadata dokumen, dan retry (12.4, 12.7)."""

from __future__ import annotations

import json
from typing import Any

from ..textutil import repair_mojibake
from . import prompts
from .citation import Author, Source

_DEFAULT_MAX_CHARS = 6000
_DEFAULT_TAIL_CHARS = 500
_METADATA_KEYS = ("year", "title", "container", "doi", "url")


class BibliographyError(Exception):
    """AI gagal mengembalikan JSON bibliografi yang bisa dipakai."""


def excerpt(text: str, max_chars: int = _DEFAULT_MAX_CHARS, tail_chars: int = _DEFAULT_TAIL_CHARS) -> str:
    """Ambil awal `max_chars` karakter plus ekor `tail_chars` karakter.

    Judul dan penulis biasanya ada di awal; tahun terbitan dan DOI kadang ada di
    akhir. Memotong di tengah menjaga prompt tetap di bawah batas konteks model.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...\n" + text[-tail_chars:]


def _first_json_object(reply: Any) -> dict | None:
    if not isinstance(reply, str):
        return None
    start = reply.find("{")
    end = reply.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(reply[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _text_field(entry: dict, key: str) -> str:
    value = entry.get(key)
    return "" if value is None else str(value)


def _source_from_dict(data: dict) -> Source:
    authors: list[Author] = []
    raw_authors = data.get("authors")
    if isinstance(raw_authors, list):
        for entry in raw_authors:
            if not isinstance(entry, dict):
                continue
            authors.append(
                Author(
                    family=repair_mojibake(_text_field(entry, "family")),
                    given=repair_mojibake(_text_field(entry, "given")),
                    is_org=bool(entry.get("is_org", False)),
                    abbrev=_text_field(entry, "abbrev"),
                )
            )
    return Source(
        authors=authors,
        year=_text_field(data, "year"),
        title=repair_mojibake(_text_field(data, "title")),
        container=repair_mojibake(_text_field(data, "container")),
        doi=_text_field(data, "doi"),
        url=_text_field(data, "url"),
    )


def extract_source(text: str, client) -> Source:
    """Minta AI mengekstrak bibliografi; coba sekali lagi bila JSON tidak valid."""
    messages = prompts.bibliography_prompt(excerpt(text))
    for _ in range(2):
        data = _first_json_object(client.chat(messages, json_mode=True))
        if data is not None:
            return _source_from_dict(data)
    raise BibliographyError("AI tidak mengembalikan JSON bibliografi yang valid setelah dua percobaan.")


def merge_metadata(ai: Source, doc: dict[str, str]) -> Source:
    """Metadata dokumen menang bila ada; penulis tetap dari AI (12.4).

    Nama penulis tidak diambil dari metadata dokumen sebagai string mentah karena
    memecahnya berarti menebak pemisahan nama; user mengoreksinya di formulir.
    """
    doc = doc or {}

    def pick(key: str, fallback: str) -> str:
        value = doc.get(key)
        if value:
            return str(value)
        return fallback

    return Source(
        authors=ai.authors,
        year=pick("year", ai.year),
        title=pick("title", ai.title),
        container=pick("container", ai.container),
        doi=pick("doi", ai.doi),
        url=pick("url", ai.url),
    )
