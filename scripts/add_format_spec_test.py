from pathlib import Path

p = Path("tests/test_format_spec.py")
content = p.read_text(encoding="utf-8")

new_test = '''

def test_pembahasan_subbab_dinamis_mengambil_judul_dari_rumusan_masalah():
    variant = format_spec.get_variant("D")
    sections = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        _sub("Latar Belakang", "Latar belakang masalah."),
        _sub("Rumusan Masalah", (
            "1. Bagaimana peran inovasi teknologi?\\n"
            "2. Faktor apa yang mempengaruhi adopsi?\\n"
            "3. Bagaimana bentuk hubungan penyuluhan dan implementasi Jajar Legowo?\\n"
            "4. Apa saja tantangan integrasi teknologi?"
        )),
        _sub("Tujuan", "1. Tujuan satu.\\n2. Tujuan dua.\\n3. Tujuan tiga.\\n4. Tujuan empat."),
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
'''

content += new_test
p.write_text(content, encoding="utf-8")
print("Added dynamic subheading test to test_format_spec.py")
