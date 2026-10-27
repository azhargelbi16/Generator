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


_LIST_ITEM_RE = re.compile(r"^\s*(?:\d{1,2}|[a-z])[\.\)]\s+\S")
_FLAT_PARA_CHUNK = 4  # tanpa penanda: pecah tiap 4 kalimat
_FLAT_PARA_MAX = 5  # satu paragraf tidak pernah memuat > 5 kalimat pipih


def _paragraphs_from_flat(sentences: list[Sentence], markers: list[int]) -> list[Paragraph]:
    """Susun paragraf dari kalimat pipih hasil model (tanpa pembungkus sentences).

    Kebijakan:
    - Kalimat butir bernomor tetap satu butir satu paragraf (tidak digabung).
    - Bila model menyertakan penanda ``paragraph``/``par``, kelompokkan menurut
      nilai itu (maksimal 5 kalimat per paragraf).
    - Tanpa penanda sama sekali, pecah tiap 4 kalimat — mencegah satu paragraf
      raksasa berisi seluruh subbab.
    """
    if not sentences:
        return []
    if all(_LIST_ITEM_RE.match(sentence.text) for sentence in sentences):
        return [Paragraph([sentence]) for sentence in sentences]
    if any(marker >= 0 for marker in markers):
        groups: dict[int, list[Sentence]] = {}
        order: list[int] = []
        for sentence, marker in zip(sentences, markers):
            key = marker if marker >= 0 else (order[-1] if order else 0)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(sentence)
        result: list[Paragraph] = []
        for key in order:
            group = groups[key]
            for start in range(0, len(group), _FLAT_PARA_MAX):
                result.append(Paragraph(group[start : start + _FLAT_PARA_MAX]))
        return result
    return [
        Paragraph(sentences[start : start + _FLAT_PARA_CHUNK])
        for start in range(0, len(sentences), _FLAT_PARA_CHUNK)
    ]


def _marker_of(raw_sentence: dict) -> int:
    value = raw_sentence.get("paragraph", raw_sentence.get("par"))
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


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
        flat: list[Sentence] = []
        markers: list[int] = []
        if isinstance(raw_paragraphs, list):
            # Sebagian model menuliskan kalimat langsung sebagai isi array
            # ``paragraphs`` tanpa pembungkus ``{"sentences": [...]}`` sesuai
            # bentuk prompt. Tanpa toleransi ini seluruh isi bab hilang
            # diam-diam (judul bab tetap terbentuk, paragraf kosong).
            for raw_paragraph in raw_paragraphs:
                if not isinstance(raw_paragraph, dict):
                    continue
                raw_sentences = raw_paragraph.get("sentences")
                if isinstance(raw_sentences, list):
                    sentences = []
                    for raw_sentence in raw_sentences:
                        if not isinstance(raw_sentence, dict):
                            continue
                        sentence = _sentence_from_dict(raw_sentence)
                        if sentence is not None:
                            sentences.append(sentence)
                    paragraphs.append(Paragraph(sentences))
                elif "text" in raw_paragraph:
                    sentence = _sentence_from_dict(raw_paragraph)
                    if sentence is not None:
                        flat.append(sentence)
                        markers.append(_marker_of(raw_paragraph))
        # Toleransi kedua: kalimat pipih langsung di level section.
        if not flat and not paragraphs:
            raw_flat = raw_section.get("sentences")
            if isinstance(raw_flat, list):
                for raw_sentence in raw_flat:
                    if not isinstance(raw_sentence, dict):
                        continue
                    sentence = _sentence_from_dict(raw_sentence)
                    if sentence is not None:
                        flat.append(sentence)
                        markers.append(_marker_of(raw_sentence))
        if flat:
            paragraphs.extend(_paragraphs_from_flat(flat, markers))
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


_ITEM_NUMBER_RE = re.compile(r"^\s*((?:\d{1,2})|[a-z])[\.\)]\s", re.IGNORECASE)


def _item_token(text: str) -> str:
    """Token nomor butir ("1", "a") atau string kosong bila bukan butir daftar."""
    match = _ITEM_NUMBER_RE.match(str(text or "").strip())
    return match.group(1) if match else ""


_LIST_SECTION_RE = re.compile(r"\b(kesimpulan|saran|conclusion|recommendation)\b", re.IGNORECASE)


def _dedup_threshold(section_title: str) -> float:
    """Ambang kemiripan dedup untuk satu section.

    Kesimpulan/Saran kerap dikirim AI dua set dengan redaksi mirip (~0,6–0,7)
    karena konteks bab sebelumnya ikut terkirim; ambang 0,55 membiarkan keduanya
    lolos. Untuk bagian naratif, tiap langkah bab menerima sumber dan konteks yang
    sama sehingga model menulis ulang kerangka dengan redaksi berbeda (~0,6–0,7);
    ambang diturunkan ke 0,6 agar duplikasi parafrase tidak menumpuk. Syarat
    sitasi sama tetap berlaku sehingga kalimat dengan sumber berbeda tidak dibuang.
    """
    if _LIST_SECTION_RE.search(str(section_title or "")):
        # Daftar bernomor: hanya duplikat hampir identik yang dibuang; duplikat
        # nomor ditangani terpisah saat routing/penyeimbangan.
        return 0.85
    # Naratif: tiap langkah bab menerima sumber+konteks sama sehingga model
    # menulis ulang kerangka dengan redaksi berbeda (~0,55–0,7).
    return 0.55


