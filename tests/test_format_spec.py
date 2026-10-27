"""Tes format baku laporan: varian A/B/C dan normalisasi struktur."""

import re

from generator import format_spec
from generator.ai.content import Paragraph, Section, Sentence


def _sec(level, title, text="Isi."):
    return Section(level, title, [Paragraph([Sentence(text, "kutipan", [0])])])


def _titles(sections):
    return [section.title for section in sections]


def test_empat_varian_tersedia_berurutan():
    assert [variant.code for variant in format_spec.VARIANTS] == ["A", "B", "C", "D"]


def test_varian_a_bab_dan_subbab_bernomor():
    variant = format_spec.get_variant("A")
    lines = format_spec.skeleton_lines(variant)
    assert "BAB 1. PENDAHULUAN" in lines
    assert any(line.startswith("  1.1 Latar Belakang") for line in lines)
    assert any(line.startswith("    2.1.1 {Aspek 1}") for line in lines)
    assert any(line.startswith("  4.2 Saran") for line in lines)


def test_varian_c_tanpa_rumusan_masalah_dan_saran_opsional():
    variant = format_spec.get_variant("C")
    lines = "\n".join(format_spec.skeleton_lines(variant))
    assert "Rumusan Masalah" not in lines
    assert "  2.1 Tempat dan Waktu Praktikum" in lines
    assert "Saran (opsional)" in lines


def test_varian_b_bab_empat_kesimpulan_dan_saran():
    titles = format_spec.outline_titles(format_spec.get_variant("B"))
    assert titles == [
        "BAB 1. PENDAHULUAN",
        "BAB 2. TINJAUAN PUSTAKA",
        "BAB 3. HASIL DAN PEMBAHASAN",
        "BAB 4. KESIMPULAN DAN SARAN",
    ]


def test_varian_d_tinjauan_pustaka_tanpa_bab_hasil():
    variant = format_spec.get_variant("D")
    titles = format_spec.outline_titles(variant)
    assert titles == [
        "BAB 1. PENDAHULUAN",
        "BAB 2. TINJAUAN PUSTAKA",
        "BAB 3. PEMBAHASAN",
        "BAB 4. KESIMPULAN DAN SARAN",
    ]
    assert not any("HASIL" in title for title in titles)
    lines = "\n".join(format_spec.skeleton_lines(variant))
    assert "2.1 {Topik 1}" in lines
    assert "2.5 {Topik 5}" in lines
    assert "3.1 {Jawaban rumusan masalah 1}" in lines
    assert "Rumusan Masalah" in lines
    assert "Saran" in lines


def test_varian_d_ikut_tampil_di_pilihan_format():
    codes = [code for code, _label in format_spec.variant_choices()]
    assert "D" in codes
    label = dict(format_spec.variant_choices())["D"]
    assert "Tinjauan" in label


def test_kode_bebas_dan_tak_dikenal_menghasilkan_none():
    assert format_spec.get_variant("bebas") is None
    assert format_spec.get_variant("") is None
    assert format_spec.get_variant("Z") is None


def test_blok_prompt_memuat_aturan_wajib_dan_struktur():
    block = format_spec.format_block(format_spec.get_variant("A"))
    assert "FORMAT WAJIB" in block
    assert "BAB 1. PENDAHULUAN" in block
    assert "[GAMBAR: ...]" in block
    assert "Jangan mengarang" in block


def test_normalisasi_memberi_nomor_bab_dan_subbab():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "pendahuluan"),
        _sec(2, "latar belakang"),
        _sec(2, "rumusan masalah"),
    ]
    result = format_spec.normalize_sections(variant, raw)
    assert result[0].title == "BAB 1. PENDAHULUAN"
    assert result[0].level == 1
    assert result[1].title == "1.1 Latar Belakang"
    assert result[2].title == "1.2 Rumusan Masalah"


def test_normalisasi_melengkapi_bab_kosong_sesuai_varian():
    variant = format_spec.get_variant("B")
    result = format_spec.normalize_sections(variant, [_sec(1, "pendahuluan")])
    chapters = [section.title for section in result if section.level == 1]
    assert chapters == [
        "BAB 1. PENDAHULUAN",
        "BAB 2. TINJAUAN PUSTAKA",
        "BAB 3. HASIL DAN PEMBAHASAN",
        "BAB 4. KESIMPULAN DAN SARAN",
    ]
    assert all(section.level in (1, 2, 3) for section in result)


