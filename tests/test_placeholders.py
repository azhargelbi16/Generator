from docx import Document
from generator.document import placeholders


def test_replaces_split_runs_and_keeps_neighbours():
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("A {{JU")
    p.add_run("DUL}} B")
    replaced = placeholders.replace_in_paragraph(p, {"{{JUDUL}}": "X"})
    assert replaced == ["{{JUDUL}}"]
    assert p.text == "A X B"


def test_multiple_placeholders_one_paragraph():
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("{{NAMA}} dan {{NIM}}")
    placeholders.replace_in_paragraph(p, {"{{NAMA}}": "Budi", "{{NIM}}": "1"})
    assert p.text == "Budi dan 1"


def test_is_standalone():
    doc = Document()
    a = doc.add_paragraph("{{LOGO}}")
    a.add_run("")
    b = doc.add_paragraph("lihat {{LOGO}} ini")
    assert placeholders.is_standalone(a, "{{LOGO}}") is True
    assert placeholders.is_standalone(b, "{{LOGO}}") is False


def test_collect_names_includes_table_cells():
    doc = Document()
    t = doc.add_table(rows=1, cols=1)
    t.cell(0, 0).paragraphs[0].add_run("{{DOSEN}}")
    assert "{{DOSEN}}" in placeholders.collect_names(doc)