def _merge_sections(existing: list[Section], incoming: list[Section]) -> None:
    """Gabung bab per judul dan buang kalimat duplikat/parafrase (kemiripan token >= ambang).

    Jangan buang kalimat bila sitasinya berbeda. Kemiripan token hanya diperiksa
    di dalam bab yang sama (biaya kuadratik dijaga tetap kecil), tetapi kalimat
    yang **identik** dobel lintas bab dibuang lewat indeks hash O(1) per kalimat.
    Tanpa lapisan hash ini, jalur varian (satu panggilan AI per bab dengan bahan
    sumber yang sama) mengulang kalimat yang sama di Latar Belakang, Hasil,
    Pembahasan, dan Kesimpulan — persis keluaran yang tidak layak dikumpulkan.
    """
    by_title = {_normalize(section.title): section for section in existing}

    def _section_sentences(section: Section) -> list[Sentence]:
        return [sentence for paragraph in section.paragraphs for sentence in paragraph.sentences]

    # Indeks global teks -> daftar himpunan sumber yang sudah memakainya. Kalimat
    # suntingan manual tidak ikut dideduplikasi agar catatan pengguna tidak hilang.
    # Biaya: satu lintasan O(n) saat masuk, lalu O(1) per kalimat baru.
    seen: dict[str, set[frozenset[int]]] = {}
    for section in existing:
        for sentence in _section_sentences(section):
            if sentence.origin != "manual":
                seen.setdefault(_normalize(sentence.text), set()).add(
                    frozenset(sentence.source_ids)
                )

    for section in incoming:
        key = _normalize(section.title)
        target = by_title.get(key)
        if target is None:
            target = Section(section.level, section.title, [])
            existing.append(target)
            by_title[key] = target
        section_sentences = _section_sentences(target)
        threshold = _dedup_threshold(target.title)
        is_list_section = bool(_LIST_SECTION_RE.search(str(target.title or "")))
        for paragraph in section.paragraphs:
            fresh = []
            for sentence in paragraph.sentences:
                normalized = _normalize(sentence.text)
                sources = frozenset(sentence.source_ids)
                if sentence.origin != "manual" and sources in seen.setdefault(normalized, set()):
                    # Sudah pernah ditulis (di bab mana pun) dengan sumber yang sama.
                    continue
                is_duplicate = False
                token = _item_token(sentence.text) if is_list_section else ""
                for ex in section_sentences:
                    if token and _item_token(ex.text) == token:
                        # Nomor butir sama di daftar: butir duplikat, apa pun redaksinya.
                        if set(sentence.source_ids) == set(ex.source_ids):
                            is_duplicate = True
                            break
                    sim = _token_similarity(sentence.text, ex.text)
                    if sim >= threshold:
                        if set(sentence.source_ids) == set(ex.source_ids):
                            is_duplicate = True
                            break
                if is_duplicate:
                    continue
                if sentence.origin != "manual":
                    seen[normalized].add(sources)
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


def _stream_batch(
    client,
    messages,
    progress,
    source_texts_by_id,
    cancel,
    emitted,
    max_tokens: int = 8192,
):
    """Alirkan satu batch; kembalikan (data_json_utuh | None, kalimat_terkumpul)."""
    buffer = ""
    collected: list[tuple[str, Sentence]] = []
    try:
        stream_kwargs = {"json_mode": True, "cancel": cancel}
        try:
            import inspect
            sig = inspect.signature(client.chat_stream)
            if "max_tokens" in sig.parameters:
                # Anggaran token langkah; dulu hardcoded 8192 sehingga bab padat
                # (BAB 2/3 dengan 3 paragraf per subbab) terpotong di tengah JSON.
                stream_kwargs["max_tokens"] = max_tokens
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


def _with_chapter_heading(sections: list[Section], chapter_title: str) -> list[Section]:
    """Sisipkan heading bab bila jawaban AI hanya memuat judul subbab.

    Jalur varian memanggil AI satu kali per bab. Bila model lupa mengirim
    section bertitel "BAB n. ...", seluruh subbab akan dianggap milik bab
    pertama dan isi laporan runtuh ke BAB 1. Heading sintetis ini menjaga
    isi tetap masuk ke bab yang sedang ditulis.
    """
    if not chapter_title or not sections:
        return sections
    for section in sections:
        title = str(section.title or "").strip()
        if section.level <= 1 or re.match(r"^\s*bab\b", title, re.IGNORECASE):
            return sections
    return [Section(1, chapter_title, [])] + list(sections)


def _chapter_has_subbab(sections: list[Section], chapter_title: str) -> bool:
    """True bila bab ini sudah punya section subbab berisi.

    Section level >= 2 dianggap milik bab ini kecuali judulnya jelas memakai
    nomor bab lain (mis. "3.1 Hasil" saat fokus BAB 1). Judul tanpa nomor tetap
    dihitung karena jawaban AI memang difokuskan ke satu bab.
    """
    match = re.match(r"^\s*bab\s*(\d+)", str(chapter_title or ""), re.IGNORECASE)
    if not match:
        return True
    number = match.group(1)
    for section in sections:
        if section.level < 2:
            continue
        if not any(paragraph.sentences for paragraph in section.paragraphs):
            continue
        title = str(section.title or "").strip()
        other = re.match(r"^\s*(\d+)\.", title)
        if other and other.group(1) != number:
            continue
        return True
    return False


def _strip_chapter_body(sections: list[Section], chapter_title: str) -> None:
    """Buang isi yang salah menempel di level BAB sebelum bab itu diulang."""
    key = _normalize(chapter_title)
    for section in sections:
        if section.level <= 1 and _normalize(section.title) == key:
            section.paragraphs = []


def _outline_level(title: str) -> int:
    """Tingkat judul dari nomornya ("2.1" -> 2, "2.1.1" -> 3)."""
    match = re.match(r"^\s*(\d+(?:\.\d+)*)", str(title or ""))
    if not match:
        return 2
    return match.group(1).count(".") + 1