def test_normalisasi_mempertahankan_isi_dan_urutan_skeleton():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "BAB 4. KESIMPULAN DAN SARAN"),
        _sec(2, "Kesimpulan", "Kesimpulan satu."),
        _sec(1, "BAB 1. PENDAHULUAN"),
        _sec(2, "Latar Belakang", "Latar belakang satu."),
    ]
    result = format_spec.normalize_sections(variant, raw)
    assert result[0].title == "BAB 1. PENDAHULUAN"
    assert result[1].title == "1.1 Latar Belakang"
    assert result[1].paragraphs[0].sentences[0].text == "Latar belakang satu."
    chapter_four = [section.title for section in result if section.level == 1][-1]
    assert chapter_four == "BAB 4. KESIMPULAN DAN SARAN"
    assert "4.1 Kesimpulan" in _titles(result)


def test_normalisasi_judul_dinamis_memakai_judul_ai():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "PENDAHULUAN"),
        _sec(1, "TINJAUAN PUSTAKA"),
        _sec(2, "Subjek Bahasan Utama"),
        _sec(3, "Aspek Pertama Penggunaan"),
    ]
    result = format_spec.normalize_sections(variant, raw)
    titles = _titles(result)
    assert "2.1 Subjek Bahasan Utama" in titles
    assert "2.1.1 Aspek Pertama Penggunaan" in titles


def test_normalisasi_membuang_saran_opsional_kosong_varian_c():
    variant = format_spec.get_variant("C")
    raw = [
        _sec(1, "PENUTUP"),
        _sec(2, "Kesimpulan", "Kesimpulan."),
        Section(2, "Saran", []),
    ]
    result = format_spec.normalize_sections(variant, raw)
    titles = _titles(result)
    assert "4.1 Kesimpulan" in titles
    assert not any("Saran" in title for title in titles)


def test_normalisasi_mengisi_subbab_kosong_dari_bagian_tambahan():
    """Isi subbab tambahan mengisi subbab wajib yang kosong, bukan dibuang."""
    variant = format_spec.get_variant("B")
    raw = [
        Section(1, "PENDAHULUAN", []),
        _sec(2, "Catatan Tambahan", "Tambahan."),
    ]
    result = format_spec.normalize_sections(variant, raw)
    all_texts = [x.text for s in result for p in s.paragraphs for x in p.sentences]
    assert "Tambahan." in all_texts
    latar = next(s for s in result if "Latar Belakang" in s.title)
    assert [x.text for p in latar.paragraphs for x in p.sentences] == ["Tambahan."]


def test_normalisasi_tanpa_bagian_mengembalikan_skeleton():
    variant = format_spec.get_variant("B")
    result = format_spec.normalize_sections(variant, [])
    assert result[0].title == "BAB 1. PENDAHULUAN"
    assert [section.title for section in result if section.level == 1][-1] == (
        "BAB 4. KESIMPULAN DAN SARAN"
    )


def test_prompt_isi_memuat_format_wajib_saat_varian_dipilih():
    from generator.ai import prompts

    messages = prompts.content_prompt("Topik", ["BAB 1. PENDAHULUAN"], [], [], variant="B")
    system = messages[0]["content"]
    assert "FORMAT WAJIB" in system
    assert "BAB 4. KESIMPULAN DAN SARAN" in system
    assert "3.2.2" in system


def test_prompt_isi_tanpa_varian_tidak_menambah_format():
    from generator.ai import prompts

    messages = prompts.content_prompt("Topik", ["Pendahuluan"], [], [])
    assert "FORMAT WAJIB" not in messages[0]["content"]


