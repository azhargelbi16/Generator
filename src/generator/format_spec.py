"""Format baku laporan: varian A/B/C dan normalisasi struktur.

Modul ini adalah satu-satunya sumber kebenaran bentuk laporan. Prompt AI memakai
`format_block()` supaya model tidak bebas mengarang bab, dan keluaran model
dinormalisasi dengan `normalize_sections()` supaya penomoran tetap pakem walau
model membandel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "Node",
    "Variant",
    "VARIANTS",
    "get_variant",
    "variant_choices",
    "outline_titles",
    "skeleton_lines",
    "format_block",
    "normalize_sections",
]


@dataclass(frozen=True)
class Node:
    """Satu judul pada struktur baku; nomor dihitung saat traversal."""

    level: int
    title: str
    hint: str = ""
    dynamic: bool = False
    optional: bool = False


@dataclass(frozen=True)
class Variant:
    code: str
    name: str
    description: str
    nodes: tuple[Node, ...]


def _n(level: int, title: str, hint: str = "", dynamic: bool = False, optional: bool = False) -> Node:
    return Node(level, title, hint, dynamic, optional)


VARIANTS: tuple[Variant, ...] = (
    Variant(
        code="A",
        name="Responsi/tinjauan (beberapa objek)",
        description="Laporan responsi atau tinjauan dengan beberapa objek bahasan.",
        nodes=(
            _n(1, "PENDAHULUAN"),
            _n(2, "Latar Belakang", "konteks, urgensi, kesenjangan; data hanya bila ada di sumber"),
            _n(2, "Rumusan Masalah", "daftar bernomor, tiap butir berupa pertanyaan"),
            _n(2, "Tujuan", "daftar bernomor, sejajar dengan rumusan masalah"),
            _n(1, "TINJAUAN PUSTAKA"),
            _n(2, "{Subjek}", "hal utama yang dibahas", dynamic=True),
            _n(3, "{Aspek 1}", dynamic=True),
            _n(3, "{Aspek 2}", dynamic=True),
            _n(3, "{Aspek 3}", dynamic=True),
            _n(2, "{Objek 1}", "hal yang dianalisis terhadap subjek", dynamic=True),
            _n(3, "{Aspek 1}", dynamic=True),
            _n(3, "{Aspek 2}", dynamic=True),
            _n(2, "{Objek 2}", dynamic=True),
            _n(3, "{Aspek 1}", dynamic=True),
            _n(3, "{Aspek 2}", dynamic=True),
            _n(1, "HASIL DAN PEMBAHASAN"),
            _n(2, "Hasil", "tabel hasil ditulis sebagai penanda [TABEL: ...]"),
            _n(2, "Pembahasan"),
            _n(3, "{Pembahasan topik 1}", dynamic=True),
            _n(3, "{Pembahasan topik 2}", dynamic=True),
            _n(1, "PENUTUP"),
            _n(2, "Kesimpulan", "butir bernomor, sejajar dengan tujuan"),
            _n(2, "Saran", "butir bernomor"),
        ),
    ),
    Variant(
        code="B",
        name="Ringkas (satu objek)",
        description="Laporan ringkas dengan satu objek bahasan.",
        nodes=(
            _n(1, "PENDAHULUAN"),
            _n(2, "Latar Belakang", "konteks, urgensi, kesenjangan; data hanya bila ada di sumber"),
            _n(2, "Rumusan Masalah", "daftar bernomor, tiap butir berupa pertanyaan"),
            _n(2, "Tujuan", "daftar bernomor, sejajar dengan rumusan masalah"),
            _n(1, "TINJAUAN PUSTAKA"),
            _n(2, "{Subjek}", "hal utama yang dibahas", dynamic=True),
            _n(3, "{Aspek 1}", dynamic=True),
            _n(3, "{Aspek 2}", dynamic=True),
            _n(3, "{Aspek 3}", dynamic=True),
            _n(2, "{Objek}", "hal yang dianalisis terhadap subjek", dynamic=True),
            _n(3, "{Aspek 1}", dynamic=True),
            _n(3, "{Aspek 2}", dynamic=True),
            _n(3, "{Aspek 3}", dynamic=True),
            _n(1, "HASIL DAN PEMBAHASAN"),
            _n(2, "Hasil", "tabel hasil ditulis sebagai penanda [TABEL: ...]"),
            _n(2, "Pembahasan"),
            _n(3, "{Pembahasan topik 1}", dynamic=True),
            _n(3, "{Pembahasan topik 2}", dynamic=True),
            _n(1, "KESIMPULAN DAN SARAN"),
            _n(2, "Kesimpulan", "butir bernomor, sejajar dengan tujuan"),
            _n(2, "Saran", "butir bernomor"),
        ),
    ),
    Variant(
        code="C",
        name="Praktikum",
        description="Laporan praktikum: metodologi, alat/bahan, langkah kerja.",
        nodes=(
            _n(1, "PENDAHULUAN"),
            _n(2, "Latar Belakang", "konteks, urgensi, kesenjangan; data hanya bila ada di sumber"),
            _n(2, "Tujuan", "daftar bernomor"),
            _n(1, "METODOLOGI"),
            _n(2, "Tempat dan Waktu Praktikum", "isi manual bila tidak ada di sumber"),
            _n(2, "Alat dan Bahan"),
            _n(3, "Alat", "daftar bernomor"),
            _n(3, "Bahan", "daftar bernomor"),
            _n(2, "Metode Praktikum", "langkah bernomor"),
            _n(1, "HASIL DAN PEMBAHASAN"),
            _n(2, "Hasil", "tabel hasil ditulis sebagai penanda [TABEL: ...]"),
            _n(2, "Pembahasan", "paragraf pembuka"),
            _n(3, "{Pembahasan 1}", dynamic=True),
            _n(3, "{Pembahasan 2}", dynamic=True),
            _n(3, "{Pembahasan 3}", dynamic=True),
            _n(1, "PENUTUP"),
            _n(2, "Kesimpulan", "butir bernomor, sejajar dengan tujuan"),
            _n(2, "Saran (opsional)", "hapus bila kosong", optional=True),
        ),
    ),
)

_RULES = (
    "FORMAT WAJIB:\n"
    "- Gunakan persis struktur bab dan subbab varian di bawah; jangan menambah, "
    "menghapus, atau mengubah nomor serta judul tetap.\n"
    '- Judul bab: "BAB n. JUDUL KAPITAL". Subbab: n.n. Sub-subbab: n.n.n. Butir huruf: a., b.\n'
    "- Ganti judul bertanda {..} dengan judul nyata dari topik dan sumber; jangan biarkan "
    "tanda kurawal tertinggal.\n"
    "- Satu butir daftar = satu paragraf terpisah, diawali angka atau huruf.\n"
    "- Daftar bernomor hanya untuk rumusan masalah, tujuan, kesimpulan, saran, alat/bahan, "
    "dan langkah kerja.\n"
    "- Kesimpulan sejajar jumlah dan urutannya dengan tujuan.\n"
    "- Jangan membuat tabel, gambar, foto, atau diagram. Tulis penanda [TABEL: ...], "
    "[GAMBAR: ...], atau [FOTO: ...] pada paragraf sendiri.\n"
    '- Tabel yang berasal dari sumber diikuti baris "Sumber: ...".\n'
    "- Jangan mengarang angka, tahun, nama, istilah teknis, atau rujukan. Bila tidak ada di "
    "sumber, kosongkan bagian itu.\n"
    "- Setiap klaim faktual memakai sitasi dari sumber yang diberikan.\n"
    "- Bagian bertanda (opsional) dihapus bila tidak ada isinya.\n"
    "- Isi setiap section dengan level: 1 untuk bab, 2 untuk subbab, 3 untuk sub-subbab."
)

_NUMBER_PREFIX = re.compile(
    r"^\s*(?:bab\s+[0-9ivxlc]+\.?|(?:\d+\.)*\d+\.?)\s*",
    re.IGNORECASE,
)
_KEY_RE = re.compile(r"[^0-9a-z]+")


@dataclass(frozen=True)
class _Entry:
    level: int
    number: str
    title: str
    hint: str
    node: Node
    chapter: int


def get_variant(code: str | Variant | None) -> Variant | None:
    """Kembalikan varian untuk kode A/B/C; kode kosong atau tak dikenal berarti bebas."""
    if isinstance(code, Variant):
        return code
    key = (code or "").strip().upper()
    for variant in VARIANTS:
        if variant.code == key:
            return variant
    return None


def variant_choices() -> list[tuple[str, str]]:
    """Pilihan untuk combo UI: (kode, label). Kode kosong berarti outline bebas."""
    choices = [("", "Bebas (outline manual)")]
    choices.extend((variant.code, f"{variant.code} — {variant.name}") for variant in VARIANTS)
    return choices


def _entries(variant: Variant) -> list[_Entry]:
    entries: list[_Entry] = []
    chapter = sub = subsub = 0
    for node in variant.nodes:
        if node.level == 1:
            chapter += 1
            sub = subsub = 0
            number = f"BAB {chapter}."
        elif node.level == 2:
            sub += 1
            subsub = 0
            number = f"{chapter}.{sub}"
        else:
            subsub += 1
            number = f"{chapter}.{sub}.{subsub}"
        entries.append(_Entry(node.level, number, node.title, node.hint, node, chapter))
    return entries


def skeleton_lines(variant: Variant) -> list[str]:
    """Baris struktur baku dengan indentasi dan catatan singkat."""
    lines: list[str] = []
    for entry in _entries(variant):
        indent = "  " * (entry.level - 1)
        line = f"{indent}{entry.number} {entry.title}"
        hint = entry.hint
        if entry.node.optional:
            line += f" ({hint})" if hint else " (opsional)"
        elif hint:
            line += f" — {hint}"
        lines.append(line)
    return lines


def outline_titles(variant: Variant) -> list[str]:
    """Judul bab bernomor untuk mengisi editor outline."""
    return [f"{entry.number} {entry.title}" for entry in _entries(variant) if entry.level == 1]


def format_block(variant: Variant) -> str:
    """Aturan wajib + struktur varian untuk ditempel ke prompt sistem."""
    structure = "\n".join(skeleton_lines(variant))
    return f"{_RULES}\n\nSTRUKTUR WAJIB (varian {variant.code} — {variant.name}):\n{structure}"


def _clean_title(title: str) -> str:
    text = " ".join(str(title or "").split())
    text = _NUMBER_PREFIX.sub("", text)
    return text.strip(" .:-")


def _key(title: str) -> str:
    return _KEY_RE.sub(" ", _clean_title(title).casefold()).strip()


def _has_text(paragraphs) -> bool:
    return any(
        sentence.text.strip()
        for paragraph in paragraphs
        for sentence in paragraph.sentences
    )


def _merge_paragraphs(target: dict, key: str, paragraphs) -> None:
    target.setdefault(key, []).extend(paragraphs)


def _match_chapter(key: str, chapters: list[_Entry], used: set[int]) -> int | None:
    if not key:
        return None
    for index, entry in enumerate(chapters):
        if index in used:
            continue
        chapter_key = _key(entry.title)
        if chapter_key == key or chapter_key in key or key in chapter_key:
            return index
    return None


def _assign_blocks(entries: list[_Entry], blocks) -> tuple[dict, list]:
    """Petakan blok AI ke subbab baku; sisanya menjadi bagian tambahan."""
    nodes = [entry for entry in entries if entry.level >= 2]
    assigned: dict[str, list] = {}
    titles: dict[str, str] = {}
    used: set[int] = set()
    pending = []
    for block in blocks:
        key = _key(block.title)
        if not _has_text(block.paragraphs):
            pending.append(block)
            continue
        match = None
        for index, entry in enumerate(nodes):
            if index in used or entry.node.dynamic:
                continue
            if _key(entry.title) == key:
                match = index
                break
        if match is None:
            pending.append(block)
            continue
        used.add(match)
        _merge_paragraphs(assigned, nodes[match].number, block.paragraphs)
    dynamic = [index for index, entry in enumerate(nodes) if entry.node.dynamic]
    cursor = 0
    extras = []
    for block in pending:
        if not _has_text(block.paragraphs):
            continue
        level = 2 if block.level <= 2 else 3
        candidate = None
        for position, index in enumerate(dynamic[cursor:], start=cursor):
            if index in used or nodes[index].level != level:
                continue
            candidate = position
            break
        if candidate is None:
            for position, index in enumerate(dynamic[cursor:], start=cursor):
                if index not in used:
                    candidate = position
                    break
        if candidate is None:
            extras.append(block)
            continue
        index = dynamic[candidate]
        used.add(index)
        _merge_paragraphs(assigned, nodes[index].number, block.paragraphs)
        titles[nodes[index].number] = _clean_title(block.title)
        cursor = candidate + 1
    return {"paragraphs": assigned, "titles": titles}, extras


def normalize_sections(variant: Variant, sections: list) -> list:
    """Paksa keluaran AI mengikuti struktur varian: nomor, judul tetap, dan urutan.

    Bagian yang tidak dikenal tetap dipakai isinya sebagai subbab tambahan di akhir
    babnya, supaya tidak ada tulisan yang hilang. Bab dan subbab tetap yang tidak
    dihasilkan AI tetap muncul sebagai judul kosong agar pengguna bisa mengisinya.
    """
    from .ai.content import Section

    entries = _entries(variant)
    chapters = [entry for entry in entries if entry.level == 1]
    chapter_body: dict[int, list] = {index: [] for index in range(len(chapters))}
    heading_used: set[int] = set()
    blocks: dict[int, list] = {index: [] for index in range(len(chapters))}
    current: int | None = None
    for section in sections:
        title = _clean_title(section.title)
        if section.level <= 1 or title.casefold().startswith("bab "):
            index = _match_chapter(_key(title), chapters, heading_used)
            if index is None:
                index = next(
                    (candidate for candidate in range(len(chapters)) if candidate not in heading_used),
                    len(chapters) - 1,
                )
            heading_used.add(index)
            current = index
            chapter_body[index].extend(section.paragraphs)
            continue
        if current is None:
            current = _chapter_for_title(_key(title), entries, chapters)
        if current is not None:
            blocks[current].append(section)

    result: list = []
    for index, chapter in enumerate(chapters):
        result.append(
            Section(1, f"{chapter.number} {chapter.title}", chapter_body.get(index, []))
        )
        chapter_entries = [entry for entry in entries if entry.chapter == chapter.chapter]
        assignment, extras = _assign_blocks(chapter_entries, blocks.get(index, []))
        assigned = assignment["paragraphs"]
        titles = assignment["titles"]
        skip_children: set[str] = set()
        next_sub = chapter.chapter
        for entry in chapter_entries:
            if entry.level == 2:
                next_sub = int(entry.number.rsplit(".", 1)[-1])
        for entry in chapter_entries:
            if entry.level < 2:
                continue
            parent = entry.number.rsplit(".", 1)[0]
            if entry.level == 3 and parent in skip_children:
                continue
            paragraphs = assigned.get(entry.number, [])
            if entry.node.dynamic and entry.number not in assigned:
                if entry.level == 2:
                    skip_children.add(entry.number)
                continue
            if entry.node.optional and not _has_text(paragraphs):
                skip_children.add(entry.number)
                continue
            title = titles.get(entry.number) or entry.title
            result.append(Section(entry.level, f"{entry.number} {title}", paragraphs))
        for extra in extras:
            next_sub += 1
            title = _clean_title(extra.title) or "Bagian tambahan"
            result.append(Section(2, f"{chapter.chapter}.{next_sub} {title}", extra.paragraphs))
    return result


def _chapter_for_title(key: str, entries: list[_Entry], chapters: list[_Entry]) -> int | None:
    if not key:
        return None
    for entry in entries:
        if entry.level >= 2 and not entry.node.dynamic and _key(entry.title) == key:
            return entry.chapter - 1
    return 0 if chapters else None
