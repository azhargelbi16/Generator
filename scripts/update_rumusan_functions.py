from pathlib import Path

p = Path("src/generator/format_spec.py")
content = p.read_text(encoding="utf-8")

old_block = '''_RUMUSAN_PREFIX_RE = re.compile(
    r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?"
    r"(?:bagaimana(?:kah)?|apakah|apa(?:kah)?|sejauh\s+mana(?:kah)?|mengapa(?:kah)?|why|how)\s+",
    re.IGNORECASE,
)


def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        if "rumusan masalah" not in str(section.title or "").casefold():
            continue
        for paragraph in section.paragraphs:
            text = " ".join(s.text for s in paragraph.sentences).strip()
            if not text:
                continue
            match = re.match(r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?(.*)$", text)
            body = (match.group(1).strip() if match else text)
            if body:
                items.append(body)
    return items


def _heading_from_rumusan(text: str, limit: int = 90) -> str:
    """Ubah butir pertanyaan menjadi judul subbab singkat."""
    heading = _RUMUSAN_PREFIX_RE.sub("", str(text or "").strip()).rstrip(" ?.!").strip()
    if not heading:
        heading = str(text or "").strip().rstrip(" ?.!")
    heading = " ".join(heading.split())
    if len(heading) > limit:
        heading = heading[:limit].rsplit(" ", 1)[0] + " …"
    return heading[:1].upper() + heading[1:] if heading else ""'''

new_block = '''_RUMUSAN_PREFIX_RE = re.compile(
    r"^\s*(?:\d+[.)]\s*|[a-z][.)]\s*)?"
    r"(?:bagaimana(?:kah)?|apakah|apa(?:kah)?(?:\s+saja)?|sejauh\s+mana(?:kah)?|mengapa(?:kah)?|why|how)\s+",
    re.IGNORECASE,
)


def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        if "rumusan masalah" not in str(section.title or "").casefold():
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
    return items


def _heading_from_rumusan(text: str, limit: int = 90) -> str:
    """Ubah butir pertanyaan menjadi judul subbab singkat."""
    heading = _RUMUSAN_PREFIX_RE.sub("", str(text or "").strip()).rstrip(" ?.!").strip()
    if not heading:
        heading = str(text or "").strip().rstrip(" ?.!")
    heading = " ".join(heading.split())
    if len(heading) > limit:
        heading = heading[:limit].rsplit(" ", 1)[0] + " …"
    return _title_case(heading) if heading else ""'''

content = content.replace(old_block, new_block)
p.write_text(content, encoding="utf-8")
print("Updated rumusan functions in format_spec.py")
