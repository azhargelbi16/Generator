"""Penulisan isi laporan berbasis sumber dan penempatan sitasi (11.1, 11.4, 12.3, 18.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from ..sources.chunking import chunk_text
from . import prompts


@dataclass
class Sentence:
    text: str
    quote: str = ""
    source_ids: list[int] = field(default_factory=list)
    is_factual: bool = True
    uid: str = field(default_factory=lambda: uuid4().hex)
    origin: str = "ai"
    citation: bool = True


@dataclass
class Paragraph:
    sentences: list[Sentence] = field(default_factory=list)


@dataclass
class Section:
    level: int
    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _first_json_object(reply) -> dict | None:
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


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_source_ids(raw) -> list[int]:
    """Ubah id sumber menjadi int dan buang yang gagal dikonversi.

    AI kadang mengembalikan "0" sebagai string; bool juga ditolak karena True/False
    akan diam-diam menjadi 0/1 dan memasang sumber yang salah.
    """
    ids: list[int] = []
    if not isinstance(raw, list):
        return ids
    for value in raw:
        if isinstance(value, bool):
            continue
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _sentence_from_dict(raw: dict) -> Sentence | None:
    text = str(raw.get("text", "") or "")
    if not text:
        return None
    return Sentence(
        text=text,
        quote=str(raw.get("quote", "") or ""),
        source_ids=_coerce_source_ids(raw.get("source_ids")),
        is_factual=bool(raw.get("is_factual", True)),
    )


def _sections_from_dict(data: dict) -> list[Section]:
    sections: list[Section] = []
    raw_sections = data.get("sections")
    if not isinstance(raw_sections, list):
        return sections
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        paragraphs: list[Paragraph] = []
        raw_paragraphs = raw_section.get("paragraphs")
        if isinstance(raw_paragraphs, list):
            for raw_paragraph in raw_paragraphs:
                if not isinstance(raw_paragraph, dict):
                    continue
                sentences = []
                raw_sentences = raw_paragraph.get("sentences")
                if isinstance(raw_sentences, list):
                    for raw_sentence in raw_sentences:
                        if not isinstance(raw_sentence, dict):
                            continue
                        sentence = _sentence_from_dict(raw_sentence)
                        if sentence is not None:
                            sentences.append(sentence)
                paragraphs.append(Paragraph(sentences))
        sections.append(
            Section(
                level=_to_int(raw_section.get("level"), 1),
                title=str(raw_section.get("title", "") or ""),
                paragraphs=paragraphs,
            )
        )
    return sections


def _batches(chunk_refs: list[tuple[int, str]], max_chars: int):
    """Kelompokkan chunk ke batch yang mendekati `max_chars`, minimal satu chunk per batch."""
    batch: list[tuple[int, str]] = []
    size = 0
    for reference in chunk_refs:
        text = reference[1]
        if batch and size + len(text) > max_chars:
            yield batch
            batch = []
            size = 0
        batch.append(reference)
        size += len(text)
    if batch:
        yield batch


def _merge_sections(existing: list[Section], incoming: list[Section]) -> None:
    """Gabung bab per judul dan buang kalimat duplikat (dibandingkan setelah normalisasi)."""
    by_title = {_normalize(section.title): section for section in existing}
    seen = {
        _normalize(sentence.text)
        for section in existing
        for paragraph in section.paragraphs
        for sentence in paragraph.sentences
    }
    for section in incoming:
        key = _normalize(section.title)
        target = by_title.get(key)
        if target is None:
            target = Section(section.level, section.title, [])
            existing.append(target)
            by_title[key] = target
        for paragraph in section.paragraphs:
            fresh = []
            for sentence in paragraph.sentences:
                normalized = _normalize(sentence.text)
                if normalized in seen:
                    continue
                seen.add(normalized)
                fresh.append(sentence)
            if fresh:
                target.paragraphs.append(Paragraph(fresh))


def _order_by_outline(sections: list[Section], outline: list[str]) -> list[Section]:
    order = {_normalize(title): position for position, title in enumerate(outline)}
    return sorted(sections, key=lambda section: order.get(_normalize(section.title), len(outline)))


def generate_sections(
    topic: str,
    outline: list[str],
    sources: list,
    source_texts: list[str],
    client,
    max_prompt_chars: int = 12000,
) -> list[Section]:
    """Tulis isi laporan per batch chunk; satu panggilan AI per batch (12.3)."""
    if not source_texts:
        raise ValueError("Teks sumber kosong; tidak ada dasar untuk menulis isi.")
    if len(sources) != len(source_texts):
        raise ValueError("Jumlah sumber dan teks sumber tidak cocok; indeks sumber tidak dapat dipercaya.")

    chunk_refs: list[tuple[int, str]] = []
    for source_id, text in enumerate(source_texts):
        for chunk in chunk_text(text, max_chars=max_prompt_chars):
            chunk_refs.append((source_id, chunk.text))

    sections: list[Section] = []
    for batch in _batches(chunk_refs, max_prompt_chars):
        reply = client.chat(prompts.content_prompt(topic, outline, sources, batch), json_mode=True)
        data = _first_json_object(reply)
        if data is not None:
            _merge_sections(sections, _sections_from_dict(data))
    return _order_by_outline(sections, outline)


def _insert_before_final_punctuation(text: str, citation: str) -> str:
    if not citation:
        return text
    if text and text[-1] in ".!?":
        return text[:-1] + citation + text[-1]
    return text + citation


def compose(paragraph: Paragraph, labels: dict[int, str]) -> str:
    """Rangkai paragraf; sitasi dipasang kode tepat sebelum tanda baca akhir (11.4)."""
    parts: list[str] = []
    for sentence in paragraph.sentences:
        citation = ""
        if sentence.is_factual and sentence.citation and sentence.source_ids:
            inner: list[str] = []
            for source_id in labels:
                if source_id not in sentence.source_ids:
                    continue
                label = labels[source_id].strip()
                if label.startswith("(") and label.endswith(")"):
                    label = label[1:-1]
                inner.append(label)
            if inner:
                citation = " (" + "; ".join(inner) + ")"
        parts.append(_insert_before_final_punctuation(sentence.text, citation))
    return " ".join(parts)