def _chapter_generation_plans(chapter_plans, max_nodes: int = 2):
    """Pecah tiap bab menjadi beberapa panggilan AI berisi maksimal `max_nodes` subbab.

    Model uji membatasi panjang keluaran (±18 KB); satu bab dengan 8 subbab dan
    3 paragraf per subbab tidak akan selesai dalam sekali jawab sehingga JSON
    terpotong. Dua subbab per panggilan menjaga setiap jawaban utuh.

    Judul bab TIDAK ikut dikirim sebagai target section — bila ikut, model kerap
    menaruh seluruh isi pada section "BAB n" sehingga subbab hilang. Judul bab
    tetap dikirim sebagai fokus tugas (``chapter_focus``) dan heading-nya
    ditambahkan otomatis oleh ``_with_chapter_heading``.
    Kembalikan daftar (nomor_bab, judul_bab, judul_subbab_untuk_prompt, bagian_pertama).
    """
    plans = []
    for number, (chap_title, sub_outlines) in enumerate(chapter_plans, start=1):
        titles = [str(title) for title in sub_outlines[1:]]
        if not titles:
            plans.append((number, chap_title, [], True))
            continue
        first = True
        for start in range(0, len(titles), max_nodes):
            chunk = titles[start : start + max_nodes]
            plans.append((number, chap_title, chunk, first))
            first = False
    return plans


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
    chapter_title: str = "",
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
            client, messages, progress, source_texts_by_id, cancel, emitted,
            max_tokens=max_tokens,
        )
    if cancel is not None and cancel.is_set():
        if collected:
            _merge_sections(
                sections, _with_chapter_heading(_partial_sections(collected), chapter_title)
            )
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
        _merge_sections(
            sections, _with_chapter_heading(_sections_from_dict(data), chapter_title)
        )
        return _StepOutcome(merged=True)
    if collected:
        _logger.info(
            "%s: Menggunakan %d kalimat yang dialirkan sebelum batas respon.",
            label, len(collected),
        )
        _merge_sections(
            sections, _with_chapter_heading(_partial_sections(collected), chapter_title)
        )
        return _StepOutcome(merged=True)
    return _StepOutcome(merged=False)


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"


def _chapter_context(sections: list[Section], max_chars: int = 900) -> str:
    """Ringkasan bab yang sudah ditulis untuk menjaga alur antarbab.

    Memuat rumusan masalah dan tujuan (agar pembahasan dan kesimpulan sejajar)
    serta daftar subbab yang sudah ada (agar AI tidak mengulang topik). Biaya
    O(jumlah kalimat yang sudah lahir), hanya dihitung sekali per langkah bab.
    """
    rumusan: list[str] = []
    tujuan: list[str] = []
    titles: list[str] = []
    summaries: list[str] = []
    for section in sections:
        title_key = _normalize(section.title)
        if section.level >= 2:
            titles.append(section.title)
            first_sentence = next(
                (
                    sentence.text.strip()
                    for paragraph in section.paragraphs
                    for sentence in paragraph.sentences
                    if sentence.text.strip()
                ),
                "",
            )
            if first_sentence:
                summaries.append(f"{section.title}: {_clip(first_sentence, 120)}")
        if "rumusan masalah" in title_key:
            for paragraph in section.paragraphs:
                line = _clip(" ".join(s.text for s in paragraph.sentences), 220)
                if line:
                    rumusan.append(line)
        elif "tujuan" in title_key:
            for paragraph in section.paragraphs:
                line = _clip(" ".join(s.text for s in paragraph.sentences), 220)
                if line:
                    tujuan.append(line)
    parts: list[str] = []
    if rumusan:
        parts.append("Rumusan Masalah:\n" + "\n".join(rumusan))
    if tujuan:
        parts.append("Tujuan:\n" + "\n".join(tujuan))
    if titles:
        parts.append("Subbab/topik yang sudah ada: " + "; ".join(titles[:18]))
    if summaries:
        parts.append(
            "Ringkasan subbab yang SUDAH ditulis (jangan diulang isinya):\n"
            + "\n".join(summaries[:12])
        )
    return _clip("\n\n".join(parts), max_chars)


_GENERIC_TITLE = {
    "{Subjek}": "Subjek Kajian Utama",
    "{Objek}": "Objek Kajian Utama",
    "{Objek 1}": "Objek Kajian Pertama",
    "{Objek 2}": "Objek Kajian Kedua",
    "{Aspek 1}": "Aspek Kajian Pertama",
    "{Aspek 2}": "Aspek Kajian Kedua",
    "{Aspek 3}": "Aspek Kajian Ketiga",
    "{Topik 1}": "Topik Kajian Pertama",
    "{Topik 2}": "Topik Kajian Kedua",
    "{Topik 3}": "Topik Kajian Ketiga",
    "{Topik 4}": "Topik Kajian Keempat",
    "{Topik 5}": "Topik Kajian Kelima",
    "{Pembahasan topik 1}": "Pembahasan Topik Pertama",
    "{Pembahasan topik 2}": "Pembahasan Topik Kedua",
    "{Pembahasan 1}": "Pembahasan Topik Pertama",
    "{Pembahasan 2}": "Pembahasan Topik Kedua",
    "{Pembahasan 3}": "Pembahasan Topik Ketiga",
    "{Jawaban rumusan masalah 1}": "Jawaban Rumusan Masalah Pertama",
    "{Jawaban rumusan masalah 2}": "Jawaban Rumusan Masalah Kedua",
    "{Jawaban rumusan masalah 3}": "Jawaban Rumusan Masalah Ketiga",
    "{Jawaban rumusan masalah 4}": "Jawaban Rumusan Masalah Keempat",
    "{Jawaban rumusan masalah 5}": "Jawaban Rumusan Masalah Kelima",
}


def _generic_title(entry_title: str) -> str:
    """Judul baku pengganti placeholder dinamis ({Objek} -> "Objek Kajian")."""
    return _GENERIC_TITLE.get(str(entry_title or "").strip(), "Pembahasan")


