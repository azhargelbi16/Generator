"""Tes kesejajaran rumusan↔tujuan↔kesimpulan dan sentence case APA 7."""

from generator.ai.content import Paragraph, Section, Sentence
from generator.ai.citation import Author, Source, _sentence_case_title, reference


# --- Kesejajaran rumusan ↔ tujuan ↔ kesimpulan -------------------------------


def test_rumusan_to_tujuan_transformasi():
    from generator.ai.content import _rumusan_to_tujuan

    assert _rumusan_to_tujuan(
        "Bagaimanakah pengaruh media sosial terhadap prestasi mahasiswa"
    ) == "Menganalisis pengaruh media sosial terhadap prestasi mahasiswa"
    assert _rumusan_to_tujuan(
        "Sejauh mana adopsi teknologi memengaruhi kinerja"
    ) == "Menganalisis adopsi teknologi memengaruhi kinerja"
    assert _rumusan_to_tujuan(
        "Apakah pembelajaran daring efektif"
    ) == "Mengkaji pembelajaran daring efektif"


def test_align_numbered_lists_menambah_tujuan_dan_kesimpulan():
    from generator.ai.content import _align_numbered_lists

    rumusan = Section(2, "1.2 Rumusan Masalah", [
        Paragraph([Sentence("1. Bagaimanakah pengaruh media sosial terhadap prestasi?", "", [], False)]),
        Paragraph([Sentence("2. Sejauh mana durasi memengaruhi IPK?", "", [], False)]),
        Paragraph([Sentence("3. Apakah pembelajaran terbuka efektif?", "", [], False)]),
    ])
    tujuan = Section(2, "1.3 Tujuan", [
        Paragraph([Sentence("1. Menganalisis pengaruh media sosial terhadap prestasi.", "", [], False)]),
        Paragraph([Sentence("2. Menganalisis durasi memengaruhi IPK.", "", [], False)]),
    ])
    kesimpulan = Section(2, "4.1 Kesimpulan", [
        Paragraph([Sentence("1. Pengaruh media sosial signifikan.", "", [], False)]),
        Paragraph([Sentence("2. Durasi berkorelasi dengan IPK.", "", [], False)]),
    ])

    _align_numbered_lists([rumusan, tujuan, kesimpulan])

    assert len(tujuan.paragraphs) == 3  # butir ke-3 ditambah dari rumusan ke-3
    assert len(kesimpulan.paragraphs) == 3  # butir ke-3 ditambah dari tujuan
    texts_tujuan = [s.text for p in tujuan.paragraphs for s in p.sentences]
    assert any("Mengkaji" in t or "pembelajaran" in t.lower() for t in texts_tujuan)
    texts_kesimpulan = [s.text for p in kesimpulan.paragraphs for s in p.sentences]
    assert len(texts_kesimpulan) == 3


def test_align_numbered_lists_tidak_mengubah_yang_sudah_sejajar():
    from generator.ai.content import _align_numbered_lists

    rumusan = Section(2, "1.2 Rumusan Masalah", [
        Paragraph([Sentence("1. Bagaimanakah X?", "", [], False)]),
        Paragraph([Sentence("2. Bagaimanakah Y?", "", [], False)]),
    ])
    tujuan = Section(2, "1.3 Tujuan", [
        Paragraph([Sentence("1. Menganalisis X.", "", [], False)]),
        Paragraph([Sentence("2. Menganalisis Y.", "", [], False)]),
    ])
    kesimpulan = Section(2, "4.1 Kesimpulan", [
        Paragraph([Sentence("1. X signifikan.", "", [], False)]),
        Paragraph([Sentence("2. Y signifikan.", "", [], False)]),
    ])

    _align_numbered_lists([rumusan, tujuan, kesimpulan])

    assert len(tujuan.paragraphs) == 2
    assert len(kesimpulan.paragraphs) == 2


# --- Sentence case APA 7 untuk judul artikel -----------------------------------


def test_sentence_case_judul_artikel():
    assert _sentence_case_title(
        "The Impact of Social Media Use Motives on Students GPA"
    ) == "The impact of social media use motives on students GPA"
    assert _sentence_case_title(
        "Social Media Improves Students Academic Performance"
    ) == "Social media improves students academic performance"
    assert _sentence_case_title(
        "The Wired Generation: Academic and Social Outcomes"
    ) == "The wired generation: Academic and social outcomes"


def test_sentence_case_pertahankan_akronim_dan_nama_diri():
    assert _sentence_case_title(
        "COVID-19 Impact on GPA in Vietnam and China"
    ) == "COVID-19 impact on GPA in Vietnam and China"
    assert _sentence_case_title(
        "WeChat Usage Among Students in Indonesia"
    ) == "WeChat usage among students in Indonesia"


def test_reference_memakai_sentence_case():
    src = Source(
        [Author("Cuong", "T. V.")], "2025",
        "The Impact of Social Media Use Motives on Students GPA",
        "Education Sciences", volume="15", issue="3", pages="317",
    )
    r = reference(src)
    assert "The impact of social media use motives on students GPA" in r
    assert "The Impact of Social Media" not in r  # Title Case tidak boleh muncul
