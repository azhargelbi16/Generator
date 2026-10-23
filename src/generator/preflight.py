"""Engine pemeriksaan akhir (preflight) sebelum ekspor — murni, tanpa Qt (addendum D.3).

`run_checks` menghasilkan baris status yang selalu tampil; `find_issues`
menghasilkan temuan yang memicu dialog perbaikan (pilihan B: dialog hanya bila
ada temuan). `fix_mojibake` bekerja pada salinan baru; data asli tak disentuh.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ai.citation import Author, Source
from .ai.content import Paragraph, Section, Sentence
from .report import can_export, labels_for, pending, references_for, sanitize_filename
from .textutil import has_mojibake, repair_mojibake
from .verification import SentenceStatus

_STYLE_LABEL = {"et_al": "et al.", "dkk": "dkk."}
_FILENAME_UNSAFE = frozenset('.<>:"/\\|?*')


@dataclass
class Check:
    label: str
    ok: bool
    detail: str = ""


@dataclass
class PreflightIssue:
    kind: str  # "mojibake" | "filename" | "citation_style" | "logo_missing" | "pending"
    message: str


def _mojibake_names(sources: list[Source]) -> list[str]:
    """Nama penulis atau judul yang masih memuat mojibake."""
    names: list[str] = []
    for source in sources:
        for author in source.authors:
            for value in (author.family, author.given, author.abbrev):
                if value and has_mojibake(value):
                    names.append(value)
        for value in (source.title, source.container):
            if value and has_mojibake(value):
                names.append(value)
    return names


def _filename_needs_fix(judul: str) -> bool:
    if has_mojibake(judul):
        return True
    return any(char in _FILENAME_UNSAFE for char in judul)


def _logo_ok(logo_path: Path | None) -> bool:
    return logo_path is not None and Path(logo_path).is_file()


def _citation_problems(
    sources: list[Source],
    statuses: list[SentenceStatus],
    cited: set[int],
) -> list[str]:
    """Masalah nyata antara sitasi di teks dan entri daftar pustaka."""
    problems: list[str] = []
    out_of_range = sorted(
        {
            source_id
            for item in statuses
            if item.sentence.is_factual and item.sentence.citation
            for source_id in item.sentence.source_ids
            if not 0 <= source_id < len(sources)
        }
    )
    if out_of_range:
        problems.append(
            "sitasi menunjuk sumber di luar daftar: " + ", ".join(map(str, out_of_range))
        )
    valid_cited = [index for index in sorted(cited) if 0 <= index < len(sources)]
    tanpa_penulis = [
        index for index in valid_cited if not sources[index].authors and not sources[index].title
    ]
    if tanpa_penulis:
        problems.append(
            "entri pustaka tanpa penulis dan judul: sumber "
            + ", ".join(str(index + 1) for index in tanpa_penulis)
        )
    tanpa_judul = [
        index
        for index in valid_cited
        if sources[index].title.strip() == "" and index not in tanpa_penulis
    ]
    if tanpa_judul:
        problems.append(
            "entri pustaka tanpa judul: sumber "
            + ", ".join(str(index + 1) for index in tanpa_judul)
        )
    return problems


def run_checks(
    judul: str,
    sources: list[Source],
    statuses: list[SentenceStatus],
    cited: set[int],
    logo_path: Path | None,
    style: str = "et_al",
    done: frozenset[str] = frozenset(),
) -> list[Check]:
    """Baris status pemeriksaan akhir; selalu berisi keenam baris."""
    export_ok, export_msg = can_export(statuses, done)
    labels = labels_for(sources, cited, style=style)
    references = references_for(sources, cited)
    mojibake = _mojibake_names(sources)
    safe_name = sanitize_filename(judul)
    problems = _citation_problems(sources, statuses, cited)
    return [
        Check("Kalimat tertunda", export_ok, export_msg),
        Check(
            "Sitasi & pustaka konsisten",
            not problems,
            "; ".join(problems) or f"{len(labels)} sitasi · {len(references)} entri pustaka",
        ),
        Check("Nama berkas", not _filename_needs_fix(judul), safe_name),
        Check("Nama penulis", not mojibake, "; ".join(mojibake)),
        Check("Logo", _logo_ok(logo_path), str(logo_path or "Belum dipilih")),
        Check("Gaya sitasi", style in _STYLE_LABEL, _STYLE_LABEL.get(style, f"Tidak didukung: {style}")),
    ]


def find_issues(
    judul: str,
    sources: list[Source],
    statuses: list[SentenceStatus],
    cited: set[int],
    logo_path: Path | None,
    style: str = "et_al",
    done: frozenset[str] = frozenset(),
) -> list[PreflightIssue]:
    """Temuan yang memicu dialog Pemeriksaan Akhir; kosong berarti ekspor langsung."""
    issues: list[PreflightIssue] = []
    tertunda = pending(statuses, done)
    if tertunda:
        issues.append(PreflightIssue("pending", f"Masih ada {len(tertunda)} kalimat tertunda."))
    mojibake = _mojibake_names(sources)
    if mojibake:
        issues.append(
            PreflightIssue("mojibake", "Nama rusak: " + "; ".join(sorted(set(mojibake))))
        )
    if _filename_needs_fix(judul):
        issues.append(
            PreflightIssue("filename", f"Nama berkas akan menjadi '{sanitize_filename(judul)}'.")
        )
    if not _logo_ok(logo_path):
        issues.append(PreflightIssue("logo_missing", "Logo belum dipilih atau berkas tidak ada."))
    if style not in _STYLE_LABEL:
        issues.append(PreflightIssue("citation_style", f"Gaya sitasi '{style}' tidak didukung."))
    return issues


def fix_mojibake(
    sources: list[Source], sections: list[Section]
) -> tuple[list[Source], list[Section]]:
    """Salinan baru sources dan sections dengan teks mojibake yang diperbaiki."""
    new_sources = [
        Source(
            authors=[
                Author(
                    family=repair_mojibake(author.family),
                    given=repair_mojibake(author.given),
                    is_org=author.is_org,
                    abbrev=repair_mojibake(author.abbrev),
                )
                for author in source.authors
            ],
            year=source.year,
            title=repair_mojibake(source.title),
            container=repair_mojibake(source.container),
            doi=source.doi,
            url=source.url,
        )
        for source in sources
    ]
    new_sections = [
        Section(
            level=section.level,
            title=repair_mojibake(section.title),
            paragraphs=[
                Paragraph(
                    sentences=[
                        Sentence(
                            text=repair_mojibake(sentence.text),
                            quote=repair_mojibake(sentence.quote),
                            source_ids=list(sentence.source_ids),
                            is_factual=sentence.is_factual,
                            uid=sentence.uid,  # uid stabil: status review tak rusak
                            origin=sentence.origin,
                            citation=sentence.citation,
                        )
                        for sentence in paragraph.sentences
                    ]
                )
                for paragraph in section.paragraphs
            ],
        )
        for section in sections
    ]
    return new_sources, new_sections