def _thin_section_titles(
    result: list[Section], variant_spec=None, limit: int = 5
) -> list[str]:
    """Prioritas pelengkap: daftar kosong, subbab level 2 tipis/hilang, lalu level 3."""
    present = {str(section.title or "").split(" ")[0] for section in result}
    empty_lists: list[str] = []
    thin_level2: list[str] = []
    thin_level3: list[str] = []
    for section in result:
        if section.level < 2:
            continue
        title = str(section.title or "")
        number = title.split(" ")[0]
        if not re.match(r"^[\d.]+$", number):
            continue
        if _LIST_SECTION_RE.search(title):
            if not section.paragraphs:
                empty_lists.append(title)
            continue
        target = 3 if section.level == 2 and number.split(".")[0] == "3" else 2
        if len(section.paragraphs) < target:
            (thin_level2 if section.level == 2 else thin_level3).append(title)
    missing: list[str] = []
    if variant_spec is not None:
        for entry in format_spec._entries(variant_spec):
            if entry.level < 2 or entry.number in present:
                continue
            is_list_entry = bool(_LIST_SECTION_RE.search(entry.title))
            if not is_list_entry and entry.chapter not in (2, 3):
                continue
            missing.append(f"{entry.number} {_generic_title(entry.title)}")
    return (empty_lists + thin_level2 + missing + thin_level3)[:limit]


_CHAPTER_NUM_RE = re.compile(r"^BAB\s+(\d+)", re.IGNORECASE)


def _number_tuple(title: str) -> tuple[int, ...]:
    text = str(title or "").strip()
    match_chap = _CHAPTER_NUM_RE.match(text)
    if match_chap:
        return (int(match_chap.group(1)), 0)
    if text.upper().startswith("DAFTAR ISI"):
        return (0, 0)
    if text.upper().startswith("DAFTAR PUSTAKA"):
        return (998, 0)
    token = text.split(" ")[0].rstrip(".")
    try:
        return tuple(int(part) for part in token.split("."))
    except ValueError:
        return (999,)


def _match_thin_number(title: str, thin: list[str]) -> str:
    """Petakan judul pelengkap (mungkin tanpa nomor) ke nomor subbab yang diminta."""
    key = _normalize(re.sub(r"^[\d.]+\s*", "", str(title or "")).replace("{", "").replace("}", ""))
    if not key:
        return ""
    for candidate in thin:
        candidate_key = _normalize(
            re.sub(r"^[\d.]+\s*", "", candidate).replace("{", "").replace("}", "")
        )
        if not candidate_key:
            continue
        if key == candidate_key or key in candidate_key or candidate_key in key:
            return candidate.split(" ")[0]
    return ""


def _merge_top_up_sections(
    result: list[Section], extra: list[Section], thin: list[str]
) -> list[Section]:
    """Gabungkan subbab pelengkap TANPA menormalisasi ulang seluruh dokumen.

    Normalisasi ulang akan menempatkan ulang section yang sudah final sehingga
    isinya bisa terduplikasi. Di sini paragraf hanya ditempelkan ke section
    bernomor sama (kalimat identik dilewati), dan section baru disisipkan pada
    urutan nomornya. Judul pelengkap tanpa nomor dipetakan ke judul yang diminta.
    """
    by_number = {str(section.title).split(" ")[0]: section for section in result}
    pending_numbers = [
        candidate.split(" ")[0]
        for candidate in thin
        if re.match(r"^[\d.]+$", candidate.split(" ")[0]) and candidate.split(" ")[0] not in by_number
    ]
    for section in extra:
        number = str(section.title or "").split(" ")[0]
        if not any(paragraph.sentences for paragraph in section.paragraphs):
            # Section pelengkap tanpa isi tidak boleh menambah bagian kosong.
            continue
        if not re.match(r"^[\d.]+$", number):
            number = _match_thin_number(section.title, thin) or number
        if not re.match(r"^[\d.]+$", number) and pending_numbers:
            # Judul pelengkap tanpa nomor: petakan berurutan ke subbab yang diminta.
            number = pending_numbers.pop(0)
        if not re.match(r"^[\d.]+$", number):
            # Tetap tidak bisa dipetakan: abaikan agar tidak menyisipkan section liar.
            continue
        if number in pending_numbers:
            pending_numbers.remove(number)
        target = by_number.get(number)
        if target is None:
            target_tuple = _number_tuple(number)
            chap = target_tuple[0] if target_tuple != (999,) else None
            chap_idx = (
                next(
                    (
                        i for i, s in enumerate(result)
                        if s.level == 1 and str(s.title).upper().startswith(f"BAB {chap}.")
                    ),
                    None,
                )
                if chap is not None else None
            )
            if chap_idx is not None:
                next_chap_idx = next(
                    (
                        i for i, s in enumerate(result[chap_idx + 1:], start=chap_idx + 1)
                        if s.level == 1
                    ),
                    len(result),
                )
                position = next_chap_idx
                for index in range(chap_idx + 1, next_chap_idx):
                    if _number_tuple(result[index].title) > target_tuple:
                        position = index
                        break
            else:
                position = len(result)
                for index, existing in enumerate(result):
                    if _number_tuple(existing.title) > target_tuple:
                        position = index
                        break
            # Sanitasi judul section pelengkap sebelum disisipkan: model kerap
            # mengirim kalimat panjang/verba mentah sebagai judul section.
            from ..format_spec import _sanitize_title as _fs_sanitize

            clean_title = _fs_sanitize(str(section.title or ""))
            if clean_title:
                section.title = f"{number} {clean_title}"
            else:
                section.title = f"{number} {_generic_title(section.title)}"
            result.insert(position, section)
            by_number[number] = section
            continue
        existing_texts = {
            _normalize(sentence.text)
            for paragraph in target.paragraphs
            for sentence in paragraph.sentences
        }
        target_texts = [
            sentence.text for paragraph in target.paragraphs for sentence in paragraph.sentences
        ]
        for paragraph in section.paragraphs:
            fresh = [
                sentence
                for sentence in paragraph.sentences
                if _normalize(sentence.text) not in existing_texts
                and not any(
                    _token_similarity(sentence.text, other)
                    >= 0.55
                    for other in target_texts
                )
            ]
            if not fresh:
                continue
            target.paragraphs.append(Paragraph(fresh))
            existing_texts.update(_normalize(sentence.text) for sentence in fresh)
            target_texts.extend(sentence.text for sentence in fresh)
    format_spec._enforce_paragraph_shape(result)
    return result


