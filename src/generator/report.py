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

import re
from datetime import date

from .ai import content
from .ai.citation import Source, order_and_label
from .ai.content import Paragraph, Section, Sentence
from .verification import STATUS_NON_FACTUAL, STATUS_VERIFIED, SentenceStatus
from .textutil import sanitize_filename  # re-export: kini utilitas umum textutil

_BULAN_INDONESIA = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)

_BULAN_INGGRIS = {
    "january": "Januari", "february": "Februari", "march": "Maret",
    "april": "April", "may": "Mei", "june": "Juni", "july": "Juli",
    "august": "Agustus", "september": "September", "october": "Oktober",
    "november": "November", "december": "Desember",
}
_TANGGAL_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")


def format_tanggal(d: date | None = None) -> str:
    """Tanggal dalam bahasa Indonesia, mis. 18 Oktober 2026 (18.5)."""
    if d is None:
        d = date.today()
    return f"{d.day} {_BULAN_INDONESIA[d.month - 1]} {d.year}"


def format_tanggal_teks(value: str) -> str:
    """Terjemahkan tanggal teks ("25 October 2026") ke bentuk Indonesia.

    PDF, unduhan, dan skrip uji kerap membawa nama bulan berbahasa Inggris;
    tanpa normalisasi ini sampul laporan berbahasa Indonesia bisa memuat
    "25 October 2026". Nilai yang tidak berpola tanggal dikembalikan apa adanya.
    """
    text = " ".join(str(value or "").split())
    match = _TANGGAL_RE.match(text)
    if not match:
        return text
    bulan = _BULAN_INGGRIS.get(match.group(2).casefold())
    if bulan is None:
        return text
    return f"{int(match.group(1))} {bulan} {match.group(3)}"


def _extract_str(obj, key: str) -> str:
    if isinstance(obj, dict):
        return str(obj.get(key, "") or "").strip()
    if hasattr(obj, key):
        return str(getattr(obj, key, "") or "").strip()
    return str(obj or "").strip()


def build_fields(
    judul: str,
    profile,
    dosen,
    mata_kuliah,
    tanggal: date | str | None = None,
) -> dict[str, str]:
    """Isi penanda wajib; penanda opsional hanya bila nilainya tidak kosong (18.5).

    Penanda yang tidak disertakan akan dikosongkan oleh renderer, sehingga tidak
    pernah ada penanda mentah tercetak di dokumen hasil.
    """
    if tanggal is None:
        tanggal = date.today()

    if isinstance(tanggal, str):
        tanggal_str = format_tanggal_teks(tanggal)
        year_str = str(date.today().year)
    else:
        tanggal_str = format_tanggal(tanggal)
        year_str = str(tanggal.year)

    dosen_str = ""
    if hasattr(dosen, "nama"):
        gelar = getattr(dosen, "gelar", "")
        dosen_str = f"{dosen.nama}, {gelar}" if gelar else str(dosen.nama)
    elif dosen:
        dosen_str = str(dosen)

    matkul_str = getattr(mata_kuliah, "nama", str(mata_kuliah or ""))

    fields = {
        "{{JUDUL}}": str(judul or "").strip(),
        "{{NAMA}}": _extract_str(profile, "nama"),
        "{{NIM}}": _extract_str(profile, "nim"),
        "{{DOSEN}}": dosen_str.strip(),
        "{{MATA_KULIAH}}": matkul_str.strip(),
        "{{TANGGAL}}": tanggal_str,
    }
    # Baris identitas sampul ditulis kapital sesuai kebiasaan halaman judul
    # akademik: PROGRAM STUDI AGROTEKNOLOGI / FAKULTAS PERTANIAN / UNIVERSITAS ...
    prodi = _extract_str(profile, "prodi").upper()
    if prodi:
        fields["{{PRODI}}"] = prodi
    fakultas = _extract_str(profile, "fakultas").upper()
    if fakultas:
        fields["{{FAKULTAS}}"] = fakultas
    institusi = _extract_str(profile, "institusi").upper()
    if institusi:
        fields["{{INSTITUSI}}"] = institusi
        fields["{{UNIVERSITAS}}"] = institusi
        fields["{{KAMPUS}}"] = institusi
    if year_str:
        fields["{{TAHUN}}"] = year_str
    return fields


def merge_for_regenerate(old_sections, new_sections, overwrite_all: bool):
    """Keputusan generate ulang (19): bila ada isi lama, catatan manual
    dipertahankan di belakang hasil baru kecuali user memilih tulis ulang semua."""
    if not old_sections:
        return new_sections
    return content.merge_regenerated(old_sections, new_sections, overwrite_all=overwrite_all)


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


def mark_non_factual_done(
    statuses: list[SentenceStatus], done: frozenset[str] | set[str] = frozenset()
) -> set[str]:
    """Tandai semua kalimat dengan is_factual == False sebagai selesai tanpa menandai kalimat perlu_ditinjau (T1.4)."""
    result = set(done)
    for st in statuses:
        if not st.sentence.is_factual:
            result.add(st.sentence.uid)
    return result


