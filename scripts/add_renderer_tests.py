from pathlib import Path

p = Path("tests/test_renderer.py")
content = p.read_text(encoding="utf-8")

new_tests = '''

def test_judul_cover_otomatis_title_case(tmp_path):
    sections = [Section(1, "Bab Satu", [Paragraph([Sentence("Isi bab.", "x", [0])])])]
    fields = {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS}
    fields["{{JUDUL}}"] = "dampak inovasi teknologi pada pertanian"
    fields["{{DOSEN}}"] = "Dr. Ir. Soetomo, M.P."
    out = renderer.render_report(
        _tmpl(tmp_path), fields, sections, [], None, tmp_path / "title_case.docx"
    )
    text = "\\n".join(p.text for p in Document(out).paragraphs)
    assert "Dampak Inovasi Teknologi pada Pertanian" in text


def test_dosen_pengampu_dihapus_jika_kosong(tmp_path):
    doc = Document()
    doc.add_paragraph("{{JUDUL}}")
    doc.add_paragraph("{{NAMA}}")
    doc.add_paragraph("{{NIM}}")
    doc.add_paragraph("{{MATA_KULIAH}}")
    doc.add_paragraph("Dosen Pengampu:")
    doc.add_paragraph("{{DOSEN}}")
    doc.add_paragraph("{{TANGGAL}}")
    doc.add_paragraph("{{DAFTAR_ISI}}")
    doc.add_paragraph("{{LOGO}}")
    doc.add_paragraph("{{ISI_LAPORAN}}")
    doc.add_paragraph("{{DAFTAR_PUSTAKA}}")
    tmpl_path = tmp_path / "tmpl_dosen.docx"
    doc.save(tmpl_path)

    sections = [Section(1, "Bab Satu", [Paragraph([Sentence("Isi.", "x", [0])])])]
    fields = {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS}
    fields["{{DOSEN}}"] = ""
    fields["DOSEN"] = ""
    out = renderer.render_report(
        tmpl_path, fields, sections, [], None, tmp_path / "no_dosen.docx"
    )
    paragraphs = [p.text.strip() for p in Document(out).paragraphs]
    assert not any("Dosen Pengampu:" in p for p in paragraphs)
    assert not any("Dosen Pembimbing:" in p for p in paragraphs)

    # Bila diisi, label dan nama dosen tetap muncul
    fields["{{DOSEN}}"] = "Prof. Dr. Ir. Budi"
    fields["DOSEN"] = "Prof. Dr. Ir. Budi"
    out2 = renderer.render_report(
        tmpl_path, fields, sections, [], None, tmp_path / "with_dosen.docx"
    )
    paragraphs2 = [p.text.strip() for p in Document(out2).paragraphs]
    assert any("Dosen Pengampu:" in p for p in paragraphs2)
    assert any("Prof. Dr. Ir. Budi" in p for p in paragraphs2)
'''

content = content + new_tests
p.write_text(content, encoding="utf-8")
print("Added unit tests for title case and dosen pengampu")