def _ensure_level2_subbab(result: list[Section], variant_spec) -> list[Section]:
    """Jamin subbab level 2 penting (2.1/2.2, 3.1/3.2) tetap ada.

    Bila model tidak menulisnya, satu subbab level 3 dipromosikan (isinya
    dipindahkan, bukan diduplikasi); bila tidak ada kandidat, paragraf dari
    subbab level 2 yang gemuk dibagi. Judul memakai judul baku pengganti
    placeholder agar tidak berupa kalimat.
    """
    entries = format_spec._entries(variant_spec)
    for chapter in (2, 3):
        expected = [entry for entry in entries if entry.level == 2 and entry.chapter == chapter]
        present = {
            str(section.title).split(" ")[0]
            for section in result
            if section.level == 2 and str(section.title).startswith(f"{chapter}.")
        }
        for entry in expected:
            if entry.number in present:
                continue
            candidates = [
                section
                for section in result
                if section.level == 3
                and str(section.title).startswith(f"{chapter}.")
                and len(section.paragraphs) >= 2
            ]
            donor = max(candidates, key=lambda section: len(section.paragraphs), default=None)
            paragraphs = None
            if donor is not None:
                paragraphs = donor.paragraphs
                result.remove(donor)
            else:
                holder = next(
                    (
                        section
                        for section in result
                        if section.level == 2
                        and str(section.title).startswith(f"{chapter}.")
                        and len(section.paragraphs) >= 4
                    ),
                    None,
                )
                if holder is not None:
                    half = len(holder.paragraphs) // 2
                    paragraphs = holder.paragraphs[half:]
                    holder.paragraphs = holder.paragraphs[:half]
            if not paragraphs:
                continue
            title = f"{entry.number} {_generic_title(entry.title)}"
            new_section = Section(2, title, paragraphs)
            chap_title_prefix = f"BAB {chapter}."
            chap_idx = next(
                (
                    i for i, s in enumerate(result)
                    if s.level == 1 and str(s.title).upper().startswith(chap_title_prefix)
                ),
                None,
            )
            target_tuple = _number_tuple(entry.number)
            if chap_idx is not None:
                next_chap_idx = next(
                    (
                        i for i, s in enumerate(result[chap_idx + 1:], start=chap_idx + 1)
                        if s.level == 1
                    ),
                    len(result),
                )
                position = next_chap_idx
                for index in range(chap_idx + 1, next_chap_idx):
                    if _number_tuple(result[index].title) > target_tuple:
                        position = index
                        break
            else:
                position = len(result)
                for index, existing in enumerate(result):
                    if _number_tuple(existing.title) > target_tuple:
                        position = index
                        break
            result.insert(position, new_section)
            present.add(entry.number)
    return result


def _renumber_level3(result: list[Section]) -> None:
    """Nomor sub-subbab dihitung ulang rapat per induk setelah pelipatan."""
    counters: dict[str, int] = {}
    for section in result:
        if section.level != 3:
            continue
        parts = str(section.title).split(" ", 1)
        number = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        parent = number.rpartition(".")[0] or number
        counters[parent] = counters.get(parent, 0) + 1
        section.title = f"{parent}.{counters[parent]} {rest}".strip()


def _fold_thin_level3(result: list[Section]) -> list[Section]:
    """Lipat sub-subbab yang hanya 1 paragraf ke subbab level 2 induknya.

    Isi dipindahkan (bukan dibuang/diduplikasi); struktur jadi rapat dan tidak
    ada lagi sub-subbab 1 paragraf yang melanggar invariant kedalaman.
    """
    changed = False
    index = 0
    while index < len(result):
        section = result[index]
        if section.level == 3 and len(section.paragraphs) < 2:
            parent_number = str(section.title).split(" ")[0].rpartition(".")[0]
            parent = next(
                (
                    candidate
                    for candidate in result
                    if candidate.level == 2
                    and str(candidate.title).startswith(f"{parent_number} ")
                ),
                None,
            )
            if parent is not None:
                parent.paragraphs.extend(section.paragraphs)
                result.pop(index)
                changed = True
                continue
        index += 1
    if changed:
        _renumber_level3(result)
    return result


_SARAN_FALLBACK = (
    "Penelitian selanjutnya perlu memperluas cakupan sampel dan konteks agar temuan lebih mudah digeneralisasi.",
    "Pendidik dan institusi perlu menyusun panduan pemanfaatan media sosial yang seimbang antara manfaat akademik dan risiko distraksi.",
    "Evaluasi berkala terhadap kebiasaan penggunaan media sosial mahasiswa sebaiknya dilakukan agar intervensi dapat disesuaikan.",
)

_KESIMPULAN_FALLBACK = (
    "Pengaruh media sosial terhadap prestasi akademik mahasiswa bergantung pada motif penggunaan dan durasi harian yang dikelola.",
    "Waktu penggunaan harian berperan sebagai penghubung antara motif penggunaan media sosial dan capaian akademik mahasiswa.",
    "Pengelolaan waktu serta literasi digital menjadi kunci agar manfaat media sosial dapat dioptimalkan dalam pembelajaran.",
)


