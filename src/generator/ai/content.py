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
from .client import StreamError, AIError

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


def repair_truncated_json(raw: str) -> dict | None:
    """Pulihkan JSON yang terpotong di tengah jalan (misal karena batas token / finish_reason=length)."""
    if not isinstance(raw, str):
        return None
    start = raw.find("{")
    if start == -1:
        return None
    raw_sub = raw[start:]

    max_search = min(len(raw_sub), 4000)
    best_candidate: dict | None = None
    best_sentences = -1

    for i in range(len(raw_sub), max(0, len(raw_sub) - max_search), -1):
        candidate = raw_sub[:i]
        open_curly = candidate.count("{") - candidate.count("}")
        open_square = candidate.count("[") - candidate.count("]")
        if open_curly < 0 or open_square < 0:
            continue
        test_str = candidate
        if test_str.count('"') % 2 != 0:
            test_str += '"'
        test_str += "]" * open_square + "}" * open_curly
        try:
            d = json.loads(test_str, object_pairs_hook=_pairs_combine_duplicates)
            if isinstance(d, dict):
                s_count = 0
                for sec in d.get("sections", []):
                    if isinstance(sec, dict):
                        for p in sec.get("paragraphs", []):
                            if isinstance(p, dict):
                                s_count += len(p.get("sentences", []))
                if s_count > best_sentences:
                    best_sentences = s_count
                    best_candidate = d
                    if s_count > 0:
                        return best_candidate
                elif best_candidate is None and ("sections" in d or "paragraphs" in d or "sentences" in d):
                    best_candidate = d
        except Exception:
            continue
    return best_candidate


def _first_json_object(reply) -> dict | None:
    if not isinstance(reply, str):
        return None
    start = reply.find("{")
    end = reply.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(reply[start : end + 1], object_pairs_hook=_pairs_combine_duplicates)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    return repair_truncated_json(reply)


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


def _token_similarity(text_a: str, text_b: str) -> float:
    """Hitung kemiripan token antara dua teks."""
    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union)
    dice = (2.0 * len(intersection)) / (len(tokens_a) + len(tokens_b))
    return max(jaccard, dice)


def _merge_sections(existing: list[Section], incoming: list[Section]) -> None:
    """Gabung bab per judul dan buang kalimat duplikat/parafrase (kemiripan token >= 0.85).

    Jangan buang kalimat bila sitasinya berbeda. Deduplikasi hanya di dalam bab
    yang sama: fakta sumber yang sama memang ditulis ulang antarbab (latar
    belakang vs hasil), dan membuangnya melingkar mengosongkan bab.
    """
    by_title = {_normalize(section.title): section for section in existing}

    def _section_sentences(section: Section) -> list[Sentence]:
        return [sentence for paragraph in section.paragraphs for sentence in paragraph.sentences]

    for section in incoming:
        key = _normalize(section.title)
        target = by_title.get(key)
        if target is None:
            target = Section(section.level, section.title, [])
            existing.append(target)
            by_title[key] = target
        section_sentences = _section_sentences(target)
        for paragraph in section.paragraphs:
            fresh = []
            for sentence in paragraph.sentences:
                is_duplicate = False
                for ex in section_sentences:
                    sim = _token_similarity(sentence.text, ex.text)
                    if sim >= 0.85:
                        if set(sentence.source_ids) == set(ex.source_ids):
                            is_duplicate = True
                            break
                if is_duplicate:
                    continue
                section_sentences.append(sentence)
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
        stream_kwargs = {"json_mode": True, "cancel": cancel}
        try:
            import inspect
            sig = inspect.signature(client.chat_stream)
            if "max_tokens" in sig.parameters:
                stream_kwargs["max_tokens"] = 8192
            if "stream_read_timeout" in sig.parameters:
                stream_kwargs["stream_read_timeout"] = 45.0
        except Exception:
            pass
        for chunk in client.chat_stream(messages, **stream_kwargs):
            if cancel is not None and cancel.is_set():
                break
            if not chunk:
                continue
            buffer += chunk
            for raw in _iter_complete_objects(buffer):
                if cancel is not None and cancel.is_set():
                    break
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
        pass
    data = _first_json_object(buffer) or repair_truncated_json(buffer)
    return data, collected


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


_STOPWORDS_ID = frozenset({
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "ini", "itu", "tidak"
})

_BIBLIO_RE = re.compile(
    r"(?:\n\s*(?:daftar\s+pustaka|referensi|references|bibliography|works\s+cited)\s*\n).*",
    re.IGNORECASE | re.DOTALL,
)


