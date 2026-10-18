"""Pencarian dan penggantian penanda `{{...}}` lintas run (9.1, 9.2, 9.4)."""

from __future__ import annotations

import re
from typing import Iterator

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")


def find_names(text: str) -> list[str]:
    """Semua penanda yang muncul di `text`, berurutan, termasuk yang berulang."""
    return [match.group(0) for match in PLACEHOLDER_RE.finditer(text)]


def iter_paragraphs(document) -> Iterator:
    """Semua paragraf: badan dokumen, sel tabel, header, dan footer (9.2).

    Text box dan shape tidak didukung dan dicatat di README (Task 18).
    """
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph
    for section in document.sections:
        for container in (section.header, section.footer):
            for paragraph in container.paragraphs:
                yield paragraph


def collect_names(document) -> list[str]:
    """Nama penanda unik di seluruh dokumen, berurutan sesuai kemunculan pertama."""
    names: list[str] = []
    seen: set[str] = set()
    for paragraph in iter_paragraphs(document):
        for name in find_names(paragraph.text):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def _run_bounds(runs) -> list[tuple[int, int]]:
    bounds: list[tuple[int, int]] = []
    position = 0
    for run in runs:
        bounds.append((position, position + len(run.text)))
        position += len(run.text)
    return bounds


def _replace_span(runs, bounds: list[tuple[int, int]], start: int, end: int, replacement: str) -> None:
    """Ganti `text[start:end]` lintas run; format run pertama dipertahankan (9.1).

    Teks sebelum penanda tetap di run pertama, teks sesudahnya tetap di run
    terakhir, run yang seluruhnya di dalam penanda dikosongkan.
    """
    first = None
    last = None
    for index, (run_start, run_end) in enumerate(bounds):
        if first is None and start < run_end and end > run_start:
            first = index
        if run_start < end <= run_end:
            last = index
    if first is None or last is None:
        return
    if last == first:
        first_start = bounds[first][0]
        run = runs[first]
        run.text = run.text[: start - first_start] + replacement + run.text[end - first_start :]
        return
    first_run = runs[first]
    first_run.text = first_run.text[: start - bounds[first][0]] + replacement
    for index in range(first + 1, last):
        runs[index].text = ""
    last_run = runs[last]
    last_run.text = last_run.text[end - bounds[last][0] :]


def replace_in_paragraph(paragraph, mapping: dict[str, str]) -> list[str]:
    """Ganti penanda di `mapping`, termasuk yang terpotong antar run (9.1).

    Mengembalikan nama penanda yang benar-benar tergantikan, berurutan dari kiri
    ke kanan. Penanda yang tidak ada di `mapping` dibiarkan apa adanya.
    """
    runs = paragraph.runs
    if not runs:
        return []
    combined = "".join(run.text for run in runs)
    matches = [match for match in PLACEHOLDER_RE.finditer(combined) if match.group(0) in mapping]
    if not matches:
        return []
    replaced: list[str] = []
    for match in reversed(matches):
        _replace_span(runs, _run_bounds(runs), match.start(), match.end(), mapping[match.group(0)])
        replaced.append(match.group(0))
    replaced.reverse()
    return replaced


def is_standalone(paragraph, name: str) -> bool:
    """True bila paragraf hanya berisi satu penanda tanpa teks lain (9.4)."""
    return paragraph.text.strip() == name
