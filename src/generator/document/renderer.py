"""Renderer DOCX: isi penanda, logo 5x5 cm, field TOC, heading berlevel, hanging indent (18, 20)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Cm, Emu
from docx.text.paragraph import Paragraph as DocxParagraph

from ..ai import content
from ..logging_setup import get_logger
from . import placeholders, template

_log = get_logger("renderer")

TOC_FIELD_XML = (
    f"<w:p {nsdecls('w')}>"
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-9" \\h \\z \\u </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    "<w:r><w:t>Klik kanan di sini lalu pilih Update Field untuk memperbarui daftar isi.</w:t></w:r>"
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    "</w:p>"
)

_LOGO_BOX = Cm(5)
_HANGING = Cm(1.27)
_MAX_HEADING_LEVEL = 9


def _heading_style(doc, level: int) -> str:
    """Nama style Heading yang aman dipakai; dibuat bila template tidak memilikinya (18.1)."""
    level = min(max(level, 1), _MAX_HEADING_LEVEL)
    name = f"Heading {level}"
    if name in doc.styles:
        return name
    try:
        style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = doc.styles["Normal"]
        style.font.bold = True
        return name
    except Exception:
        return "Normal"


def _insert_paragraph_before(anchor: DocxParagraph, text: str = "", style: str | None = None) -> DocxParagraph:
    new_p = OxmlElement("w:p")
    anchor._p.addprevious(new_p)
    paragraph = DocxParagraph(new_p, anchor._parent)
    if style:
        paragraph.style = style
    if text:
        paragraph.add_run(placeholders.clean_text(text))
    return paragraph


def _remove_paragraph(paragraph: DocxParagraph) -> None:
    element = paragraph._p
    element.getparent().remove(element)


def _clear_runs(paragraph: DocxParagraph) -> None:
    for run in paragraph.runs:
        run.text = ""


def _logo_size(logo_path: Path) -> tuple[Emu, Emu]:
    """Skala agar masuk kotak 5x5 cm tanpa memotong, rasio asli terjaga.

    Orientasi EXIF diterapkan lebih dulu: foto ponsel sering tersimpan miring
    dan Word memakai dimensi setelah rotasi.
    """
    from PIL import Image, ImageOps

    with Image.open(logo_path) as image:
        width, height = ImageOps.exif_transpose(image).size
    if width <= 0 or height <= 0:
        raise ValueError("ukuran gambar tidak valid")
    scale = min(_LOGO_BOX / width, _LOGO_BOX / height)
    return Emu(int(round(width * scale))), Emu(int(round(height * scale)))


def _place_logo(paragraph: DocxParagraph, logo_path: Path | None) -> None:
    _clear_runs(paragraph)
    if logo_path is None:
        return
    try:
        width, height = _logo_size(logo_path)
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        run.add_picture(str(logo_path), width=width, height=height)
    except Exception as error:
        _log.warning("Logo dilewati karena tidak bisa dimuat (%s): %s", logo_path, error)
        _clear_runs(paragraph)
        return
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _place_toc(paragraph: DocxParagraph) -> None:
    paragraph._p.addprevious(parse_xml(TOC_FIELD_XML))
    _remove_paragraph(paragraph)


def _enable_update_fields(doc) -> None:
    """Minta Word memperbarui field (daftar isi) saat dokumen pertama dibuka."""
    from docx.oxml.ns import qn

    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is not None:
        return
    element = OxmlElement("w:updateFields")
    element.set(qn("w:val"), "true")
    # Skema OOXML menuntut updateFields sebelum compat/rsids; Word mengabaikannya bila urutannya salah.
    compat = settings.find(qn("w:compat"))
    if compat is not None:
        compat.addprevious(element)
    else:
        settings.append(element)


def _place_body(doc, paragraph: DocxParagraph, sections, labels, label_forms=None) -> None:
    defined: set[int] = set()
    for i, section in enumerate(sections):
        heading_style = _heading_style(doc, section.level)
        heading = _insert_paragraph_before(paragraph, section.title, heading_style)
        if heading_style == "Normal":
            for run in heading.runs:
                run.bold = True

        # Cegah duplikasi teks jika bab level 1 memiliki paragraf yang sama persis
        # dengan subbab level 2 tepat di bawahnya (misal BAB 1 dan 1.1 Latar Belakang).
        paragraphs = section.paragraphs
        if section.level == 1 and i + 1 < len(sections) and sections[i + 1].level == 2:
            next_p = sections[i + 1].paragraphs
            if paragraphs and next_p:
                cur_texts = [s.text.strip() for p in paragraphs for s in p.sentences if s.text.strip()]
                next_texts = [s.text.strip() for p in next_p for s in p.sentences if s.text.strip()]
                if cur_texts and cur_texts == next_texts:
                    paragraphs = []

        for block in paragraphs:
            block_labels = labels
            if label_forms:
                # Kemunculan pertama memakai bentuk panjang, berikutnya bentuk pendek.
                block_labels = {
                    index: (pendek if index in defined else panjang)
                    for index, (panjang, pendek) in label_forms.items()
                }
            text = content.compose(block, block_labels)
            if text:
                _insert_paragraph_before(paragraph, text, "Normal")
            if label_forms:
                for sentence in block.sentences:
                    if sentence.is_factual and sentence.citation:
                        defined.update(sentence.source_ids)
    _remove_paragraph(paragraph)


def _place_references(paragraph: DocxParagraph, references: list[str]) -> None:
    for entry in references:
        item = _insert_paragraph_before(paragraph, entry, "Normal")
        item.paragraph_format.left_indent = _HANGING
        item.paragraph_format.first_line_indent = -_HANGING
    _remove_paragraph(paragraph)


def render_report(
    template_path: Path,
    fields: dict[str, str],
    sections: list,
    references: list[str],
    logo_path: Path | None,
    output_path: Path,
    labels: dict[int, str] | None = None,
    update_fields: bool = False,
    label_forms: dict[int, tuple[str, str]] | None = None,
) -> Path:
    doc = template.load_template(template_path)
    result = template.validate_document(doc)
    if not result.is_processable:
        detail: list[str] = []
        if result.missing:
            detail.append("penanda wajib tidak ada: " + ", ".join(result.missing))
        if result.not_standalone:
            detail.append(
                "penanda khusus harus berdiri sendiri: " + ", ".join(result.not_standalone)
            )
        raise template.TemplateError("Template tidak siap: " + "; ".join(detail))
    labels = labels or {}
    if update_fields:
        _enable_update_fields(doc)

    mapping = {key: value for key, value in fields.items() if key not in template.SPECIAL_PLACEHOLDERS}
    for name in template.OPTIONAL_PLACEHOLDERS:
        mapping.setdefault(name, "")

    # Penanda khusus diproses lebih dulu: nilai field bisa memuat teks yang
    # kebetulan sama dengan nama penanda khusus (mis. judul "{{ISI_LAPORAN}}").
    for paragraph in list(placeholders.iter_paragraphs(doc)):
        text = paragraph.text.strip()
        if text == "{{LOGO}}":
            _place_logo(paragraph, logo_path)
        elif text == "{{DAFTAR_ISI}}":
            _place_toc(paragraph)
        elif text == "{{ISI_LAPORAN}}":
            _place_body(doc, paragraph, sections, labels, label_forms)
        elif text == "{{DAFTAR_PUSTAKA}}":
            _place_references(paragraph, references)

    leftover = {name: "" for name in template.SPECIAL_PLACEHOLDERS}
    for paragraph in list(placeholders.iter_paragraphs(doc)):
        placeholders.replace_in_paragraph(paragraph, leftover)

    for paragraph in list(placeholders.iter_paragraphs(doc)):
        placeholders.replace_in_paragraph(paragraph, mapping)

    _save_atomic(doc, output_path)
    return output_path


def _save_atomic(doc, output_path: Path) -> None:
    """Simpan DOCX lewat berkas sementara; berkas lama tidak tersentuh bila gagal."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".docx", dir=output_path.parent
    )
    os.close(descriptor)
    try:
        doc.save(temporary)
        os.replace(temporary, output_path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
