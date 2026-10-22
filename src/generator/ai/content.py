"""Penulisan isi laporan berbasis sumber dan penempatan sitasi (11.1, 11.4, 12.3, 18.1)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from uuid import uuid4

from ..sources.chunking import chunk_text
from ..textutil import repair_mojibake
from .. import format_spec
from . import prompts
from .client import StreamError

_logger = logging.getLogger(__name__)


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


@dataclass
class GenerationProgress:
    """Callback kemajuan Generate; UI meng-override method, engine tak peduli isinya."""

    batch_count: int = 0
    sentence_hint: int = 0

    def batch_started(self, n: int, total_batches: int) -> None:
        self.batch_count = n

    def sentence_born(self, sentence: Sentence, status: str) -> None:
        self.sentence_hint += 1

    def finished(self, cancelled: bool) -> None:
        return None


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _pairs_combine_duplicates(pairs):
    res = {}
    for k, v in pairs:
        if k in res:
            if isinstance(res[k], list) and isinstance(v, list):
                res[k].extend(v)
            else:
                res[k] = v
        else:
            res[k] = v
    return res


def _first_json_object(reply) -> dict | None:
    if not isinstance(reply, str):
        return None
    start = reply.find("{")
    end = reply.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(reply[start : end + 1], object_pairs_hook=_pairs_combine_duplicates)
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
    text = repair_mojibake(str(raw.get("text", "") or ""))
    if not text:
        return None
    return Sentence(
        text=text,
        quote=repair_mojibake(str(raw.get("quote", "") or "")),
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


_TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _iter_complete_objects(partial: str) -> list[dict]:
    """Ambil objek JSON utuh berkunci "text" dari JSON yang masih parsial.

    Kalimat terakhir yang belum tertutup diabaikan; pemanggil memanggil ulang
    saat potongan teks berikutnya datang.
    """
    objects: list[dict] = []
    stack: list[int] = []
    in_string = False
    escaped = False
    for index, char in enumerate(partial):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            stack.append(index)
        elif char == "}" and stack:
            start = stack.pop()
            fragment = partial[start : index + 1]
            if '"text"' not in fragment:
                continue
            try:
                candidate = json.loads(fragment)
            except ValueError:
                continue
            if isinstance(candidate, dict) and "text" in candidate:
                objects.append(candidate)
    return objects


def _current_title(partial: str) -> str:
    """Judul bab terakhir yang terlihat di JSON parsial (untuk pengelompokan batal)."""
    matches = _TITLE_RE.findall(partial)
    if not matches:
        return ""
    try:
        return json.loads('"' + matches[-1] + '"')
    except ValueError:
        return matches[-1]


def _status_of(sentence: Sentence, source_texts_by_id: dict[int, str]) -> str:
    from ..verification import verify_sentence

    return verify_sentence(sentence, source_texts_by_id)


def _stream_batch(client, messages, progress, source_texts_by_id, cancel, emitted):
    """Alirkan satu batch; kembalikan (data_json_utuh | None, kalimat_terkumpul)."""
    buffer = ""
    collected: list[tuple[str, Sentence]] = []
    try:
        for chunk in client.chat_stream(messages, json_mode=True, cancel=cancel):
            if cancel is not None and cancel.is_set():
                break
            if not chunk:
                continue
            buffer += chunk
            for raw in _iter_complete_objects(buffer):
                sentence = _sentence_from_dict(raw)
                if sentence is None:
                    continue
                key = _normalize(sentence.text)
                if key in emitted:
                    continue
                emitted.add(key)
                progress.sentence_born(sentence, _status_of(sentence, source_texts_by_id))
                collected.append((_current_title(buffer), sentence))
    except StreamError:
        return None, collected
    return _first_json_object(buffer), collected


def _reveal_sentences(data: dict, progress, source_texts_by_id, emitted) -> None:
    """Fallback non-streaming: lahirkan semua kalimat setelah batch selesai, urut JSON."""
    for section in _sections_from_dict(data):
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                key = _normalize(sentence.text)
                if key in emitted:
                    continue
                emitted.add(key)
                progress.sentence_born(sentence, _status_of(sentence, source_texts_by_id))


def _partial_sections(collected: list[tuple[str, Sentence]]) -> list[Section]:
    """Susun kalimat yang sudah lahir menjadi bab/paragraf saat generate dibatalkan."""
    result: list[Section] = []
    by_title: dict[str, Section] = {}
    for title, sentence in collected:
        key = _normalize(title)
        section = by_title.get(key)
        if section is None:
            section = Section(1, title, [])
            by_title[key] = section
            result.append(section)
        if not section.paragraphs:
            section.paragraphs.append(Paragraph([]))
        section.paragraphs[0].sentences.append(sentence)
    return result


def generate_sections(
    topic: str,
    outline: list[str],
    sources: list,
    source_texts: list[str],
    client,
    max_prompt_chars: int = 12000,
    progress: GenerationProgress | None = None,
    cancel=None,
    variant: str | None = None,
) -> list[Section]:
    """Tulis isi laporan per batch chunk; satu panggilan AI per batch (12.3).

    Tanpa `progress` dan `cancel`, keluarannya sama persis dengan perilaku lama.
    Dengan `progress`, kalimat dilaporkan saat lahir (streaming bila client
    mendukung `chat_stream`, selain itu per batch setelah jawaban utuh tiba).
    Bila `variant` diisi (A/B/C), judul baku varian dipakai dan keluaran
    dinormalisasi ke struktur varian.
    """
    if not source_texts:
        raise ValueError("Teks sumber kosong; tidak ada dasar untuk menulis isi.")
    if len(sources) != len(source_texts):
        raise ValueError("Jumlah sumber dan teks sumber tidak cocok; indeks sumber tidak dapat dipercaya.")

    variant_spec = format_spec.get_variant(variant)
    if variant_spec is not None:
        outline = format_spec.outline_titles(variant_spec)

    def _finish(result: list[Section]) -> list[Section]:
        if variant_spec is not None:
            return format_spec.normalize_sections(variant_spec, result)
        return _order_by_outline(result, outline)

    chunk_refs: list[tuple[int, str]] = []
    for source_id, text in enumerate(source_texts):
        for chunk in chunk_text(text, max_chars=max_prompt_chars):
            chunk_refs.append((source_id, chunk.text))

    batches = list(_batches(chunk_refs, max_prompt_chars))
    source_texts_by_id = {index: text for index, text in enumerate(source_texts)}
    emitted: set[str] = set()
    sections: list[Section] = []
    total = 0
    gagal = 0
    cancelled = False
    for number, batch in enumerate(batches, start=1):
        if cancel is not None and cancel.is_set():
            cancelled = True
            break
        total += 1
        if progress is not None:
            progress.batch_started(number, len(batches))
        messages = prompts.content_prompt(
            topic, outline, sources, batch,
            variant=variant_spec.code if variant_spec is not None else None,
        )
        data = None
        collected: list[tuple[str, Sentence]] = []
        use_stream = progress is not None and hasattr(client, "chat_stream")
        if use_stream:
            data, collected = _stream_batch(
                client, messages, progress, source_texts_by_id, cancel, emitted
            )
        if cancel is not None and cancel.is_set():
            cancelled = True
            if collected:
                _merge_sections(sections, _partial_sections(collected))
            break
        if not use_stream or data is None:
            reply = client.chat(messages, json_mode=True)
            data = _first_json_object(reply)
            if data is not None and progress is not None:
                _reveal_sentences(data, progress, source_texts_by_id, emitted)
        if data is None:
            gagal += 1
            continue
        _merge_sections(sections, _sections_from_dict(data))
    if progress is not None:
        progress.finished(cancelled)
    if cancelled:
        return _finish(sections)
    if total and gagal == total:
        raise ValueError("Respons AI tidak terbaca (JSON tidak valid) pada semua batch.")
    if gagal:
        _logger.warning(
            "Generate: %d dari %d batch AI tidak terbaca; bab bisa kurang.", gagal, total
        )
    return _finish(sections)


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


def _source_samples(source_texts: list[str], max_chars: int = 1500) -> list[tuple[int, str]]:
    """Ambil cuplikan awal tiap sumber untuk prompt usulan outline dan parafrase."""
    samples: list[tuple[int, str]] = []
    for source_id, text in enumerate(source_texts):
        chunks = chunk_text(text, max_chars=max_chars)
        if chunks:
            samples.append((source_id, chunks[0].text))
    return samples


def suggest_outline(
    topic: str,
    sources: list,
    source_texts: list[str],
    client,
    max_items: int = 12,
) -> list[str]:
    """Usulkan judul bab dari topik dan ringkasan sumber (18.2). JSON gagal berarti kosong."""
    reply = client.chat(
        prompts.outline_prompt(topic, sources, _source_samples(source_texts), max_items),
        json_mode=True,
    )
    data = _first_json_object(reply)
    if data is None:
        return []
    outline = data.get("outline")
    if not isinstance(outline, list):
        return []
    titles = [str(item).strip() for item in outline if str(item).strip()]
    return titles[:max_items]


def paraphrase(paragraph: Paragraph, sources: list, source_texts: list[str], client) -> Paragraph:
    """Parafrase satu paragraf; hasil tetap `origin="ai"` agar harus lulus verifikasi (19)."""
    reply = client.chat(
        prompts.paraphrase_prompt(paragraph, sources, _source_samples(source_texts)),
        json_mode=True,
    )
    data = _first_json_object(reply)
    if data is None:
        return paragraph
    raw_sentences = data.get("sentences")
    if not isinstance(raw_sentences, list):
        return paragraph
    sentences: list[Sentence] = []
    for raw_sentence in raw_sentences:
        if not isinstance(raw_sentence, dict):
            continue
        text = repair_mojibake(str(raw_sentence.get("text", "") or ""))
        if not text:
            continue
        sentences.append(
            Sentence(
                text=text,
                quote=repair_mojibake(str(raw_sentence.get("quote", "") or "")),
                source_ids=_coerce_source_ids(raw_sentence.get("source_ids")),
                is_factual=bool(raw_sentence.get("is_factual", True)),
            )
        )
    if not sentences:
        return paragraph
    return Paragraph(sentences)


def merge_regenerated(
    old_sections: list[Section],
    new_sections: list[Section],
    overwrite_all: bool = False,
) -> list[Section]:
    """Gabungkan hasil tulis ulang dengan catatan manual lama (19).

    Kalimat `origin="manual"` dipertahankan: bab yang judulnya sama menerima catatan
    lama di belakang hasil baru; catatan dari bab yang sudah tidak ada tetap dipakai
    di babnya sendiri di urutan belakang. `overwrite_all` memakai hasil baru saja.
    """
    if overwrite_all:
        return new_sections
    merged = list(new_sections)
    by_title = {_normalize(section.title): section for section in merged}
    orphans: dict[str, Section] = {}
    for section in old_sections:
        manual = [
            sentence
            for paragraph in section.paragraphs
            for sentence in paragraph.sentences
            if sentence.origin == "manual"
        ]
        if not manual:
            continue
        key = _normalize(section.title)
        target = by_title.get(key)
        if target is not None:
            target.paragraphs.append(Paragraph(manual))
            continue
        orphan = orphans.get(key)
        if orphan is None:
            orphan = Section(section.level, section.title, [])
            orphans[key] = orphan
            merged.append(orphan)
        orphan.paragraphs.append(Paragraph(manual))
    return merged
