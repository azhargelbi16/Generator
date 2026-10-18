"""Logika inti laporan: gerbang ekspor, kalimat tertunda, sitasi, dan referensi (11, 17a).

Keputusan putaran 6 yang dipegang modul ini:
- `pending` hanya menghitung kalimat yang belum terverifikasi dan belum ditandai
  selesai, supaya kalimat terverifikasi tidak ikut dihitung tertunda.
- `cited_ids` hanya menerima kalimat faktual dengan sitasi aktif, yaitu tepat
  kalimat yang akan diberi sitasi oleh `compose`; kalimat bukan klaim faktual
  dan kalimat dengan sitasi dimatikan user tidak memaksa sumbernya masuk
  daftar pustaka.
"""

from __future__ import annotations

from .ai.citation import Source, order_and_label
from .ai.content import Paragraph, Section, Sentence
from .verification import STATUS_NON_FACTUAL, STATUS_VERIFIED, SentenceStatus


def can_export(
    statuses: list[SentenceStatus], done: frozenset[str] = frozenset()
) -> tuple[bool, str]:
    """Ekspor dibolehkan bila semua kalimat terverifikasi atau ditandai selesai."""
    blocked = pending(statuses, done)
    if not blocked:
        return True, ""
    return False, (
        f"{len(blocked)} kalimat belum selesai (belum terverifikasi dan belum "
        "ditandai selesai). Periksa penanda di daftar kalimat."
    )


def pending(statuses: list[SentenceStatus], done: frozenset[str]) -> list[int]:
    """Index kalimat yang bukan `terverifikasi` dan uid-nya belum ada di `done`."""
    return [
        item.index
        for item in statuses
        if item.status != STATUS_VERIFIED and item.sentence.uid not in done
    ]


def non_factual_uids(statuses: list[SentenceStatus]) -> list[str]:
    """Uid semua kalimat berstatus bukan klaim faktual, untuk penandaan massal."""
    return [item.sentence.uid for item in statuses if item.status == STATUS_NON_FACTUAL]


def cited_ids(statuses: list[SentenceStatus]) -> set[int]:
    """Indeks sumber yang benar-benar dirujuk kalimat yang akan disitasi."""
    referenced: set[int] = set()
    for item in statuses:
        sentence = item.sentence
        if sentence.is_factual and sentence.citation:
            referenced.update(sentence.source_ids)
    return referenced


def labels_for(sources: list[Source], cited: set[int]) -> dict[int, str]:
    """Peta indeks sumber asli ke sitasi dalam kurung; urutan kunci ikut urutan referensi."""
    return {labeled.source_index: labeled.in_text for labeled in order_and_label(sources, cite=cited)}


def references_for(sources: list[Source], cited: set[int]) -> list[str]:
    """Entri daftar pustaka hanya untuk sumber yang dikutip."""
    return [labeled.reference for labeled in order_and_label(sources, cite=cited)]


def uncited_ids(sources: list[Source], cited: set[int]) -> list[int]:
    """Indeks sumber yang dimasukkan tapi tidak dikutip, untuk peringatan (11.4)."""
    return [index for index in range(len(sources)) if index not in cited]


# --------------------------------------------------------------- serialisasi


def sentence_to_dict(sentence: Sentence) -> dict:
    """Serialisasi kalimat lengkap dengan identitas agar draf setia pada asalnya."""
    return {
        "text": sentence.text,
        "quote": sentence.quote,
        "source_ids": list(sentence.source_ids),
        "is_factual": sentence.is_factual,
        "uid": sentence.uid,
        "origin": sentence.origin,
        "citation": sentence.citation,
    }


def sentence_from_dict(raw: dict) -> Sentence:
    return Sentence(
        text=raw.get("text", ""),
        quote=raw.get("quote", ""),
        source_ids=[int(sid) for sid in raw.get("source_ids", [])],
        is_factual=bool(raw.get("is_factual", True)),
        uid=raw.get("uid", ""),
        origin=raw.get("origin", "ai"),
        citation=bool(raw.get("citation", True)),
    )


def sections_to_dicts(sections: list[Section]) -> list[dict]:
    return [
        {
            "level": section.level,
            "title": section.title,
            "paragraphs": [
                {"sentences": [sentence_to_dict(s) for s in paragraph.sentences]}
                for paragraph in section.paragraphs
            ],
        }
        for section in sections
    ]


def sections_from_dicts(raws: list[dict]) -> list[Section]:
    sections: list[Section] = []
    for raw in raws:
        paragraphs = [
            Paragraph([sentence_from_dict(s) for s in paragraph.get("sentences", [])])
            for paragraph in raw.get("paragraphs", [])
        ]
        sections.append(
            Section(
                level=int(raw.get("level", 1)),
                title=raw.get("title", ""),
                paragraphs=paragraphs,
            )
        )
    return sections
