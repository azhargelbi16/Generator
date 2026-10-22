"""Verifikasi deterministik cuplikan per kalimat (11.2, 11.3, 19).

Status hanya menandai bahwa cuplikan benar-benar ada di sumber yang dirujuk,
bukan bahwa klaimnya benar. Gerbang ekspor ada di Task 17c.

Ambang pencocokan: **kecocokan = substring eksak setelah normalisasi** — tidak
ada fuzzy matching. Normalisasi menyamakan huruf besar/kecil, merapikan spasi,
menyambung kata yang terpotong tanda hubung di akhir baris, menyeragamkan
dash/kutip tipografis, dan membuang soft hyphen.
Toleransi teks (T1.2): membandingkan juga setelah membuang karakter non-alfanumerik
agar typo tanda baca dan pemisah ribuan tidak menggagalkan verifikasi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ai.content import Section, Sentence

STATUS_VERIFIED = "terverifikasi"
STATUS_NEEDS_REVIEW = "perlu_ditinjau"
STATUS_UNVERIFIED = "tidak_terverifikasi"
STATUS_NON_FACTUAL = "bukan_klaim_faktual"
MIN_WORDS = 5

REASON_NEEDS_REVIEW = "Kutipan ada, kalimatnya tidak sepenuhnya didukung sumber."

STOPWORDS_ID = frozenset({
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "ini", "itu", "tidak"
})

_TYPOGRAPHY = str.maketrans(
    {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00ad": "",  # soft hyphen
    }
)


def normalize(text: str) -> str:
    """Normalisasi sebelum pencocokan substring eksak (11.2)."""
    text = text.replace("-\r\n", "").replace("-\n", "")
    text = text.translate(_TYPOGRAPHY)
    return " ".join(text.lower().split())


def compute_claim_support_score(sentence_text: str, window_text: str) -> float:
    """Hitung rasio kata kalimat (tanpa kata fungsi Indonesia) yang muncul di jendela teks sumber."""
    norm_sent = normalize(sentence_text)
    words = [w for w in re.findall(r"\w+", norm_sent) if w not in STOPWORDS_ID]
    if not words:
        words = re.findall(r"\w+", norm_sent)
    if not words:
        return 0.0

    window_words = set(re.findall(r"\w+", window_text))
    matched = sum(1 for w in words if w in window_words)
    return matched / len(words)


@dataclass
class SentenceStatus:
    index: int
    sentence: Sentence
    status: str
    reason: str = ""


def _get_source_text(source_texts: dict[int, str] | list[str], source_id: int) -> str:
    if isinstance(source_texts, dict):
        return source_texts.get(source_id, "")
    if isinstance(source_texts, (list, tuple)) and 0 <= source_id < len(source_texts):
        return source_texts[source_id] or ""
    return ""


def normalize_sources(source_texts: dict[int, str] | list[str]) -> dict[int, str]:
    """Pra-normalisasi seluruh teks sumber ke dictionary agar pencocokan kutipan efisien."""
    if isinstance(source_texts, dict):
        return {k: normalize(v) for k, v in source_texts.items()}
    if isinstance(source_texts, (list, tuple)):
        return {i: normalize(t) for i, t in enumerate(source_texts)}
    return {}


def verify_sentence(
    sentence: Sentence,
    source_texts: dict[int, str] | list[str],
    min_words: int = MIN_WORDS,
    normalized_sources: dict[int, str] | None = None,
) -> str:
    """Cek cuplikan kalimat terhadap teks sumber yang dirujuknya, tanpa AI."""
    if not sentence.is_factual:
        return STATUS_NON_FACTUAL
    if sentence.origin != "ai":
        return STATUS_UNVERIFIED
    quote = normalize(sentence.quote)
    if not quote or len(quote.split()) < min_words or not sentence.source_ids:
        return STATUS_UNVERIFIED

    quote_alnum = "".join(c for c in quote if c.isalnum())
    found_windows: list[str] = []

    for source_id in sentence.source_ids:
        if normalized_sources is not None and source_id in normalized_sources:
            src_norm = normalized_sources[source_id]
        else:
            src_norm = normalize(_get_source_text(source_texts, source_id))

        # 1. Pencocokan substring eksak
        start = 0
        exact_found = False
        while True:
            pos = src_norm.find(quote, start)
            if pos == -1:
                break
            exact_found = True
            w_start = max(0, pos - 400)
            w_end = min(len(src_norm), pos + len(quote) + 400)
            found_windows.append(src_norm[w_start:w_end])
            start = pos + 1

        # 2. Toleransi teks: pencocokan alfanumerik bila eksak tidak ditemukan (T1.2)
        if not exact_found and quote_alnum:
            alnum_chars: list[str] = []
            alnum_indices: list[int] = []
            for idx, char in enumerate(src_norm):
                if char.isalnum():
                    alnum_chars.append(char)
                    alnum_indices.append(idx)
            src_alnum = "".join(alnum_chars)

            start_alnum = 0
            while True:
                pos_alnum = src_alnum.find(quote_alnum, start_alnum)
                if pos_alnum == -1:
                    break
                norm_start = alnum_indices[pos_alnum]
                norm_end = alnum_indices[pos_alnum + len(quote_alnum) - 1] + 1
                w_start = max(0, norm_start - 400)
                w_end = min(len(src_norm), norm_end + 400)
                found_windows.append(src_norm[w_start:w_end])
                start_alnum = pos_alnum + 1

    if not found_windows:
        return STATUS_UNVERIFIED

    best_score = max(compute_claim_support_score(sentence.text, w) for w in found_windows)
    if best_score >= 0.6:
        return STATUS_VERIFIED
    return STATUS_NEEDS_REVIEW


def verify_sections(sections: list[Section], source_texts: dict[int, str] | list[str]) -> list[SentenceStatus]:
    """Status untuk setiap kalimat, daftar datar dengan `index` global berurutan."""
    cached = normalize_sources(source_texts)
    statuses: list[SentenceStatus] = []
    for section in sections:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                st = verify_sentence(sentence, source_texts, normalized_sources=cached)
                reason = REASON_NEEDS_REVIEW if st == STATUS_NEEDS_REVIEW else ""
                statuses.append(
                    SentenceStatus(
                        index=len(statuses),
                        sentence=sentence,
                        status=st,
                        reason=reason,
                    )
                )
    return statuses