def test_generate_sections_menormalkan_struktur_saat_varian_dipilih():
    import json

    from generator.ai.citation import Author, Source
    from generator.ai.content import generate_sections

    reply = json.dumps(
        {
            "sections": [
                {
                    "level": 1,
                    "title": "Pendahuluan",
                    "paragraphs": [
                        {
                            "sentences": [
                                {
                                    "text": "Klaim faktual.",
                                    "quote": "teks sumber",
                                    "source_ids": [0],
                                    "is_factual": True,
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    )

    class FakeClient:
        def chat(self, messages, json_mode=False):
            return reply

    source = Source([Author("Santoso", "Budi")], "2020", "T", "J")
    sections = generate_sections(
        "tema", ["BAB 1. PENDAHULUAN"], [source], ["teks sumber yang panjang"],
        FakeClient(), variant="B",
    )
    assert sections[0].title == "BAB 1. PENDAHULUAN"
    # Isi yang model taruh di level BAB disebar ke subbabnya (bukan tetap di
    # level bab), jadi teksnya dicari di seluruh section.
    all_texts = [s.text for sec in sections for p in sec.paragraphs for s in p.sentences]
    assert "Klaim faktual." in all_texts
    titles = [section.title for section in sections]
    assert "1.1 Latar Belakang" in titles
    assert "BAB 4. KESIMPULAN DAN SARAN" in titles


def test_chapter_sub_outlines_mempertahankan_penanda_judul_dinamis():
    """Judul {..} harus sampai ke AI dengan kurawal agar diganti judul nyata.

    Tanpa penanda, model menyalin nama template ("Pembahasan topik 1") ke DOCX.
    """
    chapters = format_spec.chapter_sub_outlines(format_spec.get_variant("B"))
    bab2 = dict(chapters)["BAB 2. TINJAUAN PUSTAKA"]
    assert any("{Subjek}" in title for title in bab2)
    bab3 = dict(chapters)["BAB 3. HASIL DAN PEMBAHASAN"]
    assert any("{Pembahasan topik 1}" in title for title in bab3)
    # Judul tetap tidak ikut berkurawal.
    assert "3.1 Hasil" in bab3


def test_generate_varian_d_tanpa_bab_hasil():
    import json

    from generator.ai.citation import Author, Source
    from generator.ai.content import generate_sections

    reply = json.dumps({
        "sections": [{
            "level": 2,
            "title": "Latar Belakang",
            "paragraphs": [{"sentences": [{
                "text": "Klaim faktual tentang biochar dan kesuburan tanah.",
                "quote": "teks sumber",
                "source_ids": [0],
                "is_factual": True,
            }]}],
        }],
    })

    class FakeClient:
        def chat(self, messages, json_mode=False):
            return reply

    source = Source([Author("Santoso", "Budi")], "2020", "T", "J")
    sections = generate_sections(
        "tema", format_spec.outline_titles(format_spec.get_variant("D")),
        [source], ["teks sumber yang panjang"], FakeClient(), variant="D",
    )
    titles = [section.title for section in sections]
    assert "BAB 3. PEMBAHASAN" in titles
    assert not any("HASIL" in title for title in titles)


# --- Varian D: 3–5 subbab, judul template tidak bocor ------------------------


def _sub(title, text):
    return Section(2, title, [Paragraph([Sentence(text, "q", [0])])])


def test_judul_placeholder_dari_ai_tidak_bocor_ke_dokumen():
    variant = format_spec.get_variant("D")
    sections = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        _sub("Latar Belakang", "Konteks masalah."),
        _sub("Rumusan Masalah", "1. Pertanyaan pertama?"),
        _sub("Tujuan", "1. Tujuan pertama."),
        Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
        _sub("{Topik 1}", "Isi topik satu."),
        _sub("{Topik 2}", "Isi topik dua."),
        Section(1, "BAB 3. PEMBAHASAN", []),
        _sub("{Jawaban rumusan masalah 1}", "Jawaban pertama."),
        Section(1, "BAB 4. KESIMPULAN DAN SARAN", []),
        _sub("Kesimpulan", "1. Simpulan."),
    ]

    out = format_spec.normalize_sections(variant, sections)
    titles = [section.title for section in out]
    assert not any("{" in title or "}" in title for title in titles), titles
    assert "BAB 2. TINJAUAN PUSTAKA" in titles
    assert "BAB 3. PEMBAHASAN" in titles
    # Isi yang judulnya masih nama template tidak hilang.
    texts = [s.text for section in out for p in section.paragraphs for s in p.sentences]
    assert "Isi topik satu." in texts and "Jawaban pertama." in texts


def test_varian_d_membatasi_subbab_tinjauan_pustaka_lima():
    variant = format_spec.get_variant("D")
    sections = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        _sub("Latar Belakang", "Konteks."),
        Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
    ]
    for index in range(8):
        sections.append(_sub(f"Topik {index + 1} yang dibahas", f"Isi topik {index + 1}."))
    sections.append(Section(1, "BAB 3. PEMBAHASAN", []))

    out = format_spec.normalize_sections(variant, sections)
    bab2 = [s for s in out if s.level == 2 and s.title.startswith("2.")]
    assert len(bab2) <= 5
    # Seluruh isi tetap ada walau jumlah judul dibatasi.
    texts = [x.text for s in out for p in s.paragraphs for x in p.sentences]
    assert all(f"Isi topik {index + 1}." in texts for index in range(8))


# --- Penanda tabel: hanya varian praktikum, dan deskriptornya dibuang --------


def test_varian_b_dan_d_tidak_meminta_tabel():
    block_b = format_spec.format_block(format_spec.get_variant("B"))
    block_d = format_spec.format_block(format_spec.get_variant("D"))
    block_c = format_spec.format_block(format_spec.get_variant("C"))
    assert "BUKAN laporan penelitian lapangan" in block_b
    assert "BUKAN laporan penelitian lapangan" in block_d
    assert "BUKAN laporan penelitian lapangan" not in block_c


def test_normalisasi_membuang_kalimat_deskriptor_penanda_tabel():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "PENDAHULUAN"),
        _sec(2, "1.1 Latar Belakang", "Konteks penelitian ini penting bagi petani."),
        _sec(2, "1.1 Latar Belakang", "Hasil penelitian ini disajikan dalam bentuk penanda tabel terkait temuan empiris."),
        _sec(2, "1.1 Latar Belakang", "[TABEL: Ringkasan hasil penelitian]"),
    ]

    out = format_spec.normalize_sections(variant, raw)
    texts = [x.text for s in out for p in s.paragraphs for x in p.sentences]
    assert not any("disajikan dalam bentuk penanda" in text for text in texts)
    # Penanda mentah tetap ada agar gerbang ekspor menolaknya.
    assert "[TABEL: Ringkasan hasil penelitian]" in texts


# --- Batas paragraf & BAB 4 tanpa prosa --------------------------------------


def test_normalisasi_membatasi_paragraf_subbab_maksimal_enam():
    variant = format_spec.get_variant("B")
    paragraphs = [Paragraph([Sentence(f"Kalimat {index}.", "q", [0])]) for index in range(8)]
    raw = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        Section(2, "1.1 Latar Belakang", paragraphs),
    ]

    out = format_spec.normalize_sections(variant, raw)
    latar = next(s for s in out if "Latar Belakang" in s.title)
    assert len(latar.paragraphs) <= 6
    assert sum(len(p.sentences) for p in latar.paragraphs) == 8


def test_paragraf_wrapper_lebih_lima_kalimat_dipecah():
    variant = format_spec.get_variant("B")
    panjang = Paragraph([Sentence(f"Kalimat nomor {index}.", "q", [0]) for index in range(12)])
    raw = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        Section(2, "1.1 Latar Belakang", [panjang]),
    ]

    out = format_spec.normalize_sections(variant, raw)
    latar = next(s for s in out if "Latar Belakang" in s.title)
    assert len(latar.paragraphs) >= 3
    assert all(len(p.sentences) <= 5 for p in latar.paragraphs)
    assert sum(len(p.sentences) for p in latar.paragraphs) == 12
    # Butir bernomor tidak ikut dipecah/digabung.
    butir = Paragraph([Sentence(f"{i}. Butir {i}.", "q", [0]) for i in range(1, 8)])
    raw_butir = [
        _sec(1, "BAB 1. PENDAHULUAN"),
        Section(2, "1.2 Rumusan Masalah", [butir]),
    ]
    out_butir = format_spec.normalize_sections(variant, raw_butir)
    rumusan = next(s for s in out_butir if "Rumusan Masalah" in s.title)
    assert all(len(p.sentences) == 1 for p in rumusan.paragraphs)


def test_varian_b_bab_empat_tanpa_paragraf_level_bab():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "BAB 1. PENDAHULUAN"),
        _sec(2, "1.1 Latar Belakang", "Konteks penelitian ini penting."),
        Section(1, "BAB 4. KESIMPULAN DAN SARAN", [
            Paragraph([Sentence("Prosa pembuka bab yang tidak diinginkan.", "q", [0])]),
            Paragraph([Sentence("Prosa penutup bab yang tidak diinginkan.", "q", [0])]),
        ]),
        _sec(2, "4.1 Kesimpulan", "1. Simpulan pertama."),
        _sec(2, "4.2 Saran", "1. Saran pertama."),
    ]

    out = format_spec.normalize_sections(variant, raw)
    bab4 = next(s for s in out if s.level == 1 and "KESIMPULAN" in s.title)
    assert bab4.paragraphs == []
    texts = [x.text for s in out for p in s.paragraphs for x in p.sentences]
    assert "Prosa pembuka bab yang tidak diinginkan." not in texts
    assert "1. Simpulan pertama." in texts
    assert "1. Saran pertama." in texts


