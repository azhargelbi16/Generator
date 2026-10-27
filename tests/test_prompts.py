"""Tes prompt AI: aturan kedalaman berbasis paragraf, panduan paragraf, anti-ulang."""

from generator.ai import prompts
from generator.ai.citation import Author, Source


def _sources():
    return [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]


def test_prompt_isi_memuat_aturan_kedalaman_berbasis_paragraf():
    messages = prompts.content_prompt(
        "Topik", ["BAB 1. PENDAHULUAN", "1.1 Latar Belakang"],
        _sources(), [(0, "teks sumber yang cukup panjang")],
    )
    system = messages[0]["content"]
    assert "KEDALAMAN ISI WAJIB" in system
    assert "minimal 3 paragraf" in system
    assert "minimal 2 sampai 3 paragraf" in system
    assert "3 sampai 5 kalimat" in system


def test_prompt_isi_meminta_penanda_paragraph():
    messages = prompts.content_prompt(
        "Topik", ["BAB 1. PENDAHULUAN"], _sources(), [(0, "teks sumber")],
    )
    system = messages[0]["content"]
    assert '"paragraph"' in system
    assert "nomor paragraf" in system


def test_prompt_isi_mengecualikan_daftar_bernomor():
    messages = prompts.content_prompt(
        "Topik", ["BAB 1. PENDAHULUAN"], _sources(), [(0, "teks sumber")],
    )
    system = messages[0]["content"]
    assert "KECUALI" in system and "daftar bernomor" in system
    assert "satu butir satu kalimat" in system


def test_prompt_isi_melarang_mengulang_untuk_memenuhi_kuota():
    messages = prompts.content_prompt(
        "Topik", ["BAB 1. PENDAHULUAN"], _sources(), [(0, "teks sumber")],
    )
    system = messages[0]["content"]
    assert "aspek baru" in system
    assert "tidak boleh diulang untuk memenuhi kuota" in system
    assert "kalimat mirip akan dibuang sistem" in system


def test_panduan_paragraf_untuk_bab_hasil_dan_pembahasan():
    guidance = prompts.paragraph_guidance(["BAB 3. HASIL DAN PEMBAHASAN", "3.1 Hasil"])
    assert "PANDUAN PARAGRAF BAB HASIL DAN PEMBAHASAN" in guidance
    assert "paragraf 2" in guidance and "perbandingan" in guidance


def test_panduan_paragraf_untuk_pembahasan_varian_d():
    guidance = prompts.paragraph_guidance(["BAB 3. PEMBAHASAN", "3.1 {Jawaban rumusan masalah 1}"])
    assert "PANDUAN PARAGRAF BAB PEMBAHASAN" in guidance
    assert "mekanisme" in guidance


def test_panduan_paragraf_untuk_tinjauan_pustaka():
    guidance = prompts.paragraph_guidance(["BAB 2. TINJAUAN PUSTAKA", "2.1 {Topik 1}"])
    assert "PANDUAN PARAGRAF BAB TINJAUAN PUSTAKA" in guidance
    assert "definisi/konsep" in guidance


def test_tanpa_panduan_untuk_bab_lain():
    assert prompts.paragraph_guidance(["BAB 1. PENDAHULUAN", "1.1 Latar Belakang"]) == ""


def test_prompt_fokus_bab_menekankan_hanya_bab_ini():
    messages = prompts.content_prompt(
        "Topik", ["BAB 2. TINJAUAN PUSTAKA"], _sources(), [(0, "teks")],
        chapter_focus="BAB 2. TINJAUAN PUSTAKA",
    )
    system = messages[0]["content"]
    assert "TUGAS BAB INI" in system
    assert 'HANYA section untuk "BAB 2. TINJAUAN PUSTAKA"' in system
    assert "JANGAN menulis bab atau subbab" in system


def test_format_wajib_melarang_judul_kalimat_untuk_placeholder():
    messages = prompts.content_prompt(
        "Topik", ["BAB 2. TINJAUAN PUSTAKA"], _sources(), [(0, "teks sumber")],
        variant="B",
    )
    system = messages[0]["content"]
    assert "frasa nomina" in system
    assert "DILARANG kalimat utuh" in system
    assert "klausa yang menggantung" in system