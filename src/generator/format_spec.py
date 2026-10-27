"""Format baku laporan: varian A/B/C/D dan normalisasi struktur.

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
    Variant(
        code="D",
        name="Tinjauan pustaka",
        description=(
            "Sintesis beberapa sumber tanpa penelitian lapangan: tinjauan pustaka 3–5 "
            "subbab, pembahasan mengikuti rumusan masalah, tanpa bab hasil."
        ),
        nodes=(
            _n(1, "PENDAHULUAN"),
            _n(2, "Latar Belakang", "konteks, urgensi, kesenjangan; data hanya bila ada di sumber"),
            _n(2, "Rumusan Masalah", "daftar bernomor, tiap butir berupa pertanyaan"),
            _n(2, "Tujuan", "daftar bernomor, sejajar dengan rumusan masalah"),
            _n(1, "TINJAUAN PUSTAKA"),
            # 3–5 topik utuh tanpa sub-subbab: kualitas isi lebih penting daripada
            # banyaknya subbab. Node dinamis yang tidak terpakai otomatis dibuang.
            _n(2, "{Topik 1}", "satu topik kajian utuh, 2–3 paragraf", dynamic=True),
            _n(2, "{Topik 2}", "satu topik kajian utuh, 2–3 paragraf", dynamic=True),
            _n(2, "{Topik 3}", "satu topik kajian utuh, 2–3 paragraf", dynamic=True),
            _n(2, "{Topik 4}", "satu topik kajian utuh, 2–3 paragraf", dynamic=True),
            _n(2, "{Topik 5}", "satu topik kajian utuh, 2–3 paragraf", dynamic=True),
            _n(1, "PEMBAHASAN"),
            # Satu subbab per rumusan masalah, urutannya sama dengan 1.2 Rumusan
            # Masalah dan 1.3 Tujuan.
            _n(2, "{Jawaban rumusan masalah 1}", "menjawab rumusan masalah 1", dynamic=True),
            _n(2, "{Jawaban rumusan masalah 2}", "menjawab rumusan masalah 2", dynamic=True),
            _n(2, "{Jawaban rumusan masalah 3}", "menjawab rumusan masalah 3", dynamic=True),
            _n(2, "{Jawaban rumusan masalah 4}", "menjawab rumusan masalah 4", dynamic=True),
            _n(2, "{Jawaban rumusan masalah 5}", "menjawab rumusan masalah 5", dynamic=True),
            _n(1, "KESIMPULAN DAN SARAN"),
            _n(2, "Kesimpulan", "butir bernomor, sejajar dengan tujuan"),
            _n(2, "Saran", "butir bernomor, hapus bila kosong", optional=True),
        ),
    ),
)

# Aturan tambahan per varian; ditempel setelah _RULES oleh format_block().
_NO_TABLE_RULE = (
    "- Varian ini BUKAN laporan penelitian lapangan: JANGAN menulis penanda "
    "[TABEL: ...], [GAMBAR: ...], atau [FOTO: ...], dan jangan menulis kalimat yang "
    "menyebut adanya tabel/penanda tabel. Sajikan seluruh temuan sebagai paragraf "
    "narasi yang lengkap.\n"
)

_LAST_CHAPTER_RULE = (
    "- Bab terakhir KESIMPULAN DAN SARAN tidak boleh memuat paragraf pembuka, "
    "pengantar, atau penutup di luar subbab. Seluruh isi bab ini hanya butir bernomor "
    "di dalam subbab Kesimpulan (4.1) dan Saran (4.2).\n"
)

_VARIANT_EXTRA_RULES = {
    "B": _NO_TABLE_RULE + _LAST_CHAPTER_RULE,
    "D": _NO_TABLE_RULE + _LAST_CHAPTER_RULE + (
        "- Bab 2 TINJAUAN PUSTAKA: tulis 3 sampai 5 subbab saja (pilih 3, 4, atau 5 "
        "sesuai jumlah topik yang memang dibutuhkan). Setiap subbab adalah satu topik "
        "utuh dengan 2–3 paragraf, tanpa sub-subbab. Jangan mengulang topik yang sudah "
        "dibahas pada subbab lain.\n"
        "- Bab 3 PEMBAHASAN: jumlah subbab sama dengan jumlah butir Rumusan Masalah pada "
        "Bab 1 dan urutannya sama. Setiap subbab menjawab satu rumusan masalah sekaligus "
        "menunjukkan tercapainya satu Tujuan; judul subbab menggambarkan jawabannya, bukan "
        "menyalin pertanyaan. Alur pembahasan: Rumusan Masalah → Tujuan → Pembahasan → "
        "kesimpulan butir.\n"
        "- Jangan membuat bab Hasil; seluruh temuan dari sumber dibahas di Bab 3.\n"
    ),
}

_RULES = (
    "FORMAT WAJIB:\n"
    "- Gunakan persis struktur bab dan subbab varian di bawah; jangan menambah, "
    "menghapus, atau mengubah nomor serta judul tetap.\n"
    '- Judul bab: "BAB n. JUDUL KAPITAL". Subbab: n.n. Sub-subbab: n.n.n. Butir huruf: a., b.\n'
    "- Ganti judul bertanda {..} dengan judul nyata dari topik dan sumber; jangan biarkan "
    "tanda kurawal tertinggal. Judul pengganti WAJIB frasa nomina 3–7 kata yang berdiri "
    'sendiri (contoh: "Motif Penggunaan dan Prestasi Akademik"); DILARANG kalimat utuh, '
    "kata kerja, atau klausa yang menggantung.\n"
    "- Satu butir daftar = satu paragraf terpisah, diawali angka atau huruf.\n"
    "- Daftar bernomor hanya untuk rumusan masalah, tujuan, kesimpulan, saran, alat/bahan, "
    "dan langkah kerja.\n"
    "- Kesimpulan sejajar jumlah dan urutannya dengan tujuan. Tulis kesimpulan sebagai "
    "sintesis dengan kalimat sendiri, bukan salinan kalimat bab hasil.\n"
    "- Jangan mengulang kalimat atau fakta yang sudah ditulis pada bab lain; pendahuluan "
    "berisi konteks, bab kajian berisi temuan, pembahasan berisi analisis, penutup berisi sintesis.\n"
    "- Jangan menulis sitasi di dalam teks; sitasi ditambahkan aplikasi dari source_ids.\n"
    "- Jangan menyalin kalimat sumber kata per kata; susun ulang dengan kalimat sendiri.\n"
    "- Jangan membuat tabel, gambar, foto, atau diagram. Tulis penanda [TABEL: ...], "
    "[GAMBAR: ...], atau [FOTO: ...] pada paragraf sendiri.\n"
    '- Tabel yang berasal dari sumber diikuti baris "Sumber: (Penulis, Tahun)" — '
    "jangan memakai angka indeks seperti [0].\n"
    "- Jangan mengarang angka, tahun, nama, istilah teknis, atau rujukan. Bila tidak ada di "
    "sumber, kosongkan bagian itu.\n"
    "- Setiap klaim faktual harus bersumber dari sumber yang diberikan; tandai sumbernya "
    "lewat source_ids, bukan dengan menulis sitasi sendiri.\n"
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


def chapter_sub_outlines(variant: Variant) -> list[tuple[str, list[str]]]:
    """Kelompokkan outline per bab lengkap dengan subbabnya untuk penulisan AI yang mendalam."""
    entries = _entries(variant)
    chapters: list[tuple[str, list[str]]] = []
    current_chapter: str | None = None
    current_subs: list[str] = []
    for entry in entries:
        if entry.level == 1:
            if current_chapter is not None:
                chapters.append((current_chapter, current_subs))
            current_chapter = f"{entry.number} {entry.title}"
            current_subs = [current_chapter]
        else:
            # Judul dinamis ({Aspek 1}, {Pembahasan topik 1}) HARUS sampai ke AI
            # lengkap dengan kurung kurawalnya. Tanpa penanda itu, aturan "ganti
            # judul bertanda {..}" tidak pernah aktif dan model menyalin nama
            # template mentah ("3.2.1 Pembahasan topik 1") ke dokumen final.
            title = entry.title if entry.node.dynamic else _clean_title(entry.title)
            current_subs.append(f"{entry.number} {title}")
    if current_chapter is not None:
        chapters.append((current_chapter, current_subs))
    return chapters


def outline_titles(variant: Variant) -> list[str]:
    """Judul bab bernomor untuk mengisi editor outline."""
    return [f"{entry.number} {entry.title}" for entry in _entries(variant) if entry.level == 1]


def format_block(variant: Variant) -> str:
    """Aturan wajib + struktur varian untuk ditempel ke prompt sistem."""
    structure = "\n".join(skeleton_lines(variant))
    extra = _VARIANT_EXTRA_RULES.get(variant.code, "")
    block = f"{_RULES}\n\nSTRUKTUR WAJIB (varian {variant.code} — {variant.name}):\n{structure}"
    return f"{block}\n\n{extra}" if extra else block


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


_PLACEHOLDER_TITLE_RE = re.compile(
    r"^(?:pembahasan\s+)?(?:topik|aspek|kajian|subjek|objek|jawaban\s+rumusan\s+masalah)\s*\d*$",
    re.IGNORECASE,
)


_SENTENCE_TITLE_RE = re.compile(
    r"^(berbagai\s+(penelitian|studi)|banyak\s+(penelitian|studi)|bagaimana|mengapa|"
    r"hasil\s+penelitian|penelitian\s+ini|studi\s+ini|kajian\s+ini|"
    r"bersifat|merupakan|adalah|menunjukkan|memperlihatkan|mengindikasikan|"
    r"terbukti|ditemukan|diketahui|disimpulkan)\b",
    re.IGNORECASE,
)
_MAX_TITLE_WORDS = 10

# Penanda klausa: judul kiriman AI yang memuat kata ini bukan lagi frasa nomina
# murni, sehingga dipotong sebelum penanda pertama (gejala: "Media sosial telah
# menjadi bagian yang tidak" terpotong di konjungsi).
_CLAUSE_MARKERS = frozenset({
    "yang", "telah", "adalah", "dapat", "dalam", "karena", "sehingga", "agar",
    "dengan", "merupakan", "berfungsi", "menjadi",
    "memberikan", "memfasilitasi", "mendorong", "meningkatkan", "menyebabkan",
    "mempengaruhi", "memiliki", "seperti", "bahwa", "yakni", "yaitu",
})

# Kata fungsi (Fase 1c): kata sambung/preposisi/partikel pembuka kuantitas.
# Dipakai untuk (1) membuang kata menggantung di ujung judul, (2) mengenali
# frasa bermakna saat pemotongan klausa, dan (3) mengekstrak kata konten dari
# kalimat isi. Daftar ini juga dipakai guard S3 (Fase 2) — jaga tetap sinkron.
_FUNCTION_WORDS = frozenset({
    "yang", "di", "ke", "dari", "dan", "atau", "pada", "dengan", "untuk",
    "serta", "adalah", "telah", "tidak", "juga", "masih", "akan", "dapat",
    "harus", "karena", "sehingga", "agar", "ini", "itu",
    "dalam", "sebagai", "terhadap", "bagi", "oleh", "antara", "selama",
    "hingga", "sampai", "maupun", "tetapi", "namun", "bahwa", "berbagai",
    "banyak", "sebuah", "seorang", "para", "seperti", "yakni", "yaitu",
    "diperkenalkan", "diterapkan", "dilakukan", "ditemukan", "disajikan",
})

# Kata sambung/preposisi: tidak dikapital di tengah judul (kapital judul).
_TITLE_MINOR_WORDS = frozenset({
    "dan", "atau", "tetapi", "namun", "serta", "maupun", "yang", "di", "ke",
    "dari", "untuk", "pada", "dalam", "dengan", "sebagai", "terhadap", "bagi",
    "oleh", "karena", "agar", "antara", "selama", "hingga", "sampai", "bahwa",
})


def _is_content_word(word: str) -> bool:
    """Kata konten = kata pembawa makna, bukan kata fungsi (Fase 1b/1d)."""
    core = word.strip("()[]:;,.!?\"'-–—")
    return bool(core) and core.casefold() not in _FUNCTION_WORDS


def _strip_function_edges(words: list[str]) -> list[str]:
    """Buang kata fungsi yang menempel di awal dan akhir frasa kata."""
    start, end = 0, len(words)
    while start < end and not _is_content_word(words[start]):
        start += 1
    while end > start and not _is_content_word(words[end - 1]):
        end -= 1
    return words[start:end]


def _title_valid(text: str) -> bool:
    """Judul sah = minimal 3 kata dan memuat minimal satu kata konten (Fase 1d)."""
    words = str(text or "").split()
    return len(words) >= 3 and any(_is_content_word(word) for word in words)


def _clause_cut(text: str) -> str:
    """Potong judul di penanda klausa pertama agar sisa berupa frasa nomina.

    Potong SEBELUM penanda pertama bila sisa kiri >= 3 kata bermakna; bila sisa
    kiri kurang dari 3 kata, ambil frasa sesudah penanda yang diawali dan
    diakhiri kata konten — pilih yang terpanjang. Bila tidak ada satu pun frasa
    sah, pakai sisa terpanjang yang masih >= 2 kata supaya topik tidak hilang.
    """
    words = text.split()
    if not words:
        return text
    segments: list[list[str]] = []
    current: list[str] = []
    for word in words:
        if word.strip(".,;:").casefold() in _CLAUSE_MARKERS:
            segments.append(current)
            current = []
        else:
            current.append(word)
    segments.append(current)
    left = _strip_function_edges(segments[0])
    if _title_valid(" ".join(left)):
        return " ".join(left)
    # Frasa sesudah penanda: kandidat = segmen dengan tepi kata fungsi dibuang;
    # pilih terpanjang (sama panjang -> yang paling awal).
    candidates = [_strip_function_edges(segment) for segment in segments[1:]]
    valid = [
        (len(candidate), -position, candidate)
        for position, candidate in enumerate(candidates)
        if _title_valid(" ".join(candidate))
    ]
    if valid:
        valid.sort(reverse=True)
        return " ".join(valid[0][2])
    best = max([left] + candidates, key=len)
    return " ".join(best) if len(best) >= 2 else text


def _content_phrase(text: str, min_words: int = 3, max_words: int = 5) -> str:
    """Frasa kata konten terpanjang (3-5 kata berurutan) dari kalimat isi (Fase 1d-i)."""
    runs: list[list[str]] = []
    current: list[str] = []
    for word in str(text or "").split():
        if _is_content_word(word):
            current.append(word)
        else:
            runs.append(current)
            current = []
    runs.append(current)
    best = max(runs, key=len) if runs else []
    phrase = best[:max_words]
    return " ".join(phrase) if len(phrase) >= min_words else ""


def _dominant_words(text: str, count: int = 3) -> list[str]:
    """Kata konten dominan (urutan kemunculan pertama) untuk pembeda judul (Fase 1-3)."""
    return [word for word in str(text or "").split() if _is_content_word(word)][:count]


def _title_case(text: str) -> str:
    """Kapital judul: tiap kata diawali kapital kecuali kata sambung/preposisi.

    Akronim seluruhnya kapital (mis. LED) dan kata berkapital internal (nama
    diri) dipertahankan; judul yang seluruhnya kapital dianggap echo judul BAB
    dan tetap dinormalkan.
    """
    words = text.split()
    if len(words) <= 1:
        return text
    letters = [char for char in text if char.isalpha()]
    whole_caps = bool(letters) and all(char.isupper() for char in letters)
    cased: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]:;,.!?\"'-–—")
        if not core:
            cased.append(word)
        elif not whole_caps and len(core) >= 2 and core.isupper():
            cased.append(word)  # akronim di tengah judul dipertahankan
        elif index and core.casefold() in _TITLE_MINOR_WORDS:
            cased.append(word.lower())
        elif not whole_caps and any(char.isupper() for char in core[1:]):
            cased.append(word)  # nama diri berkapital internal dipertahankan
        else:
            lowered = word.lower()
            for position, char in enumerate(lowered):
                if char.isalpha():
                    cased.append(lowered[:position] + char.upper() + lowered[position + 1:])
                    break
            else:
                cased.append(word)
    return " ".join(cased)


def _sanitize_title(title: str, fallback: str = "") -> str:
    """Judul final: frasa nomina pendek, tanpa angka AI, tanpa kalimat.

    Nomor pada judul kiriman AI dibuang (aplikasi yang menghitung). Judul
    kalimat dipotong di penanda klausa pertama sebelum dibatasi maksimal 10
    kata, kata fungsi yang menggantung di ujung dibuang berulang sampai ujung
    bersih, lalu kapitalnya dinormalkan menjadi kapital judul. Hasil yang
    kosong/placeholder/kalimat diganti ``fallback``; bila ``fallback`` kosong,
    kembalikan usaha terbaik apa adanya — keputusan fallback bertingkat
    (frasa isi -> judul baku varian) diambil ``normalize_sections`` yang
    memegang isi section.
    """
    text = " ".join(str(title or "").replace("{", " ").replace("}", " ").split())
    text = _NUMBER_PREFIX.sub("", text).strip(" .:-")
    if not text or _PLACEHOLDER_TITLE_RE.match(text) or _SENTENCE_TITLE_RE.match(text):
        return fallback
    text = _clause_cut(text)
    words = text.split()
    while words and words[-1].strip(".,;:!?\"'-–—").casefold() in _FUNCTION_WORDS:
        words.pop()
    text = " ".join(words[:_MAX_TITLE_WORDS]).strip(" .,;:-—–")
    if not text or _PLACEHOLDER_TITLE_RE.match(text) or _SENTENCE_TITLE_RE.match(text):
        return fallback
    return _title_case(text)


def _display_title(title: str) -> str:
    """Judul siap cetak; kosong berarti judul masih nama template seperti "{Topik 1}".

    Judul kosong tidak dicetak sebagai heading: isinya digabungkan ke bagian
    sebelumnya supaya dokumen tidak memuat kurawal atau "Pembahasan topik 1".
    """
    text = _clean_title(str(title or "").replace("{", " ").replace("}", " "))
    if not text:
        return ""
    if _PLACEHOLDER_TITLE_RE.match(text):
        return ""
    return text


def _extend_section(section, paragraphs) -> None:
    """Tambahkan paragraf berisi teks ke bagian terakhir (tanpa judul baru)."""
    for paragraph in paragraphs:
        if _has_text([paragraph]):
            section.paragraphs.append(paragraph)


# Kalimat yang hanya MENELOKAN keberadaan tabel ("disajikan dalam bentuk penanda
# tabel") — bukan isi, melainkan deskripsi penanda; dibuang saat normalisasi.
_TABLE_DESCRIPTOR_RE = re.compile(
    r"(penanda\s*\[?\s*tabel|disajikan\s+dalam\s+(?:bentuk\s+)?tabel|"
    r"dalam\s+bentuk\s+penanda|ditandai\s+sebagai\s+\[?tabel)",
    re.IGNORECASE,
)


def _clean_paragraphs(paragraphs) -> list:
    """Buang kalimat deskriptor penanda tabel & pecah paragraf kepanjangan.

    Satu paragraf tidak boleh memuat lebih dari 5 kalimat (kecuali daftar
    bernomor yang tetap satu butir satu paragraf); kelebihan dipecah menjadi
    beberapa paragraf berurutan. Paragraf kosong hasilnya dilesapkan.
    """
    from .ai.content import Paragraph  # impor lokal: hindari siklus modul

    cleaned: list = []
    for paragraph in paragraphs or []:
        sentences = [
            sentence
            for sentence in paragraph.sentences
            if sentence.text.strip() and not _TABLE_DESCRIPTOR_RE.search(sentence.text)
        ]
        if not sentences:
            continue
        if all(_NUMBERED_PREFIX_RE.match(sentence.text.strip()) for sentence in sentences):
            # Butir bernomor: satu butir satu paragraf (jangan digabung).
            cleaned.extend(Paragraph([sentence]) for sentence in sentences)
            continue
        if len(sentences) <= 5:
            cleaned.append(Paragraph(sentences))
            continue
        for start in range(0, len(sentences), 5):
            cleaned.append(Paragraph(sentences[start : start + 5]))
    return cleaned


# Butir daftar bernomor/huruf: tidak boleh digabung oleh heuristik paragraf.
_NUMBERED_PREFIX_RE = re.compile(r"^\s*(?:\d{1,2}|[a-z])[\.\)]\s+\S")
# Batas kata wajib: judul seperti "...Sarana Pembelajaran..." bukan subbab
# daftar bernomor (substring "saran" di dalam "Sarana" tidak boleh kena).
_LIST_TITLE_RE = re.compile(
    r"\b(rumusan masalah|tujuan|kesimpulan|saran)\b", re.IGNORECASE
)
_SARAN_HINT_RE = re.compile(
    r"(disarankan|saran|rekomendasi|sebaiknya|perlu\s+dilakukan|hendaknya)",
    re.IGNORECASE,
)


def _cap_paragraphs(paragraphs, max_paragraphs: int = 6) -> list:
    """Batasi jumlah paragraf per subbab agar isi berlebih tidak menumpuk.

    Kalimat butir bernomor tidak pernah digabung (satu butir satu paragraf).
    Kelebihan paragraf diratakan ulang menjadi maksimal ``max_paragraphs``
    paragraf agar isi tetap utuh tanpa subbab kepanjangan.
    """
    if len(paragraphs) <= max_paragraphs:
        return paragraphs
    sentences = [sentence for paragraph in paragraphs for sentence in paragraph.sentences]
    if not sentences:
        return []
    if all(_NUMBERED_PREFIX_RE.match(sentence.text.strip()) for sentence in sentences):
        return paragraphs
    from .ai.content import Paragraph  # impor lokal: hindari siklus modul

    size = -(-len(sentences) // max_paragraphs)  # ceil
    return [
        Paragraph(sentences[start : start + size])
        for start in range(0, len(sentences), size)
    ]


def _numbered_token(text: str) -> str:
    """Token nomor butir ("1.", "a.") atau string kosong bila bukan butir."""
    match = _NUMBERED_PREFIX_RE.match(str(text or "").strip())
    return match.group(0).strip() if match else ""


def _fallback_distribute_chapter_body(
    chapter_section, chapter_entries, assigned, titles
) -> None:
    """Sebar paragraf yang menempel di level BAB ke subbab yang belum terisi.

    Butir bernomor hanya diberikan ke subbab daftar bernomor; prosa hanya ke
    subbab naratif, agar isi tidak tertukar antar-jenis subbab. Judul dinamis
    diturunkan dari kalimat pertama bagian tersebut.
    """
    from .ai.content import Paragraph  # impor lokal: hindari siklus modul

    body = [p for p in chapter_section.paragraphs if _has_text([p])]
    if not body:
        return
    numbered = [
        p for p in body
        if p.sentences
        and all(_NUMBERED_PREFIX_RE.match(s.text.strip()) for s in p.sentences)
    ]
    prose = [p for p in body if p not in numbered]
    # Dedup ringan sebelum disebar: butir dengan nomor sama dan prosa yang
    # saling memparafrase tidak boleh mengisi dua subbab berbeda.
    seen_numbers: set[str] = set()
    unique_numbered = []
    for paragraph in numbered:
        token = _numbered_token(paragraph.sentences[0].text)
        if token and token in seen_numbers:
            continue
        seen_numbers.add(token)
        unique_numbered.append(paragraph)
    numbered = unique_numbered
    prose = [p for p in body if p not in numbered]
    targets = [
        entry
        for entry in chapter_entries
        if entry.level >= 2 and not _has_text(assigned.get(entry.number, []))
    ]
    list_targets = [entry for entry in targets if _LIST_TITLE_RE.search(entry.title)]
    prose_targets = [entry for entry in targets if not _LIST_TITLE_RE.search(entry.title)]

    def _assign(pool: list, nodes: list) -> list:
        if not pool or not nodes:
            return list(pool)
        size = max(1, -(-len(pool) // len(nodes)))
        for index, entry in enumerate(nodes):
            chunk = pool[index * size : (index + 1) * size]
            if not chunk:
                break
            assigned.setdefault(entry.number, []).extend(chunk)
            if entry.node.dynamic:
                first_text = next(
                    (
                        sentence.text
                        for paragraph in chunk
                        for sentence in paragraph.sentences
                        if sentence.text.strip()
                    ),
                    "",
                )
                derived = _sanitize_title(_content_phrase(first_text))
                if derived:
                    titles[entry.number] = derived
        return pool[size * len(nodes) :]

    leftover = _assign(numbered, list_targets)
    leftover += _assign(prose, prose_targets)
    if leftover:
        # Semua subbab sudah terisi: sisa isi ditempelkan ke subbab sejenis
        # (butir ke daftar, prosa ke naratif) agar tidak tersisa di level BAB.
        holders_list = [
            entry for entry in chapter_entries
            if entry.level == 2 and _LIST_TITLE_RE.search(entry.title)
            and _has_text(assigned.get(entry.number, []))
        ]
        holders_prose = [
            entry for entry in chapter_entries
            if entry.level == 2 and not _LIST_TITLE_RE.search(entry.title)
            and _has_text(assigned.get(entry.number, []))
        ]
        remaining: list = []
        for paragraph in leftover:
            is_numbered = bool(
                paragraph.sentences
                and all(_NUMBERED_PREFIX_RE.match(s.text.strip()) for s in paragraph.sentences)
            )
            holders = holders_list if is_numbered else holders_prose
            if holders:
                assigned.setdefault(holders[0].number, []).append(paragraph)
            else:
                remaining.append(paragraph)
        leftover = remaining
    chapter_section.paragraphs = list(leftover)


def _enforce_paragraph_shape(result) -> None:
    """Bentuk akhir paragraf: maksimal 5 kalimat; BAB 2/3 mencapai target paragraf.

    Paragraf dipotong/digabung deterministik berdasarkan jumlah kalimat, tanpa
    mengubah urutan atau isi kalimat. Subbab daftar bernomor tidak disentuh.
    """
    from .ai.content import Paragraph  # impor lokal: hindari siklus modul

    for section in result:
        if section.level < 2 or _LIST_TITLE_RE.search(section.title):
            continue
        sentences = [
            sentence for p in section.paragraphs for sentence in p.sentences if sentence.text.strip()
        ]
        if not sentences:
            continue
        chapter_number = str(section.title).split(".", 1)[0].strip()
        target = 3 if chapter_number == "3" else 2 if chapter_number == "2" else 0
        size = 5
        if target:
            # Paragraf dijaga minimal 3 kalimat bila isinya mencukupi.
            size = min(5, max(3, -(-len(sentences) // target)))
        if len(sentences) > 6 * size:
            size = -(-len(sentences) // 6)
        groups = [sentences[index : index + size] for index in range(0, len(sentences), size)]
        section.paragraphs = [Paragraph(group) for group in groups]


def _rebalance_chapter(chapter_section, canonical, extras, result) -> None:
    """Isi subbab wajib yang kosong dari konten longgar.

    Konten longgar = paragraf yang menempel di level BAB atau isi subbab tambahan
    (extras). Bila ada subbab kanonik yang kosong, paragraf dipindahkan ke sana
    dengan judul kanonik dipertahankan. Paragraf yang tidak terpakai tetap
    berada di sumbernya agar tidak ada isi yang hilang.
    """
    empties = [s for s in canonical if s.level >= 2 and not _has_text(s.paragraphs)]
    if not empties:
        return
    pool: list[tuple[object, object]] = [(None, p) for p in chapter_section.paragraphs if _has_text([p])]
    for section in extras:
        pool.extend((section, p) for p in section.paragraphs if _has_text([p]))
    if not pool:
        return
    chapter_section.paragraphs = []
    for target in empties:
        wants_numbered = bool(_LIST_TITLE_RE.search(target.title))
        taken: list = []
        seen_numbers: set[str] = set()
        for item in list(pool):
            _source, paragraph = item
            is_numbered = bool(
                paragraph.sentences
                and all(_NUMBERED_PREFIX_RE.match(s.text.strip()) for s in paragraph.sentences)
            )
            if is_numbered != wants_numbered:
                continue
            if wants_numbered:
                token = _numbered_token(paragraph.sentences[0].text)
                if token and token in seen_numbers:
                    continue
                seen_numbers.add(token)
            taken.append(item)
            pool.remove(item)
            if len(taken) >= 5:
                break
        if not taken:
            continue
        paragraphs = [paragraph for _source, paragraph in taken]
        target.paragraphs = (
            paragraphs if wants_numbered else _cap_paragraphs(paragraphs)
        )
    leftovers: dict[int, list] = {}
    for source, paragraph in pool:
        if source is None:
            chapter_section.paragraphs.append(paragraph)
        else:
            leftovers.setdefault(id(source), []).append(paragraph)
    for section in extras:
        rest = leftovers.get(id(section), [])
        section.paragraphs = rest
        if not rest and section in result:
            result.remove(section)
    # Prosa yang masih tersisa di level BAB dipindahkan ke subbab naratif level 2
    # agar heading BAB tidak diikuti paragraf liar.
    if chapter_section.paragraphs:
        holders = [
            section
            for section in canonical
            if section.level == 2 and not _LIST_TITLE_RE.search(section.title)
        ]
        if holders:
            for index, paragraph in enumerate(chapter_section.paragraphs):
                holders[index % len(holders)].paragraphs.append(paragraph)
            chapter_section.paragraphs = []


def _route_last_chapter_body(chapter_section, chapter_entries, assigned) -> None:
    """Varian B/D: BAB terakhir hanya boleh berisi butir di subbab Kesimpulan/Saran.

    Paragraf prosa yang menempel di level BAB dibuang; butir bernomor dipindahkan
    ke subbab yang sesuai (kata kunci saran -> Saran, selain itu -> Kesimpulan)
    supaya isi tidak hilang. Varian A/C (PENUTUP) tidak memakai pengaman ini.
    """
    from .ai.content import Paragraph  # impor lokal: hindari siklus modul

    body = list(chapter_section.paragraphs)
    if not body:
        return
    chapter_section.paragraphs = []
    level2 = [entry for entry in chapter_entries if entry.level == 2]
    kesimpulan = next(
        (entry.number for entry in level2 if "kesimpulan" in entry.title.casefold()), None
    )
    saran = next((entry.number for entry in level2 if "saran" in entry.title.casefold()), None)
    seen_tokens: dict[str, set[str]] = {}
    for paragraph in body:
        for sentence in paragraph.sentences:
            text = sentence.text.strip()
            if not _NUMBERED_PREFIX_RE.match(text):
                continue
            target = saran if (saran and _SARAN_HINT_RE.search(text)) else kesimpulan
            if target is None:
                continue
            token = _numbered_token(text)
            used = seen_tokens.setdefault(target, set())
            if token and token in used:
                # Nomor butir ganda dari dua jawaban berbeda: simpan yang pertama.
                continue
            used.add(token)
            assigned.setdefault(target, []).append(Paragraph([sentence]))


_RUMUSAN_PREFIX_RE = re.compile(
    r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?"
    r"(?:bagaimana(?:kah)?|apakah|apa(?:kah)?(?:\s+saja)?|sejauh\s+mana(?:kah)?|mengapa(?:kah)?|why|how)\s+",
    re.IGNORECASE,
)


def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        t_clean = str(section.title or "").casefold()
        if "rumusan masalah" not in t_clean or "jawaban" in t_clean:
            continue
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                for line in sentence.text.splitlines():
                    text = line.strip()
                    if not text:
                        continue
                    match = re.match(r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?(.*)$", text)
                    body = match.group(1).strip() if match else text
                    if body:
                        items.append(body)
    return items


def _heading_from_rumusan(text: str, limit: int = 90) -> str:
    """Ubah butir pertanyaan menjadi judul subbab singkat."""
    heading = _RUMUSAN_PREFIX_RE.sub("", str(text or "").strip()).rstrip(" ?.!").strip()
    if not heading:
        heading = str(text or "").strip().rstrip(" ?.!")
    heading = " ".join(heading.split())
    if len(heading) > limit:
        heading = heading[:limit].rsplit(" ", 1)[0] + " …"
    return _title_case(heading) if heading else ""


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
    rumusan_items = _rumusan_items(sections)
    chapter_body: dict[int, list] = {index: [] for index in range(len(chapters))}
    heading_used: set[int] = set()
    blocks: dict[int, list] = {index: [] for index in range(len(chapters))}
    current: int | None = None
    for section in sections:
        raw_title = str(section.title or "").strip()
        title = _clean_title(section.title)
        chap_match = re.match(r"^\s*bab\s*([0-9ivxlc]+)", raw_title, re.IGNORECASE)
        sub_match = re.match(r"^\s*(\d+)\.", raw_title)
        is_chapter_heading = section.level <= 1 or bool(chap_match) or raw_title.casefold().startswith("bab ")
        if is_chapter_heading:
            index = None
            if chap_match:
                chap_str = chap_match.group(1)
                try:
                    c_num = int(chap_str)
                    if 1 <= c_num <= len(chapters):
                        index = c_num - 1
                except ValueError:
                    pass
            if index is None:
                index = _match_chapter(_key(title), chapters, heading_used)
            if index is None:
                index = next(
                    (candidate for candidate in range(len(chapters)) if candidate not in heading_used),
                    len(chapters) - 1,
                )
            heading_used.add(index)
            current = index
            chapter_body[index].extend(_clean_paragraphs(section.paragraphs))
            continue
        target_chap = None
        if sub_match:
            try:
                c_num = int(sub_match.group(1))
                if 1 <= c_num <= len(chapters):
                    target_chap = c_num - 1
            except ValueError:
                pass
        if target_chap is None:
            target_chap = current
        if target_chap is None:
            target_chap = _chapter_for_title(_key(title), entries, chapters)
        if target_chap is not None:
            block_title = _sanitize_title(section.title)
            if not block_title:
                # Judul kalimat panjang: pakai judul baku varian bila terkandung
                # di dalamnya, agar pencocokan subbab tetap bekerja.
                raw_clean = _clean_title(section.title)
                block_title = next(
                    (
                        entry.title
                        for entry in entries
                        if entry.level >= 2
                        and not entry.node.dynamic
                        and _key(entry.title) in _key(raw_clean)
                    ),
                    raw_clean,
                )
            blocks[target_chap].append(
                Section(section.level, block_title, _clean_paragraphs(section.paragraphs))
            )
            current = target_chap

    result: list = []
    # Kunci judul per (bab, level): subbab dinamis tidak boleh kembar dengan
    # saudara selevelnya (Fase 1-3) — pembeda diambil dari isi section.
    sibling_keys: dict[tuple[int, int], set[str]] = {}
    for index, chapter in enumerate(chapters):
        chapter_section = Section(1, f"{chapter.number} {chapter.title}", chapter_body.get(index, []))
        result.append(chapter_section)
        last_section = chapter_section
        level2_count = 0
        level3_counts: dict[str, int] = {}
        current_parent = ""
        chapter_entries = [entry for entry in entries if entry.chapter == chapter.chapter]
        assignment, extras = _assign_blocks(chapter_entries, blocks.get(index, []))
        assigned = assignment["paragraphs"]
        titles = assignment["titles"]
        # Varian B/D: bab terakhir hanya berisi butir di 4.1/4.2 — paragraf prosa
        # di level BAB dibuang, butir bernomor dipindahkan ke subbab tujuannya.
        if variant.code in ("B", "D") and index == len(chapters) - 1:
            _route_last_chapter_body(chapter_section, chapter_entries, assigned)
        elif variant.code in ("B", "D"):
            # Isi yang menempel di level BAB disebar ke subbab agar struktur
            # dokumen tidak kehilangan subbab.
            _fallback_distribute_chapter_body(
                chapter_section, chapter_entries, assigned, titles
            )
        skip_children: set[str] = set()
        canonical_sections: list = []
        extra_sections: list = []
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
            fallback_title = "" if entry.node.dynamic else _sanitize_title(entry.title)
            title = _sanitize_title(titles.get(entry.number) or entry.title, fallback_title)
            if entry.node.dynamic:
                # Fase 1d: fallback bertingkat bila judul belum sah (< 3 kata /
                # tanpa kata konten), lalu Fase 1-3: pembeda bila kembar dengan
                # saudara selevel atau induknya dalam bab yang sama.
                from .ai.content import _generic_title  # impor lokal: hindari siklus

                first_text = next(
                    (
                        sentence.text
                        for paragraph in paragraphs
                        for sentence in paragraph.sentences
                        if sentence.text.strip()
                    ),
                    "",
                )
                sibling = sibling_keys.setdefault((chapter.chapter, entry.level), set())
                parent_key = (
                    _key(_clean_title(last_section.title))
                    if entry.level == 3 and last_section is not chapter_section
                    else _key(chapter.title)
                )

                def _clashes(value: str) -> bool:
                    return not value or _key(value) in sibling or _key(value) == parent_key

                if not _title_valid(title):
                    # Khusus bab Pembahasan: prioritaskan derivasi judul dari Rumusan Masalah Bab 1
                    if ("PEMBAHASAN" in chapter.title.upper() or "PEMBAHASAN" in (current_parent or parent)) and rumusan_items:
                        r_idx = (level3_counts.get(current_parent, 0) if entry.level == 3 else level2_count)
                        if r_idx < len(rumusan_items):
                            derived = _heading_from_rumusan(rumusan_items[r_idx])
                            if derived and not _clashes(derived):
                                title = derived
                    if not _title_valid(title):
                        # (i) frasa kata konten dari kalimat pertama isi section.
                        phrase = _sanitize_title(_content_phrase(first_text))
                        if _title_valid(phrase) and not _clashes(phrase):
                            title = phrase
                if not _title_valid(title):
                    # (ii) judul baku node varian — tidak pernah kosong.
                    title = _generic_title(entry.title)
                if _clashes(title):
                    # Pembeda: sufiks 2-3 kata konten dominan isi section kedua.
                    suffix_words = _dominant_words(first_text)
                    room = _MAX_TITLE_WORDS - len(title.split())
                    if len(suffix_words) >= 2 and room >= 2:
                        suffix = _title_case(" ".join(suffix_words[: min(3, room)]))
                        candidate = f"{title} — {suffix}"
                        if not _clashes(candidate):
                            title = candidate
                if _clashes(title):
                    # Upaya terakhir: bedakan dengan judul induk di depan.
                    parent_title = (
                        _clean_title(last_section.title)
                        if entry.level == 3 and last_section is not chapter_section
                        else chapter.title
                    )
                    title = f"{parent_title}: {title}"
            # Cerdas: Jika subbab pertama (misal 1.1 Latar Belakang) kosong tapi bab induk punya teks,
            # sematkan teks bab induk agar subbab tidak kosong di berkas dokumen.
            # Khusus bab terakhir varian B/D, prosa level bab sudah dibuang item 3
            # (BAB 4 hanya butir), jadi jangan disematkan kembali.
            last_chapter_cleanup = variant.code in ("B", "D") and index == len(chapters) - 1
            if (
                not _has_text(paragraphs)
                and entry.number == f"{chapter.chapter}.1"
                and _has_text(chapter_body.get(index, []))
                and not last_chapter_cleanup
            ):
                paragraphs = list(chapter_body.get(index, []))
            # Cerdas: Untuk subbab Pembahasan yang judulnya masih nama template atau generik,
            # turunkan judul dari Rumusan Masalah yang sejajar (Varian D maupun Varian B).
            is_pembahasan_sub = (
                ("PEMBAHASAN" in chapter.title.upper() or "PEMBAHASAN" in (current_parent or parent))
                and (not title or _PLACEHOLDER_TITLE_RE.match(title) or title.strip().lower() == "pembahasan")
            )
            if is_pembahasan_sub and rumusan_items:
                r_idx = (level3_counts.get(current_parent, 0) if entry.level == 3 else level2_count)
                if r_idx < len(rumusan_items):
                    derived = _heading_from_rumusan(rumusan_items[r_idx])
                    if derived:
                        title = derived
            if not title:
                if (
                    variant.code == "D"
                    and chapter.title == "PEMBAHASAN"
                    and level2_count < len(rumusan_items)
                ):
                    title = _heading_from_rumusan(rumusan_items[level2_count])
                if not title:
                    _extend_section(last_section, paragraphs)
                    continue
            # Nomor subbab dinamis dihitung ulang agar tetap berurutan walau ada
            # bagian yang digabung/dibuang; nomor judul tetap mengikuti varian.
            if entry.level == 2:
                if entry.node.dynamic:
                    display_no = f"{chapter.chapter}.{level2_count + 1}"
                else:
                    display_no = entry.number
                    level2_count = max(
                        level2_count, int(f"{entry.number.rsplit('.', 1)[-1]}")
                    )
                level2_count = max(level2_count, int(display_no.rsplit(".", 1)[-1]))
                current_parent = display_no
                level3_counts.setdefault(current_parent, 0)
            else:
                if entry.node.dynamic:
                    parent_no = current_parent or parent
                    level3_counts[parent_no] = level3_counts.get(parent_no, 0) + 1
                    display_no = f"{parent_no}.{level3_counts[parent_no]}"
                else:
                    display_no = entry.number
                    parent_no = display_no.rsplit(".", 1)[0]
                    level3_counts[parent_no] = max(
                        level3_counts.get(parent_no, 0),
                        int(display_no.rsplit(".", 1)[-1]),
                    )
            if not _LIST_TITLE_RE.search(str(entry.title)):
                paragraphs = _cap_paragraphs(paragraphs)
            sibling_keys.setdefault((chapter.chapter, entry.level), set()).add(_key(title))
            last_section = Section(entry.level, f"{display_no} {title}", paragraphs)
            result.append(last_section)
            canonical_sections.append(last_section)
        # Varian D dibatasi 3–5 subbab per bab kajian: kelebihan topik digabung
        # ke subbab terakhir, bukan menjadi heading baru yang menggelembung.
        max_level2 = (
            5 if variant.code == "D" and chapter.title in ("TINJAUAN PUSTAKA", "PEMBAHASAN")
            else None
        )
        for extra in extras:
            paragraphs = _cap_paragraphs(extra.paragraphs)
            title = _display_title(extra.title)
            if not title or (max_level2 is not None and level2_count >= max_level2):
                _extend_section(last_section, paragraphs)
                continue
            level2_count += 1
            sibling_keys.setdefault((chapter.chapter, 2), set()).add(_key(title))
            last_section = Section(2, f"{chapter.chapter}.{level2_count} {title}", paragraphs)
            result.append(last_section)
            extra_sections.append(last_section)
        # Subbab kanonik yang kosong diisi dari isi level bab / subbab tambahan,
        # agar struktur wajib (mis. 1.1 Latar Belakang) tidak pernah kosong.
        _rebalance_chapter(chapter_section, canonical_sections, extra_sections, result)
    # Batas 6 paragraf juga berlaku untuk isi yang digabung dari bagian tambahan
    # (extras) atau disematkan dari level bab — bukan hanya paragraf awal.
    _NON_FACTUAL_LIST_RE = re.compile(r"\b(rumusan masalah|tujuan|saran)\b", re.IGNORECASE)
    _CITATION_STRIP_RE = re.compile(
        r"\s*\(\s*[^()]{0,160}?\b(?:19|20)\d{2}[a-z]?\b[^()]{0,80}?\s*\)(?=[.?]?)",
        re.IGNORECASE,
    )
    for section in result:
        if (
            section.level >= 2
            and section.paragraphs
            and not _LIST_TITLE_RE.search(section.title)
        ):
            section.paragraphs = _cap_paragraphs(section.paragraphs)
            merged_paras = []
            for p in section.paragraphs:
                if (
                    merged_paras
                    and len(p.sentences) == 1
                    and not any(_NUMBERED_PREFIX_RE.match(s.text.strip()) for s in p.sentences)
                    and not any(_NUMBERED_PREFIX_RE.match(s.text.strip()) for s in merged_paras[-1].sentences)
                    and len(merged_paras[-1].sentences) + 1 <= 5
                ):
                    merged_paras[-1].sentences.extend(p.sentences)
                else:
                    merged_paras.append(p)
            section.paragraphs = merged_paras
        if _NON_FACTUAL_LIST_RE.search(section.title):
            for paragraph in section.paragraphs:
                for sentence in paragraph.sentences:
                    sentence.text = _CITATION_STRIP_RE.sub("", sentence.text)
                    sentence.citation = ""
                    sentence.source_ids = []
                    sentence.is_factual = False
    _enforce_paragraph_shape(result)
    return result


def _chapter_for_title(key: str, entries: list[_Entry], chapters: list[_Entry]) -> int | None:
    if not key:
        return None
    for entry in entries:
        if entry.level >= 2 and not entry.node.dynamic and _key(entry.title) == key:
            return entry.chapter - 1
    return 0 if chapters else None


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