def test_varian_b_butir_bernomor_di_level_bab_dipindahkan_ke_subbab():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "BAB 1. PENDAHULUAN"),
        _sec(2, "1.1 Latar Belakang", "Konteks penelitian ini penting."),
        Section(1, "BAB 4. KESIMPULAN DAN SARAN", [
            Paragraph([
                Sentence("1. Butir simpulan yang menempel di level bab.", "q", [0]),
                Sentence("2. Saran yang menempel di level bab.", "q", [0]),
            ]),
        ]),
        _sec(2, "4.1 Kesimpulan", "1. Simpulan pertama."),
        _sec(2, "4.2 Saran", "1. Saran pertama."),
    ]

    out = format_spec.normalize_sections(variant, raw)
    bab4 = next(s for s in out if s.level == 1 and "KESIMPULAN" in s.title)
    assert bab4.paragraphs == []
    kesimpulan = next(s for s in out if s.title.startswith("4.1"))
    saran = next(s for s in out if s.title.startswith("4.2"))
    kesimpulan_texts = [x.text for p in kesimpulan.paragraphs for x in p.sentences]
    saran_texts = [x.text for p in saran.paragraphs for x in p.sentences]
    assert "1. Butir simpulan yang menempel di level bab." in kesimpulan_texts
    assert "2. Saran yang menempel di level bab." in saran_texts