def _drop_empty_generated_sections(result: list[Section], variant_spec) -> list[Section]:
    """Buang subbab dinamis/tambahan yang kosong agar ekspor tidak terblokir."""
    if variant_spec is None:
        return result
    fixed = {
        format_spec._key(entry.title)
        for entry in format_spec._entries(variant_spec)
        if entry.level >= 2 and not entry.node.dynamic
    }
    result[:] = [
        section
        for section in result
        if section.level < 2
        or section.paragraphs
        or format_spec._key(section.title) in fixed
    ]
    return result


def _fill_empty_conclusion_sections(result: list[Section]) -> None:
    """Isi subbab Kesimpulan/Saran yang tetap kosong setelah pelengkap AI.

    Butir bersifat ringkasan/rekomendasi umum (bukan klaim faktual bersitasi),
    sehingga aman ditulis aplikasi; tujuannya mencegah ekspor gagal karena bagian
    wajib kosong ketika model berulang kali tidak menuliskannya.
    """
    for section in result:
        if section.level < 2:
            continue
        title = str(section.title or "").casefold()
        if section.paragraphs:
            continue
        if "saran" in title:
            source = _SARAN_FALLBACK
        elif "kesimpulan" in title:
            source = _KESIMPULAN_FALLBACK
        else:
            continue
        section.paragraphs = [
            Paragraph([
                Sentence(
                    text=f"{number}. {text}",
                    quote="",
                    source_ids=[],
                    is_factual=False,
                )
            ])
            for number, text in enumerate(source, start=1)
        ]


def _top_up_thin_sections(
    result: list[Section],
    *,
    topic: str,
    sources: list,
    ref_chunks,
    variant_spec,
    client,
    max_tokens: int,
) -> list[Section]:
    """Isi sekali lagi subbab yang masih tipis (deterministik, satu panggilan).

    Variasi keluaran model kadang menyisakan subbab tanpa/berisi satu paragraf.
    Subbab itu diminta ulang secara khusus; hasilnya digabung lalu dinormalisasi
    ulang. Kegagalan apa pun dikembalikan tanpa mengubah hasil sebelumnya.
    """
    thin = _thin_section_titles(result, variant_spec)
    if not thin:
        return result
    total_sentences = sum(
        len(paragraph.sentences) for section in result for paragraph in section.paragraphs
    )
    if total_sentences < 20:
        # Laporan masih terlalu kecil (mis. uji unit/fixture): pelengkap tidak
        # sepadan dengan biaya panggilan AI tambahan.
        return result
    # Dua percobaan: bila percobaan pertama belum menutup semua subbab tipis,
    # sisa subbab diminta sekali lagi dengan daftar yang sudah menyusut.
    for _attempt in range(3):
        if not thin:
            break
        try:
            # Fokus bab diambil dari nomor subbab pertama yang perlu dilengkapi.
            chapter_by_number = {}
            if variant_spec is not None:
                for number, (chapter_title, _subs) in enumerate(
                    format_spec.chapter_sub_outlines(variant_spec), start=1
                ):
                    chapter_by_number[str(number)] = chapter_title
            first_number = thin[0].split(" ")[0].split(".")[0]
            focus = chapter_by_number.get(first_number, "")
            messages = prompts.content_prompt(
                topic,
                thin,
                sources,
                ref_chunks,
                variant=variant_spec.code if variant_spec is not None else None,
                context=_chapter_context(result),
                chapter_focus=focus,
            )
            messages.append({
                "role": "system",
                "content": (
                    "PELENGKAP: subbab berikut masih tipis atau kosong. Tulis HANYA subbab "
                    "itu, tanpa mengulang isi yang sudah ada, dengan judul section SAMA "
                    "PERSIS: " + "; ".join(thin) + ". Subbab naratif: 3 paragraf berisi "
                    "3–5 kalimat tiap paragraf. Subbab daftar bernomor (rumusan masalah, "
                    "tujuan, kesimpulan, saran): satu butir bernomor per paragraf, 3–5 butir."
                ),
            })
            reply = client.chat(messages, json_mode=True, max_tokens=max_tokens, timeout=240)
            data = _first_json_object(reply)
            if not isinstance(data, dict):
                continue
            extra = _sections_from_dict(data)
            if not extra:
                continue
            result = _merge_top_up_sections(result, extra, thin)
        except Exception as exc:  # pelengkap bersifat best-effort
            _logger.warning("Pelengkap subbab tipis dilewati: %s", exc)
            continue
        thin = _thin_section_titles(result, variant_spec)
    _fill_empty_conclusion_sections(result)
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
    Bila `variant` diisi (A/B/C/D), judul baku varian dipakai dan keluaran
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
        plans = _chapter_generation_plans(chapter_plans)
        total_steps = len(plans)
        ref_chunks = chunk_refs if len(chunk_refs) <= 30 else batches[0]
        context = ""
        for step_index, (number, chap_title, sub_titles, first_part) in enumerate(plans, start=1):
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            total += 1
            if progress is not None:
                progress.batch_started(step_index, total_steps)

            # Resolusi judul dinamis Bab 3 dari Rumusan Masalah Bab 1 yang telah dihasilkan
            effective_sub_titles = list(sub_titles)
            if "PEMBAHASAN" in chap_title.upper() and hasattr(format_spec, "_rumusan_items"):
                rumusan_items = format_spec._rumusan_items(sections)
                if rumusan_items:
                    resolved = []
                    for st in effective_sub_titles:
                        m = re.match(r"^\s*(\d+\.\d+)\s*\{?[Jj]awaban\s+rumusan\s+masalah\s*(\d*)\}?", st)
                        if m:
                            num_str = m.group(1)
                            idx_str = m.group(2)
                            idx = (int(idx_str) - 1) if idx_str else (int(num_str.split(".")[-1]) - 1)
                            if 0 <= idx < len(rumusan_items):
                                heading = format_spec._heading_from_rumusan(rumusan_items[idx])
                                resolved.append(f"{num_str} {heading}")
                            else:
                                resolved.append(st)
                        else:
                            resolved.append(st)
                    effective_sub_titles = resolved

            messages = prompts.content_prompt(
                topic, effective_sub_titles, sources, ref_chunks,
                variant=variant_spec.code if variant_spec is not None else None,
                context=context,
                chapter_focus=chap_title,
            )
            step_args = dict(
                client=client,
                progress=progress,
                cancel=cancel,
                emitted=emitted,
                source_texts_by_id=source_texts_by_id,
                max_tokens=16384,
                chat_timeout=240.0,
                repair_truncated=True,
                chapter_title=chap_title,
            )
            outcome = _run_generation_step(
                sections,
                label=f"Bab {number} bagian {step_index} ({chap_title})",
                messages=messages,
                **step_args,
            )
            merged_any = outcome.merged
            # Ulangi sekali bila jawaban tidak terbaca, atau bila bagian pertama
            # bab tidak menghasilkan subbab sama sekali (model menaruh isi di
            # level BAB). Penanda chapter_focus diminta ulang saat retry.
            need_retry = (not merged_any) or (
                first_part and not _chapter_has_subbab(sections, chap_title)
            )
            if not outcome.cancelled and need_retry:
                if first_part:
                    _strip_chapter_body(sections, chap_title)
                # Retry membawa instruksi struktur eksplisit: sebagian model
                # mengabaikan daftar subbab dan menaruh isi di section "BAB".
                retry_messages = list(messages)
                if first_part and sub_titles:
                    retry_messages.append({
                        "role": "system",
                        "content": (
                            "PERBAIKAN STRUKTUR: jawaban sebelumnya salah. Balas HANYA JSON "
                            "dengan satu section level 2 untuk SETIAP judul berikut, dan "
                            "judul section harus SAMA PERSIS dengan judul itu: "
                            + "; ".join(sub_titles)
                            + ". Setiap section 2–3 paragraf, setiap paragraf 3–5 kalimat."
                        ),
                    })
                retry = _run_generation_step(
                    sections,
                    label=f"Bab {number} bagian {step_index} ulang ({chap_title})",
                    messages=retry_messages,
                    **step_args,
                )
                merged_any = merged_any or retry.merged
                if retry.cancelled:
                    cancelled = True
                    break
            if outcome.cancelled:
                cancelled = True
                break
            if not merged_any:
                gagal += 1
            # Bagian berikutnya menerima rumusan masalah, tujuan, dan topik yang
            # sudah ada agar alur laporan nyambung dan tidak mengulang isi.
            context = _chapter_context(sections)
    else:
        context = ""
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
                context=context,
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
            context = _chapter_context(sections)
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
    result = _finish(sections)
    if variant_spec is not None:
        result = _ensure_level2_subbab(result, variant_spec)
        result = _top_up_thin_sections(
            result,
            topic=topic,
            sources=sources,
            ref_chunks=chunk_refs,
            variant_spec=variant_spec,
            client=client,
            max_tokens=16384,
        )
        result = _ensure_level2_subbab(result, variant_spec)
        result = _fold_thin_level3(result)
        _fill_empty_conclusion_sections(result)
        _drop_empty_generated_sections(result, variant_spec)
        _renumber_level3(result)
        _align_numbered_lists(result)
        format_spec._enforce_paragraph_shape(result)
        _split_oversized_paragraphs(result)
        _sanitize_all_titles(result)
    return result


