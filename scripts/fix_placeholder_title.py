from pathlib import Path

p = Path("src/generator/document/renderer.py")
content = p.read_text(encoding="utf-8")

old_start = '''def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    cleaned = placeholders.clean_text(str(title or ""))'''

new_start = '''def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    raw = str(title or "").strip()
    if raw.startswith("{{") and raw.endswith("}}"):
        return raw
    cleaned = placeholders.clean_text(raw)'''

content = content.replace(old_start, new_start)
p.write_text(content, encoding="utf-8")
print("Updated _academic_title_case to preserve {{...}}")
