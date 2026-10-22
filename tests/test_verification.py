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
