"""Aturan sitasi dan daftar pustaka APA 7th (17.1 sampai 17.4).

Penulis dimodelkan eksplisit; kode tidak pernah menebak pemisahan nama (12.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Author:
    family: str
    given: str = ""
    is_org: bool = False
    abbrev: str = ""


@dataclass(frozen=True)
class Source:
    authors: list[Author]
    year: str
    title: str
    container: str = ""
    doi: str = ""
    url: str = ""


@dataclass
class LabeledSource:
    source: Source
    source_index: int
    suffix: str
    in_text: str
    reference: str
    in_text_short: str = ""


def initials(given: str) -> str:
    """Inisial tiap kata nama depan: "Budi Setiawan" menjadi "B. S."."""
    return " ".join(f"{word[0].upper()}." for word in given.split() if word)


def _families(source: Source) -> list[str]:
    return [author.family for author in source.authors]


def _first_family(source: Source) -> str:
    return source.authors[0].family if source.authors else source.title


def _sort_key(source: Source):
    return (_first_family(source).lower(), source.year or "n.d.", (source.title or "").lower())


def _author_key(source: Source):
    return (
        tuple((a.family, a.given, a.is_org, a.abbrev) for a in source.authors),
        source.year or "n.d.",
    )


def _collision(source: Source, other: Source) -> bool:
    """True bila `other` punya penulis pertama dan tahun sama tetapi daftar penulis berbeda."""
    if other is source or not source.authors or not other.authors:
        return False
    if other.authors[0].family != source.authors[0].family:
        return False
    if other.year != source.year:
        return False
    return other.authors != source.authors


def _has_collision(source: Source, family_with: Sequence[Source]) -> bool:
    return any(_collision(source, other) for other in family_with)


def _expansion_depth(source: Source, family_with: Sequence[Source]) -> int:
    """Jumlah penulis yang perlu ditampilkan agar berbeda dari sumber lain yang bentrok."""
    families = _families(source)
    others = [other for other in family_with if _collision(source, other)]
    for depth in range(2, len(families) + 1):
        prefix = families[:depth]
        if all(prefix != _families(other)[:depth] for other in others):
            return depth
    return len(families)


def _join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return ", ".join(names[:-1]) + ", & " + names[-1]


def _et_al_marker(style: str) -> str:
    """Penanda penulis ketiga dan seterusnya; hanya ini yang berubah antar gaya."""
    return "dkk." if style == "dkk" else "et al."


def _author_part(
    source: Source,
    first_use: bool,
    family_with: Sequence[Source],
    style: str = "et_al",
    disambiguate: bool = False,
) -> str:
    authors = source.authors
    if not authors:
        return source.title
    if len(authors) == 1:
        author = authors[0]
        if author.is_org:
            if first_use and author.abbrev:
                return f"{author.family} [{author.abbrev}]"
            return author.abbrev or author.family
        if disambiguate and author.given:
            return f"{initials(author.given)} {author.family}"
        return author.family

    families = _families(source)
    shown = families
    if disambiguate and authors[0].given and not authors[0].is_org:
        # APA 7 (8.19): inisial penulis pertama membedakan nama keluarga yang sama.
        shown = [f"{initials(authors[0].given)} {families[0]}", *families[1:]]
    if _has_collision(source, family_with):
        depth = _expansion_depth(source, family_with)
        if depth >= len(families):
            return _join_names(shown)
        return ", ".join(shown[:depth]) + f", {_et_al_marker(style)}"
    if len(families) == 2:
        return f"{shown[0]} & {shown[1]}"
    return f"{shown[0]} {_et_al_marker(style)}"


def in_text(
    source: Source,
    *,
    first_use: bool = True,
    family_with: Sequence[Source] = (),
    suffix: str = "",
    style: str = "et_al",
    disambiguate: bool = False,
) -> str:
    year = source.year or "n.d."
    return f"({_author_part(source, first_use, family_with, style, disambiguate)}, {year}{suffix})"


def _format_author(author: Author) -> str:
    # Nama dari AI kadang membawa titik/koma menempel ("Nurhaliza."); buang
    # sebelum format agar tidak menjadi "Nurhaliza., & Wijaya." (F10).
    family = author.family.strip().rstrip(".,").strip()
    given = author.given.strip().rstrip(".,").strip()
    if not family:
        return ""
    if author.is_org:
        text = family
    elif given:
        text = f"{family}, {initials(given)}"
    else:
        text = family
    return text if text.endswith(".") else text + "."


def _authors_reference(authors: list[Author]) -> str:
    formatted = [name for name in (_format_author(author) for author in authors) if name]
    if not formatted:
        return ""
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    return ", ".join(formatted[:19]) + ", … " + formatted[-1]


def _link(source: Source) -> str:
    if source.doi:
        return f"https://doi.org/{source.doi}"
    if source.url:
        return source.url
    return ""


def reference(source: Source, *, suffix: str = "") -> str:
    year = source.year or "n.d."
    year_str = f"({year}{suffix})."
    segments: list[str] = []
    author_text = _authors_reference(source.authors) if source.authors else ""
    if author_text:
        segments.append(f"{author_text} {year_str}")
        if source.title:
            segments.append(f"{source.title}.")
    else:
        head = f"{source.title}." if source.title else ""
        segments.append(f"{head} {year_str}".strip())
    if source.container:
        segments.append(f"{source.container}.")
    link = _link(source)
    if link:
        segments.append(link)
    return " ".join(segments)


def _needs_initials(source: Source, others: Sequence[Source]) -> bool:
    """True bila penulis pertama berbeda inisial dengan keluarga yang sama (APA 8.19)."""
    if not source.authors:
        return False
    first = source.authors[0]
    if first.is_org or not first.given:
        return False
    for other in others:
        if other is source or not other.authors:
            continue
        other_first = other.authors[0]
        if other_first.is_org:
            continue
        if other_first.family == first.family and other_first.given != first.given:
            return True
    return False


def order_and_label(
    sources: Sequence[Source], cite: set[int] | None = None, style: str = "et_al"
) -> list[LabeledSource]:
    """Urutkan, tetapkan sufiks a/b/c, lalu hitung sitasi dan daftar pustaka tiap sumber.

    `source_index` selalu indeks asli di `sources`. Bila `cite` diberikan, sumber di luar
    `cite` dibuang lebih dulu supaya tidak ikut menentukan sufiks (17.4).
    `style` hanya mengubah penanda "et al." menjadi "dkk." pada sitasi; daftar
    pustaka tidak berubah.
    """
    indexed = [(i, source) for i, source in enumerate(sources) if cite is None or i in cite]
    indexed.sort(key=lambda pair: _sort_key(pair[1]))

    groups: dict = {}
    for i, source in indexed:
        groups.setdefault(_author_key(source), []).append(i)
    suffix_map: dict[int, str] = {}
    for ids in groups.values():
        if len(ids) > 1:
            for position, i in enumerate(ids):
                suffix_map[i] = chr(ord("a") + position)
        else:
            suffix_map[ids[0]] = ""

    remaining = [source for _, source in indexed]
    labels: list[LabeledSource] = []
    for i, source in indexed:
        suffix = suffix_map.get(i, "")
        disambiguate = _needs_initials(source, remaining)
        labels.append(
            LabeledSource(
                source=source,
                source_index=i,
                suffix=suffix,
                in_text=in_text(
                    source,
                    first_use=True,
                    family_with=remaining,
                    suffix=suffix,
                    style=style,
                    disambiguate=disambiguate,
                ),
                in_text_short=in_text(
                    source,
                    first_use=False,
                    family_with=remaining,
                    suffix=suffix,
                    style=style,
                    disambiguate=disambiguate,
                ),
                reference=reference(source, suffix=suffix),
            )
        )
    return labels
