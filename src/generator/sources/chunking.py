"""Pemotongan teks panjang menjadi chunk sadar kalimat dengan overlap (T2.1, 12.3).

Aturan:
- Potong di batas kalimat sedekat mungkin dengan max_chars.
- Jatuh ke batas kata bila tidak ada batas kalimat yang memadai.
- Overlap 200 karakter antar chunk tanpa memotong di tengah kata.
- Teks pendek (<= max_chars) tetap menjadi satu chunk.
- Chunk.id tetap berurutan mulai dari 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_MAX_CHARS = 3000
DEFAULT_OVERLAP = 200

_SENTENCE_END_RE = re.compile(r'([.!?]["\')\]]?)(?:\s+|\n|$)')


@dataclass
class Chunk:
    id: int
    text: str


def _adjust_to_word_boundary(text: str, pos: int, start: int, end: int) -> int:
    """Sesuaikan posisi agar berada di batas kata (tidak memotong di tengah kata)."""
    if pos <= start:
        return start
    if pos >= end:
        return end

    # Jika tepat setelah spasi (awal kata baru)
    if text[pos - 1].isspace() and not text[pos].isspace():
        return pos

    # Jika pada karakter spasi, maju ke awal kata berikutnya
    if text[pos].isspace():
        while pos < end and text[pos].isspace():
            pos += 1
        return pos

    # Jika di tengah kata, mundur ke awal kata tersebut
    back = pos
    while back > start and not text[back - 1].isspace():
        back -= 1
    if back > start:
        return back

    # Jika mundur mencapai start, maju ke akhir kata tersebut
    fwd = pos
    while fwd < end and not text[fwd].isspace():
        fwd += 1
    while fwd < end and text[fwd].isspace():
        fwd += 1
    if fwd < end:
        return fwd

    return pos


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    """Bagi teks panjang menjadi chunk dengan memperhatikan batas kalimat dan overlap."""
    text_stripped = text.strip()
    if not text_stripped or len(text_stripped) <= max_chars:
        return [Chunk(0, text_stripped if text_stripped else text)]

    chunks: list[Chunk] = []
    start = 0
    length = len(text)

    while start < length:
        limit = min(start + max_chars, length)

        if limit >= length:
            end = length
        else:
            # 1. Cari batas kalimat sedekat mungkin dengan max_chars
            best_sentence_end = -1
            min_progress = start + min(overlap, max_chars // 2)
            for m in _SENTENCE_END_RE.finditer(text[start:limit]):
                cand = start + m.end()
                if cand >= min_progress:
                    best_sentence_end = cand

            if best_sentence_end != -1:
                end = best_sentence_end
            else:
                # 2. Jatuh ke batas kata (spasi terakhir sebelum limit)
                space = -1
                for m in re.finditer(r'\s+', text[start:limit]):
                    space = start + m.start()
                if space > start:
                    end = space
                else:
                    end = limit

        chunk_str = text[start:end].strip()
        if chunk_str:
            chunks.append(Chunk(len(chunks), chunk_str))

        if end >= length:
            break

        # 3. Hitung posisi awal chunk berikutnya dengan overlap
        target_start = max(start + 1, end - overlap)
        next_start = _adjust_to_word_boundary(text, target_start, start, end)

        # Pastikan start selalu maju untuk mencegah infinite loop
        if next_start <= start:
            next_start = end

        while next_start < length and text[next_start].isspace():
            next_start += 1

        start = next_start

    return chunks