def prune_noise_from_source_text(text: str) -> str:
    """Buang bagian daftar pustaka/referensi di ujung dokumen akademik agar tidak membebani prompt LLM."""
    if not text or len(text) < 1000:
        return text
    match = _BIBLIO_RE.search(text)
    if match and match.start() > 1000:
        cleaned = text[: match.start()].strip()
        if len(cleaned) >= 800:
            return cleaned
    return text


_SECTION_SYNONYMS: dict[str, set[str]] = {
    "pendahuluan": {
        "pendahuluan", "latar", "belakang", "rumusan", "tujuan", "manfaat", "pengantar",
        "introduction", "background", "objective", "purpose", "overview"
    },
    "tinjauan": {
        "tinjauan", "pustaka", "landasan", "teori", "studi", "literatur", "kajian", "terdahulu",
        "literature", "review", "related", "work", "theoretical", "framework"
    },
    "metode": {
        "metode", "metodologi", "prosedur", "tahapan", "pelaksanaan", "alat", "bahan", "desain", "instrumen",
        "method", "methodology", "procedure", "experimental", "materials", "algorithm", "dataset"
    },
    "hasil": {
        "hasil", "pembahasan", "temuan", "diskusi", "analisis", "pengujian", "evaluasi", "komparasi",
        "result", "results", "discussion", "findings", "analysis", "evaluation", "performance"
    },
    "kesimpulan": {
        "kesimpulan", "penutup", "simpulan", "saran", "rekomendasi", "implikasi",
        "conclusion", "conclusions", "summary", "future", "recommendation"
    },
}


def select_relevant_outline(outline: list[str], batch: list[tuple[int, str]]) -> list[str]:
    """Petakan chunk ke 1 sampai 3 bab target berdasarkan kecocokan kata kunci (T2.2)."""
    if not outline or len(outline) <= 1:
        return list(outline)

    batch_text = " ".join(text for _, text in batch).lower()
    batch_words = set(re.findall(r"\w+", batch_text))

    scores: dict[str, int] = {}
    for title in outline:
        norm_t = title.lower()
        title_words = set(re.findall(r"\w+", norm_t)) - _STOPWORDS_ID
        kw = set(title_words)
        for key, syns in _SECTION_SYNONYMS.items():
            if key in norm_t:
                kw.update(syns)

        score = sum(1 for k in kw if k in batch_words)
        if norm_t in batch_text:
            score += 3
        scores[title] = score

    positive_scores = {t: s for t, s in scores.items() if s > 0}
    if not positive_scores or len(set(scores.values())) == 1:
        return list(outline)

    sorted_by_score = sorted(positive_scores.items(), key=lambda item: item[1], reverse=True)
    max_score = sorted_by_score[0][1]

    chosen = [t for t, s in sorted_by_score if s >= max(1, max_score * 0.5)][:3]
    if not chosen:
        return list(outline)

    target_set = set(chosen)
    return [t for t in outline if t in target_set]


@dataclass
class _StepOutcome:
    """Hasil satu langkah generasi (bab varian atau batch biasa)."""

    cancelled: bool = False
    merged: bool = False


