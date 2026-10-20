import base64
from docx import Document
from docx.shared import Cm
from generator.document import renderer, template
from generator.ai.content import Sentence, Paragraph, Section


def _tmpl(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    for ph in template.REQUIRED_PLACEHOLDERS:
        d.add_paragraph(ph)
    d.save(p)
    return p


def _png(path, w, h):
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    path.write_bytes(png)
    return path


def test_render_fills_fields_and_body(tmp_path):
    secs = [Section(1, "Pendahuluan", [Paragraph([Sentence("Isi bab.", "x", [0])])])]
    out = renderer.render_report(_tmpl(tmp_path),
        {"{{JUDUL}}": "Laporan X", "{{NAMA}}": "Budi", "{{NIM}}": "1",
         "{{MATA_KULIAH}}": "Agro", "{{DOSEN}}": "Dr. X", "{{TANGGAL}}": "2026"},
        secs, ["Santoso, B. (2020)."], None, tmp_path / "out.docx")
    doc = Document(out)
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Laporan X" in text and "{{" not in text
    assert "Pendahuluan" in text and "Isi bab." in text and "Santoso, B. (2020)." in text
    assert any(p.style.name == "Heading 1" for p in doc.paragraphs)


def test_render_places_citations_from_labels(tmp_path):
    secs = [Section(1, "Bab", [Paragraph([Sentence("Pertanian organik meningkat pesat di Indonesia.", "q", [0])])])]
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 secs, ["Santoso, B. (2020)."], None, tmp_path / "o.docx",
                                 labels={0: "(Santoso, 2020)"})
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert "Pertanian organik meningkat pesat di Indonesia (Santoso, 2020)." in text


def test_toc_field_present(tmp_path):
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], None, tmp_path / "o.docx")
    assert "TOC" in Document(out).element.xml


def test_special_placeholder_keys_in_fields_ignored(tmp_path):
    logo = _png(tmp_path / "l.png", 1, 1)
    fields = {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS}
    out = renderer.render_report(_tmpl(tmp_path), fields, [], [], logo, tmp_path / "o.docx")
    doc = Document(out)
    assert len(doc.inline_shapes) == 1
    assert "TOC" in doc.element.xml


def test_logo_square_is_5cm(tmp_path):
    logo = _png(tmp_path / "l.png", 1, 1)
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], logo, tmp_path / "o.docx")
    shape = Document(out).inline_shapes[0]
    assert shape.width == Cm(5) and shape.height == Cm(5)


def test_logo_non_square_fits_within_5cm(tmp_path):
    from PIL import Image
    logo = tmp_path / "wide.png"; Image.new("RGB", (200, 100), "black").save(logo)
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], logo, tmp_path / "o.docx")
    shape = Document(out).inline_shapes[0]
    assert shape.width == Cm(5) and shape.height <= Cm(5)


def test_bad_logo_skipped(tmp_path):
    bad = tmp_path / "l.txt"; bad.write_text("nope")
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], bad, tmp_path / "o.docx")
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert out.exists() and "{{LOGO}}" not in text and "nope" not in text


def test_missing_heading_style_falls_back(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    st = d.styles["Heading 1"].element
    st.getparent().remove(st)
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.save(p)
    secs = [Section(1, "Bab Tanpa Style", [Paragraph([Sentence("Isi bab.", "x", [0])])])]
    out = renderer.render_report(p, {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                  secs, [], None, tmp_path / "o.docx")
    text = "\n".join(par.text for par in Document(out).paragraphs)
    assert "Bab Tanpa Style" in text and "Isi bab." in text


def test_missing_optional_placeholder_is_blanked(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.add_paragraph("Tahun {{TAHUN}} prodi {{PRODI}}")
    d.save(p)
    out = renderer.render_report(p, {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], None, tmp_path / "o.docx")
    text = "\n".join(par.text for par in Document(out).paragraphs)
    assert "{{" not in text and "Tahun" in text and "prodi" in text


def test_references_hanging_indent(tmp_path):
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], ["Santoso, B. (2020)."], None, tmp_path / "o.docx")
    doc = Document(out)
    ref = [p for p in doc.paragraphs if "Santoso, B. (2020)." in p.text][0]
    assert ref.paragraph_format.left_indent is not None
    assert ref.paragraph_format.first_line_indent is not None
    assert ref.paragraph_format.first_line_indent < 0


# --- Task 1.7: updateFields Word ---------------------------------------------


def _settings_xml(path) -> str:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        return archive.read("word/settings.xml").decode("utf-8")


def test_update_fields_true_menambah_flag_update_fields(tmp_path):
    out = renderer.render_report(
        _tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
        [], [], None, tmp_path / "o.docx", update_fields=True,
    )
    assert 'w:updateFields w:val="true"' in _settings_xml(out)


def test_update_fields_default_tanpa_flag(tmp_path):
    out = renderer.render_report(
        _tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
        [], [], None, tmp_path / "o.docx",
    )
    assert "updateFields" not in _settings_xml(out)