def test_varian_c_penutup_mempertahankan_prosa_level_bab():
    variant = format_spec.get_variant("C")
    raw = [
        _sec(1, "BAB 1. PENDAHULUAN"),
        _sec(2, "1.1 Latar Belakang", "Konteks praktikum."),
        Section(1, "BAB 4. PENUTUP", [
            Paragraph([Sentence("Prosa penutup yang sah untuk varian C.", "q", [0])]),
        ]),
        _sec(2, "4.1 Kesimpulan", "1. Simpulan praktikum."),
    ]

    out = format_spec.normalize_sections(variant, raw)
    bab4 = next(s for s in out if s.level == 1 and "PENUTUP" in s.title)
    texts = [x.text for p in bab4.paragraphs for x in p.sentences]
    assert "Prosa penutup yang sah untuk varian C." in texts


def test_isi_level_bab_disebar_ke_subbab_varian_b():
    """Model kadang menaruh seluruh isi BAB 2 di level bab; harus disebar ke subbab."""
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "BAB 1. PENDAHULUAN"),
        _sec(2, "1.1 Latar Belakang", "Konteks penelitian ini penting."),
        Section(1, "BAB 2. TINJAUAN PUSTAKA", [
            Paragraph([Sentence(f"Topik kajian nomor {index} dibahas di sini.", "q", [0])])
            for index in range(1, 5)
        ]),
    ]

    out = format_spec.normalize_sections(variant, raw)
    bab2 = next(s for s in out if s.level == 1 and "TINJAUAN" in s.title)
    assert bab2.paragraphs == []
    subs = [s for s in out if s.level >= 2 and s.title.startswith("2.")]
    assert len(subs) >= 2
    assert all(section.paragraphs for section in subs)
    assert all("{" not in section.title for section in subs)


# --- FASE 1: judul section frasa nomina, bukan potongan kalimat ----------------