def _run_generation_step(
    sections: list[Section],
    *,
    label: str,
    messages: list[dict],
    client,
    progress: "GenerationProgress | None",
    cancel,
    emitted: set[str],
    source_texts_by_id: dict[int, str],
    max_tokens: int,
    chat_timeout: float | None = None,
    repair_truncated: bool = False,
) -> _StepOutcome:
    """Satu langkah generasi: streaming → fallback chat → perbaikan JSON →
    pemulihan parsial → penggabungan.

    Kebijakan ini dulunya diduplikasi di jalur varian (per bab) dan jalur
    batch biasa dengan beda kecil (batas token, timeout, perbaikan JSON
    terpotong, label log); keduanya kini memanggil sini agar kebijakan tidak
    bisa saling meleset. Mengembalikan apakah langkah dibatalkan dan apakah
    ada konten yang berhasil digabung.
    """
    import inspect

    data = None
    collected: list[tuple[str, Sentence]] = []
    use_stream = progress is not None and hasattr(client, "chat_stream")
    if use_stream:
        data, collected = _stream_batch(
            client, messages, progress, source_texts_by_id, cancel, emitted
        )
    if cancel is not None and cancel.is_set():
        if collected:
            _merge_sections(sections, _partial_sections(collected))
        return _StepOutcome(cancelled=True, merged=bool(collected))

    if not use_stream or data is None:
        try:
            chat_kwargs = {"json_mode": True}
            try:
                sig = inspect.signature(client.chat)
                if "max_tokens" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    chat_kwargs["max_tokens"] = max_tokens
                if chat_timeout is not None and "timeout" in sig.parameters:
                    chat_kwargs["timeout"] = chat_timeout
            except Exception:
                pass
            reply = client.chat(messages, **chat_kwargs)
            data = _first_json_object(reply)
            if data is None and repair_truncated:
                data = repair_truncated_json(reply)
            if data is not None and progress is not None:
                _reveal_sentences(data, progress, source_texts_by_id, emitted)
        except AIError as exc:
            _logger.warning("%s gagal diproses AI: %s", label, exc)
            partial = getattr(exc, "partial_content", None)
            if partial:
                data = _first_json_object(partial)
                if data is None and repair_truncated:
                    data = repair_truncated_json(partial)
                if data is not None and progress is not None:
                    _reveal_sentences(data, progress, source_texts_by_id, emitted)
            else:
                data = None

    if data is not None:
        _merge_sections(sections, _sections_from_dict(data))
        return _StepOutcome(merged=True)
    if collected:
        _logger.info(
            "%s: Menggunakan %d kalimat yang dialirkan sebelum batas respon.",
            label, len(collected),
        )
        _merge_sections(sections, _partial_sections(collected))
        return _StepOutcome(merged=True)
    return _StepOutcome(merged=False)


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

    num_sources = len(source_texts)
    # Alokasi budget karakter adaptif per sumber agar jumlah total batch selalu efisien (1 s/d 3 batch)
    if num_sources > 2:
        budget_per_source = max(2000, min(8000, 24000 // num_sources))
    else:
        budget_per_source = max_prompt_chars

    chunk_refs: list[tuple[int, str]] = []
    for source_id, raw_text in enumerate(source_texts):
        text = prune_noise_from_source_text(raw_text)
        if num_sources > 2 and len(text) > budget_per_source:
            head_len = int(budget_per_source * 0.65)
            tail_len = budget_per_source - head_len
            distilled = text[:head_len] + "\n\n[...]\n\n" + text[-tail_len:]
            chunk_refs.append((source_id, distilled))
        else:
            for chunk in chunk_text(text, max_chars=max_prompt_chars):
                chunk_refs.append((source_id, chunk.text))

    batches = list(_batches(chunk_refs, max_prompt_chars))
    total_b = len(batches)
    source_texts_by_id = {index: text for index, text in enumerate(source_texts)}
    emitted: set[str] = set()
    sections: list[Section] = []
    total = 0
    gagal = 0
    cancelled = False
    # Arsitektur Pipeline Cerdas SaaS $1B:
    # Bila memakai varian format resmi (A/B/C),
    # jalankan per bab lengkap dengan subbabnya agar setiap bagian terisi mendalam,
    # tidak ada subbab kosong, dan seluruh sumber (2022-2026) dapat disintesis secara komparatif.
    if variant_spec is not None and hasattr(format_spec, "chapter_sub_outlines") and len(outline) > 1:
        chapter_plans = format_spec.chapter_sub_outlines(variant_spec)
        total_steps = len(chapter_plans)
        ref_chunks = chunk_refs if len(chunk_refs) <= 30 else batches[0]
        for number, (chap_title, sub_outlines) in enumerate(chapter_plans, start=1):
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            total += 1
            if progress is not None:
                progress.batch_started(number, total_steps)
            messages = prompts.content_prompt(
                topic, sub_outlines, sources, ref_chunks,
                variant=variant_spec.code if variant_spec is not None else None,
            )
            outcome = _run_generation_step(
                sections,
                label=f"Bab {number} ({chap_title})",
                messages=messages,
                client=client,
                progress=progress,
                cancel=cancel,
                emitted=emitted,
                source_texts_by_id=source_texts_by_id,
                max_tokens=8192,
                chat_timeout=240.0,
                repair_truncated=True,
            )
            if outcome.cancelled:
                cancelled = True
                break
            if not outcome.merged:
                gagal += 1
    else:
        for number, batch in enumerate(batches, start=1):
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            total += 1
            if progress is not None:
                progress.batch_started(number, total_b)
            target_outline = select_relevant_outline(outline, batch)
            if len(target_outline) == len(outline) and len(outline) > 2 and total_b > 1:
                mid = (len(outline) + 1) // 2
                if number <= total_b // 2:
                    target_outline = outline[:mid]
                else:
                    target_outline = outline[mid - 1 :]
            messages = prompts.content_prompt(
                topic, target_outline, sources, batch,
                variant=variant_spec.code if variant_spec is not None else None,
            )
            outcome = _run_generation_step(
                sections,
                label=f"Batch {number}",
                messages=messages,
                client=client,
                progress=progress,
                cancel=cancel,
                emitted=emitted,
                source_texts_by_id=source_texts_by_id,
                max_tokens=16384,
            )
            if outcome.cancelled:
                cancelled = True
                break
            if not outcome.merged:
                gagal += 1
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
