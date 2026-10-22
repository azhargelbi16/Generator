"""Tes format baku laporan: varian A/B/C dan normalisasi struktur."""

from generator import format_spec
from generator.ai.content import Paragraph, Section, Sentence


def _sec(level, title, text="Isi."):
    return Section(level, title, [Paragraph([Sentence(text, "kutipan", [0])])])


def _titles(sections):
    return [section.title for section in sections]


def test_tiga_varian_tersedia_berurutan():
    assert [variant.code for variant in format_spec.VARIANTS] == ["A", "B", "C"]


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
        _sec(2, "Subjek Bahasan"),
        _sec(3, "Aspek Pertama"),
    ]
    result = format_spec.normalize_sections(variant, raw)
    titles = _titles(result)
    assert "2.1 Subjek Bahasan" in titles
    assert "2.1.1 Aspek Pertama" in titles


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


def test_normalisasi_menomori_bagian_tambahan_di_belakang():
    variant = format_spec.get_variant("B")
    raw = [
        _sec(1, "PENDAHULUAN"),
        _sec(2, "Catatan Tambahan", "Tambahan."),
    ]
    result = format_spec.normalize_sections(variant, raw)
    assert "1.4 Catatan Tambahan" in _titles(result)


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
    assert sections[0].paragraphs[0].sentences[0].text == "Klaim faktual."
    titles = [section.title for section in sections]
    assert "1.1 Latar Belakang" in titles
    assert "BAB 4. KESIMPULAN DAN SARAN" in titles

