"""Verifikasi deterministik cuplikan per kalimat (11.2, 11.3, 19).

Status hanya menandai bahwa cuplikan benar-benar ada di sumber yang dirujuk,
bukan bahwa klaimnya benar. Gerbang ekspor ada di Task 17c.

Ambang pencocokan: **kecocokan = substring eksak setelah normalisasi** — tidak
ada fuzzy matching. Normalisasi menyamakan huruf besar/kecil, merapikan spasi,
menyambung kata yang terpotong tanda hubung di akhir baris, menyeragamkan
dash/kutip tipografis, dan membuang soft hyphen.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ai.content import Section, Sentence

STATUS_VERIFIED = "terverifikasi"
STATUS_UNVERIFIED = "tidak_terverifikasi"
STATUS_NON_FACTUAL = "bukan_klaim_faktual"
MIN_WORDS = 8

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


@dataclass
class SentenceStatus:
    index: int
    sentence: Sentence
    status: str


def _get_source_text(source_texts: dict[int, str] | list[str], source_id: int) -> str:
    if isinstance(source_texts, dict):
        return source_texts.get(source_id, "")
    if isinstance(source_texts, (list, tuple)) and 0 <= source_id < len(source_texts):
        return source_texts[source_id] or ""
    return ""


def verify_sentence(sentence: Sentence, source_texts: dict[int, str] | list[str], min_words: int = MIN_WORDS) -> str:
    """Cek cuplikan kalimat terhadap teks sumber yang dirujuknya, tanpa AI."""
    if not sentence.is_factual:
        return STATUS_NON_FACTUAL
    if sentence.origin != "ai":
        return STATUS_UNVERIFIED
    quote = normalize(sentence.quote)
    if not quote or len(quote.split()) < min_words or not sentence.source_ids:
        return STATUS_UNVERIFIED
    for source_id in sentence.source_ids:
        if quote in normalize(_get_source_text(source_texts, source_id)):
            return STATUS_VERIFIED
    return STATUS_UNVERIFIED


def verify_sections(sections: list[Section], source_texts: dict[int, str]) -> list[SentenceStatus]:
    """Status untuk setiap kalimat, daftar datar dengan `index` global berurutan."""
    statuses: list[SentenceStatus] = []
    for section in sections:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                statuses.append(
                    SentenceStatus(
                        index=len(statuses),
                        sentence=sentence,
                        status=verify_sentence(sentence, source_texts),
                    )
                )
    return statuses
