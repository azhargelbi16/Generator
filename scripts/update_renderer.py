from pathlib import Path

p = Path("src/generator/document/renderer.py")
content = p.read_text(encoding="utf-8")

# 1. Update TOC_FIELD_XML to remove instructional text
old_toc = (
    f'<w:r><w:fldChar w:fldCharType="separate"/></w:r>\n'
    f'    "<w:r><w:t>Klik kanan di sini lalu pilih Update Field untuk memperbarui daftar isi.</w:t></w:r>"\n'
    f'    \'<w:r><w:fldChar w:fldCharType="end"/></w:r>\''
)
new_toc = (
    f'<w:r><w:fldChar w:fldCharType="separate"/></w:r>\n'
    f'    \'<w:r><w:fldChar w:fldCharType="end"/></w:r>\''
)

if old_toc in content:
    content = content.replace(old_toc, new_toc)
else:
    # try CRLF version
    old_toc_crlf = old_toc.replace('\n', '\r\n')
    new_toc_crlf = new_toc.replace('\n', '\r\n')
    if old_toc_crlf in content:
        content = content.replace(old_toc_crlf, new_toc_crlf)
    else:
        print("Warning: TOC_FIELD_XML pattern not matched directly, checking regex")
        import re
        content = re.sub(
            r'<w:r><w:t>Klik kanan di sini lalu pilih Update Field untuk memperbarui daftar isi\.</w:t></w:r>(\r?\n\s*)',
            '',
            content
        )

# 2. Add _academic_title_case helper before render_report
title_helper = '''
_TITLE_MINOR_WORDS = frozenset({
    "dan", "atau", "tetapi", "namun", "serta", "maupun", "yang", "di", "ke",
    "dari", "untuk", "pada", "dalam", "dengan", "sebagai", "terhadap", "bagi",
    "oleh", "karena", "agar", "antara", "selama", "hingga", "sampai", "tentang",
})


def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    words = str(title or "").split()
    if not words:
        return str(title or "")
    cased: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]:;,.!?\"'-")
        if not core:
            cased.append(word)
        elif len(core) >= 2 and core.isupper():
            cased.append(word)  # akronim tetap kapital
        elif index > 0 and core.casefold() in _TITLE_MINOR_WORDS:
            cased.append(word.lower())
        else:
            lowered = word.lower()
            for pos, char in enumerate(lowered):
                if char.isalpha():
                    cased.append(lowered[:pos] + char.upper() + lowered[pos + 1:])
                    break
            else:
                cased.append(word)
    return " ".join(cased)
'''

if "def _academic_title_case" not in content:
    content = content.replace("def render_report(", title_helper.strip() + "\n\n\ndef render_report(")

# 3. Apply title case to JUDUL and handle empty DOSEN in render_report
old_mapping_block = '''        value = str(raw_value or "")
        mapping[braced] = value
        mapping[bare] = value'''

new_mapping_block = '''        value = str(raw_value or "")
        if bare.upper() == "JUDUL":
            value = _academic_title_case(value)
        mapping[braced] = value
        mapping[bare] = value'''

content = content.replace(old_mapping_block, new_mapping_block)

# 4. Handle empty DOSEN removal
old_doc_setup = '''    if update_fields:
        _enable_update_fields(doc)'''

new_doc_setup = '''    if update_fields:
        _enable_update_fields(doc)

    has_dosen = bool(str(fields.get("DOSEN") or "").strip() or str(fields.get("{{DOSEN}}") or "").strip())
    if not has_dosen:
        for p in list(placeholders.iter_paragraphs(doc)):
            p_text = p.text.strip().casefold()
            if p_text in ("dosen pengampu:", "dosen pembimbing:", "dosen pengampu", "dosen pembimbing"):
                _remove_paragraph(p)
            elif p_text == "{{dosen}}":
                _remove_paragraph(p)'''

content = content.replace(old_doc_setup, new_doc_setup)

p.write_text(content, encoding="utf-8")
print("renderer.py successfully updated!")