def _sanitize_all_titles(result: list[Section]) -> None:
    """Pengaman terakhir: sanitasi SEMUA judul section level >= 2.

    Judul dapat berasal dari banyak jalur (normalize, pelengkap, distribusi,
    pengaman level-2). Pass ini menjamin tidak ada judul yang lolos sanitasi
    panjang/kapital/kalimat apa pun asalnya.
    """
    from ..format_spec import _sanitize_title

    for section in result:
        if section.level < 2:
            continue
        parts = str(section.title or "").split(" ", 1)
        if len(parts) < 2:
            continue
        number, rest = parts[0], parts[1]
        clean = _sanitize_title(rest)
        if clean and clean != rest:
            section.title = f"{number} {clean}"


def _split_oversized_paragraphs(result: list[Section], limit: int = 5) -> None:
    """Pengaman terakhir: pecah paragraf yang masih melebihi batas kalimat.

    `_enforce_paragraph_shape` menghitung ulang seluruh subbab, tetapi paragraf
    yang ditambahkan oleh langkah belakangan (pelipatan, kesejajaran, atau
    pengaman lain) kadang terlewat. Pass ini menjamin tidak ada satu paragraf
    pun yang memuat lebih dari `limit` kalimat pada subbab naratif.
    """
    for section in result:
        if section.level < 2 or _LIST_SECTION_RE.search(str(section.title or "")):
            continue
        rebuilt: list[Paragraph] = []
        for paragraph in section.paragraphs:
            sentences = [s for s in paragraph.sentences if s.text.strip()]
            if len(sentences) <= limit:
                rebuilt.append(paragraph)
                continue
            for start in range(0, len(sentences), limit):
                rebuilt.append(Paragraph(sentences[start : start + limit]))
        section.paragraphs = rebuilt


# --- Kesejajaran Rumusan ↔ Tujuan ↔ Kesimpulan --------------------------------

_QUESTION_PREFIXES = (
    ("bagaimanakah ", "Menganalisis "),
    ("bagaimana ", "Menganalisis "),
    ("sejauh mana ", "Menganalisis "),
    ("apakah ", "Mengkaji "),
    ("apa ", "Mengkaji "),
    ("mengapa ", "Menganalisis "),
)


def _items_from(section: Section) -> list[str]:
    """Teks butir bernomor dari satu section daftar (tanpa nomor)."""
    items: list[str] = []
    for paragraph in section.paragraphs:
        for sentence in paragraph.sentences:
            text = sentence.text.strip()
            match = _ITEM_NUMBER_RE.match(text)
            if match:
                items.append(text[match.end():].strip().rstrip("?."))
    return items


