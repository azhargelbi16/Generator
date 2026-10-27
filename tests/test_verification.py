from generator.verification import (
    normalize,
    verify_sentence,
    verify_sections,
    compute_claim_support_score,
    STATUS_VERIFIED,
    STATUS_NEEDS_REVIEW,
    STATUS_UNVERIFIED,
    STATUS_NON_FACTUAL,
)
from generator.ai.content import Sentence, Paragraph, Section

GOOD = "pertanian organik di indonesia sangat penting bagi petani"


def test_normalize_collapses_and_casefolds():
    assert normalize("Halo   DUNIA\nini") == "halo dunia ini"


def test_normalize_joins_hyphen_breaks():
    assert "pertanian" in normalize("pertani-\nan organik")


def test_verify_uses_only_referenced_source():
    texts = {
        0: "laporan penelitian " + GOOD,
        1: "topik lain sama sekali berbeda dan tidak berkaitan lagi",
    }
    assert verify_sentence(Sentence(GOOD, GOOD, [0]), texts) == STATUS_VERIFIED
    assert verify_sentence(
        Sentence(GOOD, "topik lain sama sekali berbeda dan tidak berkaitan", [0]), texts
    ) == STATUS_UNVERIFIED


def test_short_quote_is_unverified():
    assert verify_sentence(Sentence("x", "kata pendek ada", [0]), {0: "kata pendek ada"}) == STATUS_UNVERIFIED


def test_factual_without_source_is_unverified():
    assert verify_sentence(Sentence("x", "", []), {0: GOOD}) == STATUS_UNVERIFIED


def test_manual_sentence_is_unverified():
    assert verify_sentence(Sentence(GOOD, GOOD, [0], origin="manual"), {0: GOOD}) == STATUS_UNVERIFIED


def test_unknown_source_id_is_unverified_not_crash():
    assert verify_sentence(Sentence(GOOD, GOOD, [99]), {0: GOOD}) == STATUS_UNVERIFIED


def test_non_factual_status():
    assert verify_sentence(Sentence("x", is_factual=False), {}) == STATUS_NON_FACTUAL


def test_verify_sections_indexes_every_sentence():
    sec = Section(
        1,
        "B",
        [Paragraph([Sentence(GOOD, GOOD, [0]), Sentence("b.", is_factual=False)])],
    )
    statuses = verify_sections([sec], {0: GOOD})
    assert [s.status for s in statuses] == [STATUS_VERIFIED, STATUS_NON_FACTUAL]
    assert [s.index for s in statuses] == [0, 1]


# --- Task 1.4: ambang pencocokan kutipan ------------------------------------


def test_aturan_sambung_kata_lama_tetap_berlaku():
    assert normalize("about-\none third") == "aboutone third"


def test_normalize_membuang_soft_hyphen():
    assert normalize("presi\u00adsi") == "presisi"


def test_kutip_dengan_varian_dash_lolos():
    texts = {0: "hasil sekitar–satu ton per hektare pada musim kemarau"}
    quote = "hasil sekitar-satu ton per hektare pada musim kemarau"
    assert verify_sentence(Sentence(quote, quote, [0]), texts) == STATUS_VERIFIED


def test_kutip_dengan_kutip_keriting_lolos():
    texts = {0: "petani memakai istilah 'presisi' dalam praktik harian mereka"}
    quote = "petani memakai istilah \u2018presisi\u2019 dalam praktik harian mereka"
    assert verify_sentence(Sentence(quote, quote, [0]), texts) == STATUS_VERIFIED


def test_normalize_sources_and_cached_verification():
    from generator.verification import normalize_sources
    source_texts = ["Teks sumber pertama tentang " + GOOD, "Sumber kedua"]
    cached = normalize_sources(source_texts)
    assert 0 in cached and 1 in cached
    sec = Section(1, "Bab 1", [Paragraph([Sentence(GOOD, GOOD, [0])])])
    statuses = verify_sections([sec], source_texts)
    assert statuses[0].status == STATUS_VERIFIED


# --- Task 1.1: Skor dukungan klaim ------------------------------------------


def test_kutipan_asli_dengan_kalimat_tidak_didukung_menghasilkan_perlu_ditinjau():
    texts = {0: "laporan penelitian " + GOOD}
    # Kutipan asli ada di sumber, tetapi kalimatnya halusinasi / tidak didukung
    sent = Sentence(
        text="Pemerintah melarang ekspor komoditas beras secara ketat di pasar internasional.",
        quote=GOOD,
        source_ids=[0],
    )
    assert verify_sentence(sent, texts) == STATUS_NEEDS_REVIEW


