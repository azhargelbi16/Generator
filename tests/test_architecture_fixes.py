"""Pengujian regresi untuk perbaikan arsitektur Generator Laporan."""
import pytest
from generator import format_spec, textutil
from generator.ai import content
from generator.document import placeholders


def test_number_tuple_chapter_hierarchy():
    """_number_tuple harus mengembalikan tuple monoton naik untuk bab dan subbab."""
    t_bab1 = content._number_tuple("BAB 1. PENDAHULUAN")
    t_sub11 = content._number_tuple("1.1 Latar Belakang")
    t_sub12 = content._number_tuple("1.2 Rumusan Masalah")
    t_bab2 = content._number_tuple("BAB 2. TINJAUAN PUSTAKA")
    t_sub21 = content._number_tuple("2.1 Tinjauan Umum")
    t_sub22 = content._number_tuple("2.2 Objek Kajian Utama")
    t_bab3 = content._number_tuple("BAB 3. HASIL DAN PEMBAHASAN")
    t_dafpus = content._number_tuple("DAFTAR PUSTAKA")

    assert t_bab1 == (1, 0)
    assert t_bab2 == (2, 0)
    assert t_sub22 == (2, 2)
    assert t_bab1 < t_sub11 < t_sub12 < t_bab2 < t_sub21 < t_sub22 < t_bab3 < t_dafpus


def test_ensure_level2_subbab_bounds():
    """Subbab 2.2 yang dipromosikan tidak boleh disisipkan sebelum BAB 1."""
    variant = format_spec.get_variant("B")
    sections = [
        content.Section(1, "BAB 1. PENDAHULUAN", [
            content.Paragraph([content.Sentence("Pengantar latar belakang.", "", [0])])
        ]),
        content.Section(2, "1.1 Latar Belakang", [
            content.Paragraph([content.Sentence("Isi latar belakang.", "", [0])])
        ]),
        content.Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
        content.Section(2, "2.1 Kajian Pustaka", [
            content.Paragraph([content.Sentence(f"Kalimat {i}.", "", [0]) for i in range(5)]),
            content.Paragraph([content.Sentence(f"Paragraf dua {i}.", "", [0]) for i in range(5)]),
            content.Paragraph([content.Sentence(f"Paragraf tiga {i}.", "", [0]) for i in range(5)]),
            content.Paragraph([content.Sentence(f"Paragraf empat {i}.", "", [0]) for i in range(5)]),
        ]),
        content.Section(1, "BAB 3. HASIL DAN PEMBAHASAN", []),
    ]

    result = content._ensure_level2_subbab(sections, variant)
    titles = [s.title for s in result]

    # Pastikan BAB 1 tetap di indeks 0
    assert titles[0].startswith("BAB 1.")
    # Pastikan ada 2.2 dan letaknya setelah BAB 2
    idx_bab2 = next(i for i, t in enumerate(titles) if t.startswith("BAB 2."))
    idx_sub22 = next((i for i, t in enumerate(titles) if t.startswith("2.2")), None)
    idx_bab3 = next(i for i, t in enumerate(titles) if t.startswith("BAB 3."))

    assert idx_sub22 is not None
    assert idx_bab2 < idx_sub22 < idx_bab3


def test_clause_cut_verb_markers():
    """Kata kerja predikatif harus dipotong rapi menjadi frasa nomina."""
    title1 = format_spec._sanitize_title("Sarana Pembelajaran Terbuka Memberikan Peluang")
    assert title1 == "Sarana Pembelajaran Terbuka"

    title2 = format_spec._sanitize_title("Memfasilitasi Pertukaran Pengetahuan, Diskusi Kelompok")
    assert title2 == "Pertukaran Pengetahuan, Diskusi Kelompok"


def test_strip_citations_in_rumusan_and_saran():
    """Rumusan masalah dan saran harus dibersihkan dari sitasi parenthetik."""
    variant = format_spec.get_variant("B")
    sections = [
        content.Section(1, "BAB 1. PENDAHULUAN", []),
        content.Section(2, "1.2 Rumusan Masalah", [
            content.Paragraph([
                content.Sentence(
                    "1. Bagaimana pengaruh teknologi digital terhadap mahasiswa (Santoso, 2020)?",
                    "Santoso 2020",
                    [0],
                    is_factual=True,
                )
            ])
        ]),
        content.Section(1, "BAB 4. KESIMPULAN DAN SARAN", []),
        content.Section(2, "4.2 Saran", [
            content.Paragraph([
                content.Sentence(
                    "a. Mahasiswa disarankan mengatur waktu harian (Cuong et al., 2025).",
                    "Cuong 2025",
                    [1],
                    is_factual=True,
                )
            ])
        ]),
    ]

    out = format_spec.normalize_sections(variant, sections)
    rumusan_sec = next(s for s in out if "Rumusan Masalah" in s.title)
    saran_sec = next(s for s in out if "Saran" in s.title)

    sent_rumusan = rumusan_sec.paragraphs[0].sentences[0]
    sent_saran = saran_sec.paragraphs[0].sentences[0]

    assert "(Santoso, 2020)" not in sent_rumusan.text
    assert sent_rumusan.text.endswith("terhadap mahasiswa?")
    assert sent_rumusan.is_factual is False
    assert sent_rumusan.source_ids == []

    assert "(Cuong et al., 2025)" not in sent_saran.text
    assert sent_saran.text.endswith("mengatur waktu harian.")
    assert sent_saran.is_factual is False
    assert sent_saran.source_ids == []


def test_glyph_sanitization():
    """Karakter replacement unicode \\ufffd dan tanda kutip rusak harus dibersihkan."""
    fixed = textutil.repair_mojibake("Students\ufffd Academic Performance")
    assert fixed == "Students' Academic Performance"

    cleaned_xml = placeholders.clean_text("Kriszti\ufffdn J\ufffdzsa")
    assert cleaned_xml == "Krisztin Jzsa"
