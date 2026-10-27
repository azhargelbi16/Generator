from pathlib import Path

p = Path("src/generator/format_spec.py")
content = p.read_text(encoding="utf-8")

old_code = '''def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        t_clean = str(section.title or "").casefold()
        if "rumusan masalah" not in t_clean or "jawaban" in t_clean:
            continue
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                text = sentence.text.strip()
                if not text:
                    continue
                match = re.match(r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?(.*)$", text)
                body = match.group(1).strip() if match else text
                if body:
                    items.append(body)
    return items'''

new_code = '''def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        t_clean = str(section.title or "").casefold()
        if "rumusan masalah" not in t_clean or "jawaban" in t_clean:
            continue
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                for line in sentence.text.splitlines():
                    text = line.strip()
                    if not text:
                        continue
                    match = re.match(r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?(.*)$", text)
                    body = match.group(1).strip() if match else text
                    if body:
                        items.append(body)
    return items'''

content = content.replace(old_code, new_code)
p.write_text(content, encoding="utf-8")
print("Updated _rumusan_items with splitlines support in format_spec.py")