def cited_ids(statuses: list[SentenceStatus]) -> set[int]:
    """Indeks sumber yang benar-benar dirujuk kalimat yang akan disitasi."""
    referenced: set[int] = set()
    for item in statuses:
        sentence = item.sentence
        if sentence.is_factual and sentence.citation:
            referenced.update(sentence.source_ids)
    return referenced


def labels_for(sources: list[Source], cited: set[int], style: str = "et_al") -> dict[int, str]:
    """Peta indeks sumber asli ke sitasi dalam kurung; urutan kunci ikut urutan referensi."""
    return {
        labeled.source_index: labeled.in_text
        for labeled in order_and_label(sources, cite=cited, style=style)
    }


def label_forms_for(
    sources: list[Source], cited: set[int], style: str = "et_al"
) -> dict[int, tuple[str, str]]:
    """Peta indeks sumber ke (bentuk panjang, bentuk pendek).

    Bentuk panjang dipakai pada kemunculan pertama (mis. singkatan organisasi),
    bentuk pendek untuk kemunculan berikutnya (APA 7, 8.21).
    """
    return {
        labeled.source_index: (labeled.in_text, labeled.in_text_short)
        for labeled in order_and_label(sources, cite=cited, style=style)
    }


def references_for(sources: list[Source], cited: set[int]) -> list[str]:
    """Entri daftar pustaka hanya untuk sumber yang dikutip."""
    return [labeled.reference for labeled in order_and_label(sources, cite=cited)]


def reference_runs_for(sources: list[Source], cited: set[int]) -> list[list]:
    """Entri daftar pustaka terpejal per run (teks, italic) untuk renderer DOCX."""
    return [
        labeled.reference_runs
        for labeled in order_and_label(sources, cite=cited)
    ]


def uncited_ids(sources: list[Source], cited: set[int]) -> list[int]:
    """Indeks sumber yang dimasukkan tapi tidak dikutip, untuk peringatan (11.4)."""
    return [index for index in range(len(sources)) if index not in cited]


# --------------------------------------------------------------- serialisasi


def apply_manual_edit(sentence: Sentence, new_text: str) -> Sentence:
    """Kalimat baru hasil suntingan manual; uid dan sumber tetap, asal jadi manual (19)."""
    return Sentence(
        text=new_text,
        quote=sentence.quote,
        source_ids=list(sentence.source_ids),
        is_factual=sentence.is_factual,
        uid=sentence.uid,
        origin="manual",
        citation=sentence.citation,
    )


def display_text(sentence: Sentence, labels: dict[int, str]) -> str:
    """Teks kalimat untuk dokumen review: sitasi tertulis sebelum tanda baca akhir."""
    return content.compose(Paragraph([sentence]), labels)


def strip_rendered_citation(text: str, sentence: Sentence, labels: dict[int, str]) -> str:
    """Buang sitasi yang ikut tersunting; render berikutnya menambahkannya lagi.

    Dokumen review menampilkan `text` yang sudah memuat sitasi. Bila user menyunting
    sebagian kalimat (bukan seluruhnya), sitasi itu masih ada di teks hasil suntingan;
    tanpa dibuang, apply_manual_edit + render menulis sitasi dua kali.
    """
    if not (sentence.is_factual and sentence.citation and sentence.source_ids):
        return text
    inner: list[str] = []
    for source_id in labels:
        if source_id not in sentence.source_ids:
            continue
        label = labels[source_id].strip()
        if label.startswith("(") and label.endswith(")"):
            label = label[1:-1]
        inner.append(label)
    if not inner:
        return text
    citation = " (" + "; ".join(inner) + ")"
    if text.endswith(citation):
        return text[: -len(citation)]
    for mark in ".!?":
        if text.endswith(mark) and text[:-1].endswith(citation):
            return text[: -1 - len(citation)] + mark
    return text


def restore_citation(sentence: Sentence) -> Sentence:
    """Salinan kalimat dengan sitasi dibuka kembali; objek lama tidak diubah."""
    return Sentence(
        text=sentence.text,
        quote=sentence.quote,
        source_ids=list(sentence.source_ids),
        is_factual=sentence.is_factual,
        uid=sentence.uid,
        origin=sentence.origin,
        citation=True,
    )


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
        source_ids=_int_list(raw.get("source_ids", [])),
        is_factual=bool(raw.get("is_factual", True)),
        uid=raw.get("uid", ""),
        origin=raw.get("origin", "ai"),
        citation=bool(raw.get("citation", True)),
    )


def _int_list(values) -> list[int]:
    """Daftar int yang toleran terhadap JSON rusak atau suntingan tangan."""
    result: list[int] = []
    for value in values or []:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


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