def test_skor_dukungan_klaim_ambang_batas():
    source_context = "laporan penelitian pertanian organik di indonesia sangat penting bagi petani lokal daerah"
    texts = {0: source_context}

    # Kalimat didukung sebagian besar kata (skor >= 0.6)
    sent_ok = Sentence(
        text="Pertanian organik di Indonesia sangat penting bagi petani lokal.",
        quote=GOOD,
        source_ids=[0],
    )
    assert verify_sentence(sent_ok, texts) == STATUS_VERIFIED

    # Kalimat dengan kutipan asli tetapi kata pendukung di bawah 0.6
    sent_review = Sentence(
        text="Pertanian organik di Indonesia menghasilkan surplus triliunan devisa pertambangan emas batubara.",
        quote=GOOD,
        source_ids=[0],
    )
    assert verify_sentence(sent_review, texts) == STATUS_NEEDS_REVIEW


def test_perlu_ditinjau_memiliki_alasan_di_verify_sections():
    texts = {0: "laporan penelitian " + GOOD}
    sent = Sentence(
        text="Pemerintah melarang ekspor komoditas beras secara ketat di pasar internasional.",
        quote=GOOD,
        source_ids=[0],
    )
    sec = Section(1, "Bab 1", [Paragraph([sent])])
    statuses = verify_sections([sec], texts)
    assert statuses[0].status == STATUS_NEEDS_REVIEW
    assert "Kutipan ada" in statuses[0].reason


# --- Task 1.2: Toleransi teks -----------------------------------------------


def test_kutipan_enam_kata_dengan_perbedaan_tanda_baca_lolos():
    texts = {0: "hasil panen padi mencapai 10.000 ton, menurut laporan resmi bps"}
    # Kutipan 6 kata dengan perbedaan tanda baca (tanpa pemisah ribuan dan tanpa koma)
    quote = "hasil panen padi mencapai 10000 ton menurut"
    sentence = Sentence(
        text="Hasil panen padi mencapai 10000 ton menurut laporan resmi.",
        quote=quote,
        source_ids=[0],
    )
    assert verify_sentence(sentence, texts) == STATUS_VERIFIED


def test_min_words_lima_lolos_dan_empat_gagal():
    texts = {0: "pertanian organik sangat penting bagi petani daerah"}
    # 5 kata lolos
    quote_5 = "pertanian organik sangat penting bagi"
    sent_5 = Sentence(
        text="Pertanian organik sangat penting bagi petani.",
        quote=quote_5,
        source_ids=[0],
    )
    assert verify_sentence(sent_5, texts) == STATUS_VERIFIED

    # 4 kata gagal (< MIN_WORDS=5)
    quote_4 = "pertanian organik sangat penting"
    sent_4 = Sentence(
        text="Pertanian organik sangat penting bagi petani.",
        quote=quote_4,
        source_ids=[0],
    )
    assert verify_sentence(sent_4, texts) == STATUS_UNVERIFIED


# --- Deteksi salinan verbatim ------------------------------------------------


def test_kalimat_panjang_menyalin_verbatim_ditandai_perlu_ditinjau():
    source = (
        "pemberian biochar dengan dosis sepuluh ton per hektar meningkatkan ph tanah "
        "asam sebesar nol koma lima sampai satu koma dua satuan"
    )
    quote = "biochar dengan dosis sepuluh ton per hektar"
    sentence = Sentence(text=source, quote=quote, source_ids=[0])
    assert verify_sentence(sentence, {0: source}) == STATUS_NEEDS_REVIEW

    statuses = verify_sections(
        [Section(1, "Bab", [Paragraph([sentence])])], {0: source}
    )
    assert statuses[0].status == STATUS_NEEDS_REVIEW
    assert "parafrase" in statuses[0].reason


def test_kalimat_panjang_hasil_parafrase_tetap_terverifikasi():
    source = (
        "pemberian biochar dengan dosis sepuluh ton per hektar meningkatkan ph tanah "
        "asam sebesar nol koma lima sampai satu koma dua satuan"
    )
    quote = "biochar dengan dosis sepuluh ton per hektar"
    paraphrase = (
        "biochar sepuluh ton per hektar dinaikkan untuk memperbaiki ph tanah masam "
        "sekitar nol koma lima hingga satu koma dua poin"
    )
    assert verify_sentence(
        Sentence(text=paraphrase, quote=quote, source_ids=[0]), {0: source}
    ) == STATUS_VERIFIED


