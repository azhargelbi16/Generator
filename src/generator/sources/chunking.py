"""Pemotongan teks panjang menjadi chunk (12.3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    text: str


def chunk_text(text: str, max_chars: int = 3000) -> list[Chunk]:
    if len(text) <= max_chars:
        return [Chunk(0, text)]
    chunks: list[Chunk] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        chunks.append(Chunk(len(chunks), text[start:end]))
        start = end
        while start < length and text[start] == " ":
            start += 1
    return chunks
