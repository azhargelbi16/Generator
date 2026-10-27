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
    # Data bibliografis tambahan dari CrossRef (APA 7: jurnal, volume(nomor), halaman).
    # Kosong bila sumber lama/tidak diketahui — referensi jatuh ke bentuk lamanya.
    volume: str = ""
    issue: str = ""
    pages: str = ""


@dataclass
class LabeledSource:
    source: Source
    source_index: int
    suffix: str
    in_text: str
    reference: str
    in_text_short: str = ""
    # Referensi terpejal per run: (teks, italic) — dipakai renderer DOCX untuk
    # miringkan nama jurnal + volume sesuai APA 7; kosong bila tidak relevan.
    reference_runs: list = None

    def __post_init__(self):
        if self.reference_runs is None:
            self.reference_runs = []


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


# --- Sentence case judul artikel (APA 7, 17.2) ------------------------------
# Nama diri umum yang kapitalnya dipertahankan; daftar ini boleh tumbuh bila
# ada nama diri lain yang muncul di sumber. Hanya judul artikel yang dikonversi,
# bukan nama jurnal/buku (container).
_TITLE_PROPER_NOUNS = (
    "Vietnam", "China", "Indonesia", "Asia", "America", "WeChat", "Facebook",
    "Zalo", "TikTok", "Telegram", "WhatsApp", "Twitter", "Instagram",
)
_TITLE_PROPER_NOUN_CANON = {name.casefold(): name for name in _TITLE_PROPER_NOUNS}
_KNOWN_ACRONYMS = frozenset({
    "AI", "IOT", "GPS", "GIS", "CNN", "RNN", "LSTM", "SVM", "ANN",
    "FAO", "WHO", "UNESCO", "PBB", "BPS", "USA", "UK", "EU", "COVID-19",
    "DNA", "RNA", "NPK", "PH", "GPA",
})

_TITLE_EDGE_PUNCT = "()[]{}.,;:!?\"'“”‘’—–-"


def _is_uppercase_acronym(core: str) -> bool:
    """True bila kata SEMULA seluruhnya kapital dan berhuruf >= 2 (GPA, COVID-19)."""
    letters = [char for char in core if char.isalpha()]
    return len(letters) >= 2 and all(char.isupper() for char in letters)


def _capitalize_first_alpha(text: str) -> str:
    """Kapitalkan huruf pertama pada teks; tanda baca pembuka dilewati."""
    for position, char in enumerate(text):
        if char.isalpha():
            return text[:position] + char.upper() + text[position + 1:]
    return text


def _sentence_case_title(title: str) -> str:
    """Judul artikel gaya sentence case APA 7 secara deterministik.

    Semua kata dihuruf-kecilkan KECUALI (i) kata pertama judul, (ii) kata
    pertama setelah titik dua, (iii) akronim (kata yang SEMULA seluruhnya
    kapital >= 2 huruf, mis. GPA/COVID-19), dan (iv) nama diri pada daftar
    putih. Bila seluruh judul berasal dari header jurnal yang ALL CAPS, kata-kata
    dikonversi ke huruf kecil terlebih dahulu kecuali akronim baku.
    Tanda kutip dan tanda baca di tepi kata dipertahankan.
    """
    words = str(title or "").split()
    if not words:
        return ""

    # Deteksi bila judul secara dominan berupa ALL CAPS (dari header jurnal)
    alpha_words = [w.strip(_TITLE_EDGE_PUNCT) for w in words if any(c.isalpha() for c in w)]
    caps_count = sum(1 for w in alpha_words if len(w) >= 2 and w.isupper())
    is_all_caps_title = len(alpha_words) >= 3 and (caps_count / len(alpha_words)) >= 0.6

    cased: list[str] = []
    at_sentence_start = True
    for word in words:
        core = word.strip(_TITLE_EDGE_PUNCT)
        if not core:
            cased.append(word)
            at_sentence_start = False
            continue
        start = word.find(core)
        prefix, suffix = word[:start], word[start + len(core):]
        if is_all_caps_title:
            if core.upper() in _KNOWN_ACRONYMS:
                body = core.upper()
            elif core.casefold() in _TITLE_PROPER_NOUN_CANON:
                body = _TITLE_PROPER_NOUN_CANON[core.casefold()]
            elif at_sentence_start:
                body = _capitalize_first_alpha(core.lower())
            else:
                body = core.lower()
        else:
            if _is_uppercase_acronym(core):
                body = core
            elif core.casefold() in _TITLE_PROPER_NOUN_CANON:
                body = _TITLE_PROPER_NOUN_CANON[core.casefold()]
            elif at_sentence_start:
                body = _capitalize_first_alpha(core.lower())
            else:
                body = core.lower()
        cased.append(prefix + body + suffix)
        at_sentence_start = word.rstrip().endswith(":")
    return " ".join(cased)


def _container_segments(source: Source) -> list[tuple[str, bool]]:
    """Segmen container APA 7: (teks, italic).

    Contoh: container "Healthcare", volume 9, issue 10, pages 1272 menjadi
    [("Healthcare, 9", True), ("(10), 1272.", False)] — judul jurnal dan volume
    miring; nomor dan halaman tegak. Tanpa data volume, seluruhnya miring
    ("Healthcare.").
    """
    container = str(source.container or "").strip().rstrip(".")
    if not container:
        return []
    volume = str(source.volume or "").strip()
    issue = str(source.issue or "").strip()
    pages = str(source.pages or "").strip().rstrip(".")
    italic_text = f"{container}, {volume}" if volume else container
    tail = ""
    if issue:
        tail += f"({issue})"
    if pages:
        tail += (", " if tail else "") + pages
    if tail:
        return [(italic_text, True), (tail + ".", False)]
    return [(italic_text + ".", True)]


def reference_segments(source: Source, *, suffix: str = "") -> list[tuple[str, bool]]:
    """Referensi APA 7 terpejal per run: (teks, italic)."""
    year = source.year or "n.d."
    year_str = f"({year}{suffix})."
    segs: list[tuple[str, bool]] = []
    author_text = _authors_reference(source.authors) if source.authors else ""
    title = _sentence_case_title(source.title) if source.title else ""
    if author_text:
        segs.append((f"{author_text} {year_str}", False))
        if title:
            segs.append((f"{title}.", False))
    else:
        head = f"{title}." if title else ""
        segs.append((f"{head} {year_str}".strip(), False))
    segs.extend(_container_segments(source))
    link = _link(source)
    if link:
        segs.append((link, False))
    return segs


def _join_runs(segments: list[tuple[str, bool]]) -> str:
    """Gabung run menjadi teks; nomor "(10)" menempel pada volume tanpa spasi."""
    out = ""
    for text, _italic in segments:
        if not text:
            continue
        if not out:
            out = text
        elif text.startswith("(") or text.startswith(","):
            out += text
        else:
            out += " " + text
    return out


def reference(source: Source, *, suffix: str = "") -> str:
    return _join_runs(reference_segments(source, suffix=suffix))


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
                reference_runs=reference_segments(source, suffix=suffix),
            )
        )
    return labels
