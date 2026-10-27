from pathlib import Path

p = Path("tests/test_citation.py")
content = p.read_text(encoding="utf-8")

new_test = '''

def test_sentence_case_menormalkan_judul_all_caps_dari_pdf():
    from generator.ai.citation import Source, Author, reference
    src = Source(
        [Author("Putra", "Rizki Aditya"), Author("Sadono", "Dwi")],
        "2024",
        "EXAMINING THE RELATIONSHIP BETWEEN INNOVATION CHARACTERISTICS AND EXTENSION SUPPORT WHEN USING JAJAR LEGOWO AS AN AGRICULTURAL INNOVATION",
        "Jurnal AGRISEP: Kajian Masalah Sosial Ekonomi Pertanian dan Agribisnis",
    )
    ref = reference(src)
    assert "Examining the relationship between innovation characteristics and extension support when using jajar legowo as an agricultural innovation." in ref
    assert "Jurnal AGRISEP: Kajian Masalah Sosial Ekonomi Pertanian dan Agribisnis." in ref
'''

content += new_test
p.write_text(content, encoding="utf-8")
print("Added all-caps test to test_citation.py")