def test_sanitize_memotong_judul_kalimat_di_penanda_klausa():
    # Gejala dokumen final: judul terpotong di konjungsi/kata depan/kata kerja.
    assert format_spec._sanitize_title(
        "Media sosial telah menjadi bagian yang tidak"
    ) == "Media Sosial"
    assert format_spec._sanitize_title(
        "Durasi waktu harian yang dihabiskan di dunia maya"
    ) == "Durasi Waktu Harian"
    assert format_spec._sanitize_title(
        "Platform digital dan jejaring sosial telah berkembang pesat"
    ) == "Platform Digital dan Jejaring Sosial"


def test_sanitize_sisa_kiri_kurang_tiga_kata_ambil_frasa_sesudahnya():
    assert format_spec._sanitize_title(
        "Media sosial telah menjadi bagian yang tidak dapat dipisahkan dari kehidupan pelajar"
    ) == "Dipisahkan dari Kehidupan Pelajar"
    assert format_spec._sanitize_title("Yang menjadi sorotan utama") == "Sorotan Utama"


def test_sanitize_normalisasi_kapital_dan_akronim():
    assert format_spec._sanitize_title("durasi penggunaan LED oleh siswa") == (
        "Durasi Penggunaan LED oleh Siswa"
    )
    # Judul baku varian idempoten terhadap normalisasi kapital.
    assert format_spec._sanitize_title("Tempat dan Waktu Praktikum") == (
        "Tempat dan Waktu Praktikum"
    )
    # Judul seluruhnya kapital (echo judul BAB) dinormalkan.
    assert format_spec._sanitize_title("DURASI WAKTU HARIAN PELAJAR") == (
        "Durasi Waktu Harian Pelajar"
    )


def test_sanitize_buang_kata_sambung_menggantung_di_ujung():
    assert format_spec._sanitize_title("Analisis faktor internal dan") == (
        "Analisis Faktor Internal"
    )
    assert format_spec._sanitize_title("Temuan lapangan untuk") == "Temuan Lapangan"
    assert format_spec._sanitize_title("Analisis motif menunjukkan bahwa") == (
        "Analisis Motif Menunjukkan"
    )


def test_sanitize_placeholder_setelah_potong_jatuh_ke_fallback():
    # "Topik 1 yang dibahas" terpotong menjadi "Topik 1" -> placeholder -> fallback.
    assert format_spec._sanitize_title(
        "Topik 1 yang dibahas", "Latar Belakang"
    ) == "Latar Belakang"
    assert format_spec._sanitize_title("Pembahasan topik 1") == ""


def test_judul_dinamis_kembar_diganti_turunan_isi():
    """AI mengulang judul baku "Pembahasan": sub-subbab tidak boleh kembar."""
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "BAB 3. HASIL DAN PEMBAHASAN"),
        _sec(2, "3.1 Hasil", "Tabel hasil utama."),
        _sec(2, "3.2 Pembahasan", "Paragraf pembuka pembahasan."),
        _sec(3, "Pembahasan", "Faktor akademik memengaruhi prestasi siswa."),
        _sec(3, "Pembahasan", "Mediasi waktu belajar menentukan hasil ujian."),
    ]
    out = format_spec.normalize_sections(variant, raw)
    subs = [s.title for s in out if s.level == 3 and s.title.startswith("3.2.")]
    assert len(subs) == 2, subs
    keys = [re.sub(r"^[\d.]+\s*", "", t).casefold() for t in subs]
    assert len(set(keys)) == 2, subs
    assert "pembahasan" not in keys, subs


def test_fallback_generik_tidak_menghasilkan_judul_kembar():
    """{Aspek 1} pada dua induk berbeda tidak boleh sama-sama "Aspek Pertama"."""
    variant = format_spec.get_variant("A")
    raw = [
        _sec(1, "BAB 2. TINJAUAN PUSTAKA"),
        _sec(2, "{Subjek}", "Berbagai penelitian mengkaji media sosial pelajar."),
        _sec(3, "{Aspek 1}", "Berbagai penelitian mengkaji motif penggunaan."),
        _sec(3, "{Aspek 2}", "Berbagai penelitian mengkaji durasi akses."),
        _sec(2, "{Objek 1}", "Berbagai penelitian mengkaji prestasi akademik."),
        _sec(3, "{Aspek 1}", "Berbagai penelitian mengkaji faktor sekolah."),
        _sec(3, "{Aspek 2}", "Berbagai penelitian mengkaji faktor keluarga."),
    ]
    out = format_spec.normalize_sections(variant, raw)
    titles = [s.title for s in out if s.level >= 2]
    stripped = [re.sub(r"^[\d.]+\s*", "", t).casefold() for t in titles]
    assert len(stripped) == len(set(stripped)), titles
    assert not any("{" in t or "}" in t for t in titles), titles