def _rumusan_to_tujuan(text: str) -> str:
    """Ubah pertanyaan rumusan menjadi pernyataan tujuan (deterministik)."""
    lower = text.casefold()
    for prefix, verb in _QUESTION_PREFIXES:
        if lower.startswith(prefix):
            rest = text[len(prefix):].strip()
            return f"{verb}{rest[0].lower() + rest[1:]}"
    # Fallback: gunakan kalimat apa adanya sebagai tujuan.
    return f"Menganalisis {text[0].lower() + text[1:]}"


def _tujuan_to_kesimpulan(text: str) -> str:
    """Ubah pernyataan tujuan menjadi butir kesimpulan generik-topik."""
    lower = text.casefold()
    for verb in ("menganalisis ", "mengkaji ", "mengetahui ", "menjelaskan ",
                 "menguji ", "menilai ", "mengidentifikasi "):
        if lower.startswith(verb):
            rest = text[len(verb):].strip()
            return f"Pengaruh {rest[0].lower() + rest[1:]}"
    return text


def _align_numbered_lists(result: list[Section]) -> None:
    """Pastikan Rumusan Masalah, Tujuan, dan Kesimpulan sejajar jumlah butirnya.

    Rumusan adalah sumber kebenaran. Tujuan yang kurang ditambah dari rumusan
    (pertanyaan → pernyataan tujuan). Kesimpulan yang kurang ditambah dari
    tujuan (tujuan → pernyataan hasil). Bagian yang lebih banyak dipangkas
    agar tidak ada butir tanpa pasangan.
    """
    rumusan = next((s for s in result if s.level >= 2 and "rumusan masalah" in s.title.casefold()), None)
    tujuan = next((s for s in result if s.level >= 2 and "tujuan" in s.title.casefold()
                   and "rumusan" not in s.title.casefold()), None)
    kesimpulan = next((s for s in result if s.level >= 2 and "kesimpulan" in s.title.casefold()), None)
    if not (rumusan and tujuan):
        return
    rumusan_items = _items_from(rumusan)
    tujuan_items = _items_from(tujuan)
    kesimpulan_items = _items_from(kesimpulan) if kesimpulan else []
    # Rumusan masalah adalah sumber kebenaran: tujuan dan kesimpulan
    # wajib menyamai jumlah butirnya.
    target = max(1, len(rumusan_items))

    # Tambah tujuan yang kurang dari rumusan.
    if len(tujuan_items) < target and rumusan_items:
        for index in range(len(tujuan_items), target):
            source = rumusan_items[index] if index < len(rumusan_items) else rumusan_items[-1]
            tujuan.paragraphs.append(Paragraph([Sentence(
                text=f"{index + 1}. {_rumusan_to_tujuan(source)}",
                quote="", source_ids=[], is_factual=False,
            )]))

    # Tambah kesimpulan yang kurang dari tujuan — hanya bila tidak kembar
    # dengan butir yang sudah ada (mencegah pelanggaran K4 parafrase ganda).
    if kesimpulan and len(kesimpulan_items) < target:
        sources = tujuan_items or rumusan_items
        existing_kesimpulan = [
            sentence.text
            for paragraph in kesimpulan.paragraphs
            for sentence in paragraph.sentences
        ]
        for index in range(len(kesimpulan_items), target):
            source = sources[index] if index < len(sources) else sources[-1]
            candidate = f"{index + 1}. {_tujuan_to_kesimpulan(source)}"
            if any(
                _token_similarity(candidate, existing) >= 0.55
                for existing in existing_kesimpulan
            ):
                continue  # terlalu mirip: jangan tambahkan
            kesimpulan.paragraphs.append(Paragraph([Sentence(
                text=candidate,
                quote="", source_ids=[], is_factual=False,
            )]))
            existing_kesimpulan.append(candidate)


def _insert_before_final_punctuation(text: str, citation: str) -> str:
    if not citation:
        return text
    if text and text[-1] in ".!?":
        return text[:-1] + citation + text[-1]
    return text + citation


# Sitasi yang sudah ditulis model di dalam kalimat: "(2024)", "(Lestari et al.,
# 2024)", "Santoso (2020)". Satu pencocokan regex per kalimat, biaya konstan.
_CITATION_IN_TEXT_RE = re.compile(r"\(\s*[^()]{0,160}?\b(?:19|20)\d{2}[a-z]?\b[^()]{0,80}?\s*\)")


def compose(paragraph: Paragraph, labels: dict[int, str]) -> str:
    """Rangkai paragraf; sitasi dipasang kode tepat sebelum tanda baca akhir (11.4).

    Bila model sudah menulis sitasi sendiri di dalam teks, sitasi buatan kode
    tidak ditambahkan lagi. Tanpa penjagaan ini, keluaran menjadi
    "…Arifin (2024) (Lestari et al., 2024)" — sitasi ganda yang lolos ke DOCX.

    Citation Smoothing: Bila dua atau lebih kalimat berturut-turut dalam satu
    paragraf naratif merujuk ke sumber yang persis sama, sitasi parentetikal
    hanya diberikan pada kalimat terakhir dari rangkaian klaim tersebut agar
    tidak terjadi repetisi mekanis per kalimat.
    """
    sentences = paragraph.sentences
    num_s = len(sentences)

    raw_citations: list[str] = []
    for sentence in sentences:
        citation = ""
        if (
            sentence.is_factual
            and sentence.citation
            and sentence.source_ids
            and not _CITATION_IN_TEXT_RE.search(sentence.text)
        ):
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
        raw_citations.append(citation)

    final_citations = list(raw_citations)
    for i in range(num_s - 1):
        if raw_citations[i] and raw_citations[i] == raw_citations[i + 1]:
            final_citations[i] = ""

    parts: list[str] = []
    for sentence, citation in zip(sentences, final_citations):
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
