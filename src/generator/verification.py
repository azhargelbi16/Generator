"""Verifikasi deterministik cuplikan per kalimat (11.2, 11.3, 19).

Status hanya menandai bahwa cuplikan benar-benar ada di sumber yang dirujuk,
bukan bahwa klaimnya benar. Gerbang ekspor ada di Task 17c.

Ambang pencocokan: **kecocokan = substring eksak setelah normalisasi** — tidak
ada fuzzy matching. Normalisasi menyamakan huruf besar/kecil, merapikan spasi,
menyambung kata yang terpotong tanda hubung di akhir baris, menyeragamkan
dash/kutip tipografis, dan membuang soft hyphen.
Toleransi teks (T1.2): membandingkan juga setelah membuang karakter non-alfanumerik
agar typo tanda baca dan pemisah ribuan tidak menggagalkan verifikasi.

Penjaga salinan (patchwriting): kalimat panjang (>= 12 kata) yang sebagian besar
potongannya muncul harfiah di jendela sumber berstatus `perlu_ditinjau`, bukan
`terverifikasi`, supaya salinan kata-per-kata tidak lolos sebagai kutipan sah.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ai.content import Section, Sentence

STATUS_VERIFIED = "terverifikasi"
STATUS_NEEDS_REVIEW = "perlu_ditinjau"
STATUS_UNVERIFIED = "tidak_terverifikasi"
STATUS_NON_FACTUAL = "bukan_klaim_faktual"
MIN_WORDS = 5

REASON_NEEDS_REVIEW = "Kutipan ada, kalimatnya tidak sepenuhnya didukung sumber."
REASON_VERBATIM = "Kalimat menyalin teks sumber hampir kata per kata; parafrase dulu."
REASON_TRANSLATED = (
    "Kutipan ditemukan persis di sumber berbahasa asing; kalimat adalah "
    "terjemahan bebas — periksa artinya, bukan kata-katanya."
)

# Penanda fungsi bahasa untuk deteksi lintas bahasa yang murah dan deterministik.
_ID_MARKERS = frozenset({
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah",
    "ini", "itu", "tidak", "sehingga", "tersebut", "oleh", "atau", "juga",
    "bagaimana", "apakah", "apa", "mengapa", "terhadap", "dalam", "sebagai",
    "dapat", "akan", "telah", "sudah", "masih", "lebih", "sangat", "antara",
    "bagi", "para", "setiap", "melalui", "merupakan", "terdapat", "yaitu",
    "seperti", "namun", "tetapi", "karena", "agar", "bila", "jika", "saat",
    "ketika", "setelah", "sebelum", "selama", "tanpa", "secara", "serta",
    "maka", "hal", "kini", "sebagai", "berbagai", "hingga",
})
_EN_MARKERS = frozenset({
    "the", "of", "and", "to", "in", "a", "is", "that", "for", "with", "as",
    "on", "by", "an", "be", "this", "are", "was", "were", "or", "their", "its",
    "these", "which", "such", "from", "at", "it",
})


def _marker_ratio(text: str, markers: frozenset) -> float:
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0.0
    return sum(1 for word in words if word in markers) / len(words)


def _cross_language(sentence_text: str, window: str) -> bool:
    """True bila kalimat berbahasa Indonesia sementara jendela sumber Inggris.

    Dipakai verifikasi kutipan terjemahan: skor dukungan kata pasti rendah
    (kosakata beda bahasa) meski kutipannya ditemukan persis. Ambang rasio
    fungsi kata dipilih konservatif agar halusinasi sebahasa TIDAK dianggap
    terjemahan: kalimat butuh penanda Indonesia dan jendela butuh penanda Inggris.
    """
    return _marker_ratio(sentence_text, _ID_MARKERS) >= 0.12 and _marker_ratio(
        window, _EN_MARKERS
    ) >= 0.10

# Deteksi salinan verbatim: kalimat panjang dibandingkan potongan katanya
# dengan jendela sumber yang sudah ditemukan saat verifikasi kutipan (tanpa
# membaca ulang sumber), sehingga biayanya tetap kecil per kalimat.
_VERBATIM_SHINGLE = 8
_VERBATIM_MIN_WORDS = 12
_VERBATIM_LIMIT = 0.8
_VERBATIM_SAMPLES = 5
_PUNCT_SPACES = str.maketrans({char: " " for char in ".,;:!?()[]{}\"'“”‘’—–-/"})

STOPWORDS_ID = frozenset({
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "ini", "itu", "tidak"
})

_TYPOGRAPHY = str.maketrans(
    {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00ad": "",  # soft hyphen
    }
)


def normalize(text: str) -> str:
    """Normalisasi sebelum pencocokan substring eksak (11.2)."""
    text = text.replace("-\r\n", "").replace("-\n", "")
    text = text.translate(_TYPOGRAPHY)
    return " ".join(text.lower().split())


def compute_claim_support_score(sentence_text: str, window_text: str) -> float:
    """Hitung rasio kata kalimat (tanpa kata fungsi Indonesia) yang muncul di jendela teks sumber."""
    norm_sent = normalize(sentence_text)
    words = [w for w in re.findall(r"\w+", norm_sent) if w not in STOPWORDS_ID]
    if not words:
        words = re.findall(r"\w+", norm_sent)
    if not words:
        return 0.0

    window_words = set(re.findall(r"\w+", window_text))
    matched = sum(1 for w in words if w in window_words)
    return matched / len(words)


@dataclass
class SentenceStatus:
    index: int
    sentence: Sentence
    status: str
    reason: str = ""


def _get_source_text(source_texts: dict[int, str] | list[str], source_id: int) -> str:
    if isinstance(source_texts, dict):
        return source_texts.get(source_id, "")
    if isinstance(source_texts, (list, tuple)) and 0 <= source_id < len(source_texts):
        return source_texts[source_id] or ""
    return ""


def normalize_sources(source_texts: dict[int, str] | list[str]) -> dict[int, str]:
    """Pra-normalisasi seluruh teks sumber ke dictionary agar pencocokan kutipan efisien."""
    if isinstance(source_texts, dict):
        return {k: normalize(v) for k, v in source_texts.items()}
    if isinstance(source_texts, (list, tuple)):
        return {i: normalize(t) for i, t in enumerate(source_texts)}
    return {}


def _plain_words(text: str) -> list[str]:
    """Kata tanpa tanda baca; translate + split berjalan di C, bukan regex."""
    return text.translate(_PUNCT_SPACES).split()


def verbatim_ratio(sentence_text: str, windows: list[str]) -> float:
    """Perkiraan fraksi kalimat yang muncul harfiah di jendela sumber.

    Hanya dihitung untuk kalimat panjang (>= `_VERBATIM_MIN_WORDS` kata) karena
    salinan verbatim yang layak ditandai adalah salinan panjang. Beberapa potongan
    `_VERBATIM_SHINGLE` kata diambil merata, lalu dicari sebagai substring pada
    jendela yang tanda bacanya sudah dibuang. Pencarian substring berjalan di C
    (str.find), jauh lebih murah daripada membangun himpunan shingle seluruh jendela.
    """
    words = _plain_words(normalize(sentence_text))
    if len(words) < _VERBATIM_MIN_WORDS:
        return 0.0
    last = len(words) - _VERBATIM_SHINGLE
    if last < 0:
        return 0.0
    if last == 0:
        starts = [0]
    elif last < _VERBATIM_SAMPLES:
        starts = list(range(last + 1))
    else:
        step = last / (_VERBATIM_SAMPLES - 1)
        starts = [round(index * step) for index in range(_VERBATIM_SAMPLES)]
    spans = [" ".join(words[start : start + _VERBATIM_SHINGLE]) for start in starts]
    if not spans:
        return 0.0
    best = 0.0
    for window in windows:
        plain = " ".join(_plain_words(window))
        if not plain:
            continue
        hits = sum(1 for span in spans if span in plain)
        best = max(best, hits / len(spans))
        if best >= _VERBATIM_LIMIT:
            break
    return best


_ELLIPSIS_RE = re.compile(r"(?:\.\.\.|…)")


def _fragment_windows(src_norm: str, fragment: str, cache: dict) -> list[str]:
    """Jendela sumber tempat `fragment` ditemukan (eksak, lalu toleransi alfanumerik)."""
    windows: list[str] = []
    start = 0
    while len(windows) < 20:
        pos = src_norm.find(fragment, start)
        if pos == -1:
            break
        windows.append(
            src_norm[max(0, pos - 400) : min(len(src_norm), pos + len(fragment) + 400)]
        )
        start = pos + 1
    if windows:
        return windows
    fragment_alnum = "".join(char for char in fragment if char.isalnum())
    if not fragment_alnum:
        return []
    if "alnum" not in cache:
        chars: list[str] = []
        indices: list[int] = []
        for index, char in enumerate(src_norm):
            if char.isalnum():
                chars.append(char)
                indices.append(index)
        cache["alnum"] = ("".join(chars), indices)
    src_alnum, indices = cache["alnum"]
    start_alnum = 0
    while len(windows) < 20:
        pos = src_alnum.find(fragment_alnum, start_alnum)
        if pos == -1:
            break
        norm_start = indices[pos]
        norm_end = indices[pos + len(fragment_alnum) - 1] + 1
        windows.append(
            src_norm[max(0, norm_start - 400) : min(len(src_norm), norm_end + 400)]
        )
        start_alnum = pos + 1
    return windows


def _evaluate(
    sentence: Sentence,
    source_texts: dict[int, str] | list[str],
    min_words: int,
    normalized_sources: dict[int, str] | None,
) -> tuple[str, str]:
    """Status + alasan untuk satu kalimat (satu lintasan pencocokan)."""
    if not sentence.is_factual:
        return STATUS_NON_FACTUAL, ""
    if sentence.origin != "ai":
        return STATUS_UNVERIFIED, ""
    quote = normalize(sentence.quote)
    if not quote or len(quote.split()) < min_words or not sentence.source_ids:
        return STATUS_UNVERIFIED, ""

    # Quote boleh memuat elipsis ("...") dari model; tiap bagian harus ditemukan.
    fragments = [part.strip() for part in _ELLIPSIS_RE.split(quote) if part.strip()]
    if not fragments:
        fragments = [quote]
    found_windows: list[str] = []
    for source_id in sentence.source_ids:
        if normalized_sources is not None and source_id in normalized_sources:
            src_norm = normalized_sources[source_id]
        else:
            src_norm = normalize(_get_source_text(source_texts, source_id))
        cache: dict = {}
        source_windows: list[str] = []
        complete = True
        for fragment in fragments:
            windows = _fragment_windows(src_norm, fragment, cache)
            if not windows:
                complete = False
                break
            source_windows.extend(windows)
        if complete:
            found_windows = source_windows
            break

    if not found_windows:
        return STATUS_UNVERIFIED, ""
    if len(fragments) > 1:
        # Elipsis: gabungkan jendela tiap bagian agar dukungan dihitung atas
        # keseluruhan bukti, bukan satu potongan saja.
        found_windows = [" ".join(found_windows)]

    scores = [compute_claim_support_score(sentence.text, w) for w in found_windows]
    best_score = max(scores)
    best_window = found_windows[scores.index(best_score)]
    if best_score < 0.6:
        # Kutipan panjang yang persis ditemukan + kosakata nyaris tak tumpang
        # tindih + bahasa kalimat vs sumber berbeda = terjemahan jujur dari
        # sumber asing; bukan halusinasi. Tetap terverifikasi dengan alasan khusus.
        if (
            len(quote.split()) >= 8
            and best_score < 0.25
            and _cross_language(sentence.text, best_window)
        ):
            return STATUS_VERIFIED, REASON_TRANSLATED
        return STATUS_NEEDS_REVIEW, REASON_NEEDS_REVIEW
    if verbatim_ratio(sentence.text, found_windows) >= _VERBATIM_LIMIT:
        return STATUS_NEEDS_REVIEW, REASON_VERBATIM
    return STATUS_VERIFIED, ""


def verify_sentence(
    sentence: Sentence,
    source_texts: dict[int, str] | list[str],
    min_words: int = MIN_WORDS,
    normalized_sources: dict[int, str] | None = None,
) -> str:
    """Cek cuplikan kalimat terhadap teks sumber yang dirujuknya, tanpa AI."""
    return _evaluate(sentence, source_texts, min_words, normalized_sources)[0]


def verify_sections(sections: list[Section], source_texts: dict[int, str] | list[str]) -> list[SentenceStatus]:
    """Status untuk setiap kalimat, daftar datar dengan `index` global berurutan."""
    cached = normalize_sources(source_texts)
    statuses: list[SentenceStatus] = []
    for section in sections:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                st, reason = _evaluate(sentence, source_texts, MIN_WORDS, cached)
                statuses.append(
                    SentenceStatus(
                        index=len(statuses),
                        sentence=sentence,
                        status=st,
                        reason=reason,
                    )
                )
    return statuses