def test_kata_sarana_bukan_subbab_daftar():
    """Substring "saran" dalam "Sarana" tidak boleh mengubah perlakuan subbab.

    Subbab naratif berjudul "...Sarana Pembelajaran..." tetap dibatasi maksimal
    6 paragraf seperti subbab naratif lain, bukan dikecualikan seperti daftar
    bernomor.
    """
    variant = format_spec.get_variant("B")
    paragraphs = [Paragraph([Sentence(f"Kalimat sarana {index}.", "q", [0])]) for index in range(9)]
    raw = [
        Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
        Section(2, "Media Sosial sebagai Sarana Pembelajaran", paragraphs),
    ]
    out = format_spec.normalize_sections(variant, raw)
    section = next(s for s in out if "Sarana" in s.title)
    assert len(section.paragraphs) <= 6, section.title
    # Sebaliknya, judul daftar asli tetap dikenali.
    assert format_spec._LIST_TITLE_RE.search("4.2 Saran")
    assert format_spec._LIST_TITLE_RE.search("1.2 Rumusan Masalah")
    assert not format_spec._LIST_TITLE_RE.search("Sarana Pembelajaran Terbuka")



def test_pembahasan_subbab_dinamis_mengambil_judul_dari_rumusan_masalah():
    variant = format_spec.get_variant("D")
    sections = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        _sub("Latar Belakang", "Latar belakang masalah."),
        _sub("Rumusan Masalah", (
            "1. Bagaimana peran inovasi teknologi?\n"
            "2. Faktor apa yang mempengaruhi adopsi?\n"
            "3. Bagaimana bentuk hubungan penyuluhan dan implementasi Jajar Legowo?\n"
            "4. Apa saja tantangan integrasi teknologi?"
        )),
        _sub("Tujuan", "1. Tujuan satu.\n2. Tujuan dua.\n3. Tujuan tiga.\n4. Tujuan empat."),
        Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
        _sub("{Topik 1}", "Isi topik satu."),
        _sub("{Topik 2}", "Isi topik dua."),
        Section(1, "BAB 3. PEMBAHASAN", []),
        _sub("{Jawaban rumusan masalah 1}", "Jawaban satu."),
        _sub("{Jawaban rumusan masalah 2}", "Jawaban dua."),
        _sub("{Jawaban rumusan masalah 3}", "Tingkat implementasi inovasi di lapangan sangat dipengaruhi oleh kombinasi antara dukungan penyuluhan pertanian dan persepsi positif petani terhadap karakteristik teknik penanaman yang diperkenalkan seperti sistem Jajar Legowo."),
        _sub("{Jawaban rumusan masalah 4}", "Proses integrasi teknologi pertanian di berbagai wilayah sering kali dihadapkan pada berbagai tantangan nyata seperti tingginya biaya implementasi."),
        Section(1, "BAB 4. KESIMPULAN DAN SARAN", []),
        _sub("Kesimpulan", "1. Simpulan."),
        _sub("Saran", "1. Saran."),
    ]

    out = format_spec.normalize_sections(variant, sections)
    titles = [s.title for s in out]

    # Pastikan tidak ada judul cacat/terpotong yang diawali "Diperkenalkan Seperti" atau "Tantangan Nyata Seperti"
    assert not any("Diperkenalkan" in t for t in titles), titles
    assert not any("Seperti" in t for t in titles), titles
    # Subbab 3.3 harus mencerminkan rumusan masalah 3
    assert any("Bentuk Hubungan" in t or "Hubungan Penyuluhan" in t for t in titles), titles
    # Subbab 3.4 harus mencerminkan rumusan masalah 4
    assert any("Tantangan Integrasi" in t or "Tantangan" in t for t in titles), titles