def test_kalimat_pendek_tidak_dihukum_karena_kebetulan_sama():
    # < 12 kata: pernyataan pendek yang sama dengan kutipan tetap terverifikasi.
    source = "pertanian organik di indonesia sangat penting bagi petani kecil"
    sentence = Sentence(
        text="Pertanian organik di Indonesia sangat penting bagi petani.",
        quote="pertanian organik di indonesia sangat penting bagi petani",
        source_ids=[0],
    )
    assert verify_sentence(sentence, {0: source}) == STATUS_VERIFIED


# --- Verifikasi kutipan lintas bahasa (kalimat ID <-> sumber EN) --------------

EN_SOURCE = (
    "social media use is associated with lower academic performance and reduced "
    "study time among college students in the survey"
)


def test_kalimat_terjemahan_dengan_kutipan_asing_eksak_terverifikasi():
    sentence = Sentence(
        text=(
            "Penggunaan media sosial yang berlebihan berkaitan dengan menurunnya "
            "prestasi akademik dan berkurangnya waktu belajar mahasiswa."
        ),
        quote=EN_SOURCE,
        source_ids=[0],
    )
    statuses = verify_sections(
        [Section(1, "Bab", [Paragraph([sentence])])], {0: EN_SOURCE}
    )
    assert statuses[0].status == STATUS_VERIFIED
    assert "terjemahan" in statuses[0].reason


def test_kutipan_asing_yang_tidak_ada_di_sumber_tetap_tidak_terverifikasi():
    sentence = Sentence(
        text=(
            "Penggunaan media sosial yang berlebihan berkaitan dengan menurunnya "
            "prestasi akademik dan berkurangnya waktu belajar mahasiswa."
        ),
        quote="this exact quotation does not appear anywhere in the source text at all",
        source_ids=[0],
    )
    assert verify_sentence(sentence, {0: EN_SOURCE}) == STATUS_UNVERIFIED


def test_kalimat_inggris_salinan_verbatim_tetap_perlu_ditinjau():
    verbatim = (
        "Social media use is associated with lower academic performance and "
        "reduced study time among college students in the survey."
    )
    sentence = Sentence(text=verbatim, quote=EN_SOURCE, source_ids=[0])
    statuses = verify_sections(
        [Section(1, "Bab", [Paragraph([sentence])])], {0: EN_SOURCE}
    )
    assert statuses[0].status == STATUS_NEEDS_REVIEW
    assert "parafrase" in statuses[0].reason


def test_halusinasi_sebahasa_tetap_perlu_ditinjau():
    """Kalimat Indonesia yang tidak didukung sumber Indonesia tidak dianggap terjemahan."""
    source = "laporan penelitian pertanian organik di indonesia sangat penting bagi petani"
    sentence = Sentence(
        text="Pemerintah melarang ekspor komoditas beras secara ketat di pasar internasional.",
        quote="pertanian organik di indonesia sangat penting bagi petani",
        source_ids=[0],
    )
    assert verify_sentence(sentence, {0: source}) == STATUS_NEEDS_REVIEW


# --- Kutipan berelipsis ("...") ----------------------------------------------


EN_LONG = (
    "In educational institutions, the impact of social media on academic performance "
    "remains a highly debated topic. Numerous studies have demonstrated a negative "
    "relationship between social media use and academic achievement among students."
)


def test_kutipan_berelipsis_yang_semua_bagiannya_ada_tetap_terverifikasi():
    quote = (
        "impact of social media on academic performance remains a highly debated topic "
        "... Numerous studies have demonstrated a negative relationship"
    )
    sentence = Sentence(
        text=(
            "Pengaruh media sosial terhadap prestasi akademik mahasiswa masih menjadi "
            "perdebatan, dan banyak studi menunjukkan hubungan negatif antara keduanya."
        ),
        quote=quote,
        source_ids=[0],
    )
    statuses = verify_sections([Section(1, "Bab", [Paragraph([sentence])])], {0: EN_LONG})
    assert statuses[0].status == STATUS_VERIFIED


def test_kutipan_berelipsis_dengan_satu_bagian_hilang_tetap_tidak_terverifikasi():
    quote = (
        "impact of social media on academic performance remains a highly debated topic "
        "... kalimat ini sama sekali tidak ada di sumber"
    )
    sentence = Sentence(
        text="Pengaruh media sosial terhadap prestasi akademik masih diperdebatkan.",
        quote=quote,
        source_ids=[0],
    )
    assert verify_sentence(sentence, {0: EN_LONG}) == STATUS_UNVERIFIED
