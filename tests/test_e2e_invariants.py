"""E2E deterministik dengan klien AI palsu — Penjaga Regresi (Fase 0).

Menguji pipeline penuh (generate → normalize → render DOCX) terhadap variasi
bentuk jawaban model, lalu memeriksa invariant struktur/konten/sitasi/ekspor.

``FakeAIClient`` mengembalikan JSON kemasan sesuai judul subbab yang diminta
pada prompt, sehingga perilaku model dapat direproduksi tanpa jaringan.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document

from generator import format_spec
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence, generate_sections
from generator.document import renderer, template

TOPIC = "Pengaruh Media Sosial terhadap Prestasi Akademik Mahasiswa"
VARIANT = "b"
CHAPTER_PLANS = format_spec.chapter_sub_outlines(format_spec.get_variant(VARIANT))
LIST_TITLES = ("rumusan masalah", "tujuan", "kesimpulan", "saran")
NUMBERED = re.compile(r"^\s*(?:\d{1,2}|[a-z])[\.\)]\s+\S")
MARKER = re.compile(r"\[(?:TABEL|GAMBAR|FOTO)\s*:", re.IGNORECASE)

# --- Guard S3 (Fase 2): judul level >= 2 harus frasa nomina bersih -----------
# Kata fungsi & penanda klausa diimpor dari format_spec supaya tes dan aplikasi
# tidak pernah berbeda; JANGAN salin daftarnya di sini.
_FUNCTION_WORDS = format_spec._FUNCTION_WORDS
_CLAUSE_MARKERS = format_spec._CLAUSE_MARKERS
_MAX_TITLE_WORDS = 10
_TRAILING_PUNCT = ".,;:!?\"'-–—"

# Judul baku NON-dinamis varian: sah walau hanya 1–2 kata ("Hasil", "Saran").
# Tanpa pengecualian ini semua run merah karena judul baku varian memang pendek.
_CANONICAL_TITLE_KEYS = {
    format_spec._key(entry.title)
    for entry in format_spec._entries(format_spec.get_variant(VARIANT))
    if entry.level >= 2 and not entry.node.dynamic
}

# Judul dinamis diganti judul nyata per nomor subbab (meniru model patuh aturan:
# frasa nomina 3-7 kata, tanpa kata penanda klausa seperti "dalam"/"yang").
TITLE_REPLACEMENT = {
    "2.1": "Peran Media Sosial",
    "2.1.1": "Motif Penggunaan Mahasiswa",
    "2.1.2": "Durasi Akses Harian",
    "2.1.3": "Pembelajaran Terbuka Jarak Jauh",
    "2.2": "Prestasi Akademik Mahasiswa",
    "2.2.1": "Faktor Akademik Internal",
    "2.2.2": "Mediasi Waktu Belajar",
    "2.2.3": "Keterlibatan Belajar Aktif",
    "3.2.1": "Analisis Motif Penggunaan",
    "3.2.2": "Analisis Waktu Belajar",
}

_VOCAB = (
    "motif interaksi hiburan ekspresi konformitas pencarian informasi waktu durasi "
    "multitasking konsentrasi prestasi akademik mahasiswa kampus digital platform "
    "literasi kolaborasi diskusi umpan balik motivasi stres regulasi jadwal "
    "produktivitas kebiasaan pengukuran survei regresi mediator korelasi temuan "
    "literatur teori model adopsi teknologi keterlibatan partisipasi lingkungan "
    "kebijakan pendidik institusi kurikulum intervensi evaluasi refleksi kapasitas"
).split()


def _word(seed: int) -> str:
    return _VOCAB[(seed * 7 + 3) % len(_VOCAB)]


def _sentence(seed: int) -> str:
    """Kalimat unik per seed agar dedup tidak membuang fixture secara keliru."""
    return (
        f"Kata{seed} menandai Istilah{seed * 3 + 1} lewat Konsep{seed * 7 + 2} "
        f"pada Variabel{seed * 11 + 3} dan Faktor{seed * 13 + 5}."
    )


def _real_title(raw: str) -> str:
    number = str(raw).strip().split(" ")[0]
    if number in TITLE_REPLACEMENT:
        return f"{number} {TITLE_REPLACEMENT[number]}"
    cleaned = re.sub(r"^[\d.]+\s*", "", str(raw)).replace("{", "").replace("}", "").strip()
    return cleaned or "Subbab"


def _requested(messages: list[dict]) -> tuple[str, list[str]]:
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    focus_match = re.search(r'tulis HANYA section untuk "([^"]+)"', system)
    focus = focus_match.group(1) if focus_match else ""
    user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    match = re.search(r"Judul subbab yang wajib ditulis, berurutan: (.+)", user)
    titles = [t.strip() for t in match.group(1).split(",")] if match else []
    return focus, [t for t in titles if t]


def _is_list(title: str) -> bool:
    return any(key in title.casefold() for key in LIST_TITLES)


def _section_payload(raw_title: str, index: int, style: str, chapter: str) -> dict:
    title = _real_title(raw_title)
    number = title.split(" ")[0]
    level = number.count(".") + 1 if re.match(r"^[\d.]+$", number) else 2
    if _is_list(title):
        list_seed = int(chapter) * 10000 + sum(ord(char) for char in title) * 7
        prefix = "Disarankan" if "saran" in title.casefold() else "Kata"
        sentences = [
            {"text": f"{item}. {prefix} {_sentence(list_seed + item * 11)}",
             "quote": f"Butir {item}", "source_ids": [0], "is_factual": True}
            for item in range(1, 4)
        ]
        return {"level": 2, "title": title, "paragraphs": [{"sentences": [s]} for s in sentences]}

    paragraphs = []
    base_seed = int(chapter) * 10000 + sum(ord(char) for char in title) * 7 + index * 100
    paragraph_count = 3 if chapter == "3" else 2
    for para_index in range(1, paragraph_count + 1):
        sentences = [
            {"text": _sentence(base_seed + para_index * 10 + kalimat),
             "quote": _sentence(base_seed + para_index * 10 + kalimat),
             "source_ids": [0], "is_factual": True}
            for kalimat in range(1, 5)
        ]
        if style == "flat":
            for sentence_number, sentence in enumerate(sentences, start=1):
                sentence["paragraph"] = para_index
            paragraphs.extend(sentences)
        else:
            paragraphs.append({"sentences": sentences})
    return {"level": level, "title": title, "paragraphs": paragraphs}


class FakeAIClient:
    """Klien AI palsu; perilaku ditentukan oleh ``style`` (lihat daftar di tes)."""

    def __init__(self, style: str = "nested"):
        self.style = style
        self.calls = 0
        self._truncated_once = False

    def chat(self, messages, **kwargs):
        self.calls += 1
        focus, titles = _requested(messages)
        match = re.search(r"BAB\s*(\d+)", focus)
        chapter = match.group(1) if match else "1"
        if self.style == "truncated" and not self._truncated_once:
            self._truncated_once = True
            return '{"sections":[{"level":2,"title":"1.1 Latar Belakang","paragraphs":[{"sent'
        if self.style == "level1_dump":
            paragraphs = []
            for index, title in enumerate(titles, start=1):
                paragraphs.extend(_section_payload(title, index, "nested", chapter)["paragraphs"])
            return json.dumps({"sections": [{
                "level": 1,
                "title": f"BAB {chapter}. JUDUL BAB",
                "paragraphs": paragraphs,
            }]}, ensure_ascii=False)
        sections = []
        for index, title in enumerate(titles, start=1):
            payload = _section_payload(title, index, self.style, chapter)
            if self.style == "long_title":
                payload["title"] = (
                    "Berbagai penelitian telah mengkaji bagaimana " + payload["title"]
                )
            if self.style == "dup_conclusion" and any(
                key in payload["title"].casefold() for key in ("kesimpulan", "saran")
            ):
                set_seed = sum(ord(char) for char in payload["title"])
                payload["paragraphs"] = [
                    {"sentences": [{"text": f"{number}. {_sentence(set_seed + number)}",
                                    "quote": f"Butir {number}", "source_ids": [0],
                                    "is_factual": True}]}
                    for number in (1, 2)
                ] + [
                    {"sentences": [{"text": f"{number}. {_sentence(set_seed + 5000 + number)}",
                                    "quote": f"Butir {number}", "source_ids": [0],
                                    "is_factual": True}]}
                    for number in (1, 2)
                ]
            sections.append(payload)
        sections.insert(0, {"level": 1, "title": f"BAB {chapter}. JUDUL BAB", "paragraphs": []})
        return json.dumps({"sections": sections}, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def _sources() -> list[Source]:
    return [Source(
        [Author("Santoso", "Budi")], "2023", "Studi Media Sosial", "Jurnal Pendidikan",
        doi="10.1/x", volume="9", issue="10", pages="1272",
    )]


def _run_pipeline(tmp_path: Path, style: str):
    client = FakeAIClient(style)
    sections = generate_sections(
        TOPIC,
        format_spec.outline_titles(format_spec.get_variant(VARIANT)),
        _sources(),
        ["teks sumber yang panjang sekali " * 40],
        client,
        variant=VARIANT,
    )
    template_path = tmp_path / f"tpl-{style}.docx"
    doc = Document()
    # Baris identitas sampul (kapital) seperti template akademik.
    doc.add_paragraph("PROGRAM STUDI {{PRODI}}")
    doc.add_paragraph("FAKULTAS {{FAKULTAS}}")
    doc.add_paragraph("{{INSTITUSI}}")
    doc.add_paragraph("{{TAHUN}}")
    for placeholder in template.REQUIRED_PLACEHOLDERS:
        doc.add_paragraph(placeholder)
    doc.save(template_path)
    out_path = tmp_path / f"out-{style}.docx"
    fields = {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS}
    fields.update({
        "{{JUDUL}}": TOPIC, "{{NAMA}}": "Rudi", "{{NIM}}": "1",
        "{{MATA_KULIAH}}": "Metodologi", "{{DOSEN}}": "Dr. X",
        "{{TANGGAL}}": "25 Oktober 2026",
        "{{PRODI}}": "AGROTEKNOLOGI", "{{FAKULTAS}}": "PERTANIAN",
        "{{INSTITUSI}}": "UNIVERSITAS JEMBER", "{{TAHUN}}": "2026",
    })
    reference_runs = [[
        ("Santoso, B. (2023). Studi Media Sosial. ", False),
        ("Jurnal Pendidikan, 9", True),
        ("(10), 1272.", False),
    ]]
    renderer.render_report(
        template_path, fields, sections, reference_runs, None, out_path,
        labels={0: "(Santoso, 2023)"},
    )
    return sections, Document(out_path)


# --------------------------------------------------------------------------- #
# Invariant
# --------------------------------------------------------------------------- #


def _chapter_groups(sections: list[Section]) -> dict[int, list[Section]]:
    groups: dict[int, list[Section]] = {}
    current = 0
    for section in sections:
        if section.level == 1:
            current += 1
            groups[current] = [section]
        else:
            groups.setdefault(current, []).append(section)
    return groups


def _titles(sections: list[Section]) -> list[str]:
    return [section.title for section in sections]


def _texts(sections: list[Section]) -> list[str]:
    return [s.text.strip() for section in sections for p in section.paragraphs for s in p.sentences]


def _title_without_number(title: str) -> str:
    """Judul tanpa nomor subbab: hitungan kata & normalisasi memakai bentuk ini."""
    return re.sub(r"^[\d.]+\s*", "", str(title or "")).strip()


def _chapter_token(title: str) -> str:
    """Nomor bab dari token pertama judul ("2.2.1" -> "2"); "" bila bukan nomor."""
    first = str(title or "").split()[0] if str(title or "").split() else ""
    return first.split(".")[0] if re.fullmatch(r"[\d.]+", first) else ""


def check_s3(sections: list[Section]) -> list[str]:
    """Guard S3 (Fase 2): judul level >= 2 bersih, pendek, dan unik selevel.

    Menolak heading yang (a) lebih dari 10 kata (dihitung tanpa nomor),
    (b) berakhir pada kata fungsi, (c) kembar dengan saudara SELEVEL dalam bab
    yang sama setelah nomor dibuang, (d) kurang dari 3 kata kecuali judul baku
    statis varian, dan (e) memuat penanda klausa (bukan frasa nomina lagi).
    """
    problems: list[str] = []
    seen: dict[tuple[str, int], dict[str, str]] = {}
    for section in sections:
        if section.level < 2:
            continue
        title = str(section.title or "").strip()
        stripped = _title_without_number(title)
        words = stripped.split()
        key = format_spec._key(stripped)
        canonical = key in _CANONICAL_TITLE_KEYS
        if len(words) > _MAX_TITLE_WORDS:
            problems.append(f"S3: judul > 10 kata: {title[:70]}")
        if words and words[-1].strip(_TRAILING_PUNCT).casefold() in _FUNCTION_WORDS:
            problems.append(f"S3: judul berakhir kata fungsi: {title[:70]}")
        if not canonical and any(
            word.strip(_TRAILING_PUNCT).casefold() in _CLAUSE_MARKERS for word in words
        ):
            problems.append(f"S3: judul memuat penanda klausa: {title[:70]}")
        if not canonical and len(words) < 3:
            problems.append(f"S3: judul < 3 kata non-kanonik: {title[:70]}")
        if stripped.rstrip().endswith("."):
            problems.append(f"S3: judul diakhiri titik: {title[:70]}")
        if re.match(
            r"^(berbagai\s+(penelitian|studi)|banyak\s+(penelitian|studi)|"
            r"bagaimana|mengapa|penelitian\s+ini|hasil\s+penelitian)",
            stripped,
            re.I,
        ):
            problems.append(f"S3: judul tampak kalimat: {title[:70]}")
        # (c) Kembar dengan saudara SELEVEL dalam bab yang sama; kelompokkan per
        # (bab, level) supaya dua bab boleh memakai judul baku yang sama.
        group = seen.setdefault((_chapter_token(title), section.level), {})
        if key and key in group:
            problems.append(
                f"S3: judul kembar selevel '{title[:50]}' dengan '{group[key][:50]}'"
            )
        group.setdefault(key, title)
    return problems


def check_structure(sections: list[Section]) -> list[str]:
    problems: list[str] = []
    titles = _titles(sections)

    bab2 = [s for s in sections if s.title.startswith("BAB 2.")]
    if not bab2 or bab2[0].paragraphs:
        problems.append("S1: heading BAB 2 masih memuat paragraf")
    subs2 = [s for s in sections if s.level >= 2 and s.title.startswith("2.")]
    if not any(s.title.startswith("2.1") for s in subs2) or not any(
        s.title.startswith("2.2") for s in subs2
    ):
        problems.append(f"S1: subbab 2.1/2.2 tidak lengkap: {[s.title for s in subs2][:6]}")

    groups = _chapter_groups(sections)
    if 0 in groups:
        problems.append("S2: subbab terdeteksi sebelum BAB 1 dimulai")
    for chapter, members in groups.items():
        level2 = sorted(
            int(s.title.split(" ")[0].split(".")[1])
            for s in members
            if s.level == 2 and s.title.split(" ")[0].count(".") == 1
        )
        if level2 and level2 != list(range(1, len(level2) + 1)):
            problems.append(f"S2: nomor level 2 bab {chapter} tidak rapat: {level2}")
        by_parent: dict[str, list[int]] = {}
        for section in members:
            if section.level != 3:
                continue
            number = section.title.split(" ")[0]
            parent, _, last = number.rpartition(".")
            by_parent.setdefault(parent, []).append(int(last))
        for parent, numbers in by_parent.items():
            numbers.sort()
            if numbers != list(range(1, len(numbers) + 1)):
                problems.append(f"S2: nomor level 3 {parent} tidak rapat: {numbers}")

    problems.extend(check_s3(sections))

    if any("{" in t or "}" in t for t in titles):
        problems.append("S4: judul template {...} tersisa")
    if [t for t in titles if re.search(r"\b(pengisi|tambahan|topik \d)\b", t, re.I)]:
        problems.append("S4: judul pengisi terdeteksi")

    bab4 = [s for s in sections if s.title.startswith("BAB 4.")]
    if bab4 and bab4[0].paragraphs:
        problems.append("S5: paragraf menempel di level BAB 4")
    if not any(s.title.startswith("4.1") for s in sections) or not any(
        s.title.startswith("4.2") for s in sections
    ):
        problems.append("S5: subbab 4.1/4.2 hilang")

    latar = next((s for s in sections if "Latar Belakang" in s.title), None)
    if latar is None or len(latar.paragraphs) < 2:
        problems.append("S7: 1.1 Latar Belakang < 2 paragraf")
    for section in sections:
        if section.level < 2 or _is_list(section.title) or not section.paragraphs:
            continue
        if len(section.paragraphs) > 6:
            problems.append(f"S7: {section.title[:40]} > 6 paragraf")
        if section.title.startswith(("2.", "3.")) and len(section.paragraphs) < 2:
            problems.append(f"S7: {section.title[:40]} < 2 paragraf")
        if section.level == 2 and section.title.startswith("3.") and len(section.paragraphs) < 3:
            problems.append(f"K5: {section.title[:40]} < 3 paragraf")
        for paragraph in section.paragraphs:
            count = len([s for s in paragraph.sentences if s.text.strip()])
            if count > 5:
                problems.append(f"S7: {section.title[:40]} paragraf {count} kalimat")
    return problems


def check_content(sections: list[Section]) -> list[str]:
    problems: list[str] = []
    texts = _texts(sections)
    if any(MARKER.search(t) for t in texts):
        problems.append("K1: penanda [TABEL/GAMBAR/FOTO] tersisa")
    if any(re.search(r"(penanda\s+tabel|disajikan\s+dalam\s+bentuk\s+tabel)", t, re.I) for t in texts):
        problems.append("K1: deskriptor tabel tersisa")
    if any(t[:1].islower() for t in texts):
        problems.append("K2: kalimat berawalan huruf kecil")
    for section in sections:
        if not _is_list(section.title):
            continue
        numbers = [
            NUMBERED.match(s.text.strip()).group(0).strip()
            for p in section.paragraphs for s in p.sentences
            if NUMBERED.match(s.text.strip())
        ]
        if len(numbers) != len(set(numbers)):
            problems.append(f"K3: nomor butir ganda di {section.title[:30]}")
    seen: dict[str, str] = {}
    for section in sections:
        for text in [s.text.strip() for p in section.paragraphs for s in p.sentences]:
            key = " ".join(text.lower().split())
            if key in seen and seen[key] != section.title:
                problems.append("K4: duplikat identik lintas bab")
            seen.setdefault(key, section.title)
    from generator.ai.content import _token_similarity

    for section in sections:
        if section.level < 2:
            continue
        sentences = [s.text for p in section.paragraphs for s in p.sentences]
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                if _token_similarity(sentences[i], sentences[j]) >= 0.55:
                    problems.append(f"K4: parafrase ganda di {section.title[:30]}")
                    break
    return problems


def check_docx(doc) -> list[str]:
    problems: list[str] = []
    texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if any("{{" in t for t in texts):
        problems.append("E1: penanda {{...}} tersisa")
    if not any("TOC" in p._p.xml for p in doc.paragraphs):
        problems.append("E1: field TOC tidak ada")
    if "PAGE" not in doc.sections[0].footer._element.xml:
        problems.append("E1: nomor halaman tidak ada")
    if "PROGRAM STUDI AGROTEKNOLOGI" not in "\n".join(texts[:20]):
        problems.append("E1: sampul prodi tidak terisi")
    italic = [run.text for p in doc.paragraphs for run in p.runs if run.italic]
    if not any("Jurnal Pendidikan, 9" in text for text in italic):
        problems.append("V2: container+volume tidak italic")
    if not any("(10), 1272." in t for t in texts):
        problems.append("V2: volume(nomor), halaman tidak muncul")
    if any(len(NUMBERED.findall(t)) > 1 for t in texts):
        problems.append("S6: beberapa butir dalam satu paragraf")
    if not [t for t in texts if NUMBERED.match(t)]:
        problems.append("S6: tidak ada paragraf butir")
    if not any("(Santoso, 2023)" in t for t in texts):
        problems.append("V1: sitasi dalam teks tidak muncul")
    return problems


def test_e2e_invariants_fake_client(tmp_path):
    """Semua invariant harus hijau pada seluruh variasi jawaban model."""
    failures: dict[str, list[str]] = {}
    for style in ("nested", "flat", "long_title", "level1_dump", "dup_conclusion", "truncated"):
        sections, doc = _run_pipeline(tmp_path, style)
        problems = check_structure(sections) + check_content(sections) + check_docx(doc)
        if problems:
            failures[style] = problems
    assert not failures, failures


# --------------------------------------------------------------------------- #
# Guard S3 (Fase 2) — kasus negatif: guard WAJIB menolak judul buruk
# --------------------------------------------------------------------------- #


def _section(level: int, title: str) -> Section:
    return Section(level, title, [])


def test_guard_s3_menolak_judul_berakhir_kata_fungsi():
    problems = check_s3([_section(2, "2.1 Media sosial telah menjadi bagian yang tidak")])
    assert any("berakhir kata fungsi" in problem for problem in problems), problems


def test_guard_s3_menolak_judul_klausa_menggantung():
    # Bukan frasa nomina: ada klausa "yang dihabiskan di dunia" di tengah judul.
    problems = check_s3([_section(2, "2.2 Durasi waktu harian yang dihabiskan di dunia")])
    assert any("penanda klausa" in problem for problem in problems), problems


def test_guard_s3_menolak_judul_kembar_selevel():
    problems = check_s3([
        _section(2, "3.1 Pembahasan"),
        _section(2, "3.2 Pembahasan"),
    ])
    assert any("kembar selevel" in problem for problem in problems), problems


def test_guard_s3_judul_sama_di_bab_berbeda_tidak_kembar():
    # Judul baku yang sama pada bab berbeda bukan duplikat (cek cakupan bab).
    problems = check_s3([
        _section(3, "3.2 Pembahasan"),
        _section(4, "4.3 Pembahasan"),
    ])
    assert not any("kembar" in problem for problem in problems), problems


def test_guard_s3_menolak_judul_sebelas_kata():
    problems = check_s3([_section(
        2,
        "2.10 Analisis Pengaruh Media Sosial terhadap Prestasi Akademik Mahasiswa "
        "Indonesia Tahun Terakhir",
    )])
    assert any("> 10 kata" in problem for problem in problems), problems


def test_guard_s3_menolak_judul_satu_kata_non_kanonik():
    problems = check_s3([_section(2, "2.4 Motivasi")])
    assert any("< 3 kata" in problem for problem in problems), problems


def test_guard_s3_judul_kanonik_pendek_tetap_sah():
    problems = check_s3([
        _section(3, "3.1 Hasil"),
        _section(3, "3.2 Pembahasan"),
        _section(4, "4.1 Kesimpulan"),
        _section(4, "4.2 Saran"),
        _section(1, "3.3 Tujuan"),  # level 1 tidak diperiksa guard S3
    ])
    assert problems == [], problems


def test_guard_s3_menerima_judul_hasil_pipeline_fase_1(tmp_path):
    """Judul yang sudah disanitasi pipeline (Fase 1) harus lolos guard S3."""
    for style in ("nested", "long_title", "level1_dump"):
        sections = _run_pipeline(tmp_path, style)[0]
        assert check_s3(sections) == [], (style, check_s3(sections))
