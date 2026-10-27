from pathlib import Path

p = Path("src/generator/format_spec.py")
content = p.read_text(encoding="utf-8")

old_code = '''def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        if "rumusan masalah" not in str(section.title or "").casefold():
            continue'''

new_code = '''def _rumusan_items(sections) -> list[str]:
    """Ambil butir Rumusan Masalah dari Bab 1 (untuk judul pembahasan cadangan)."""
    items: list[str] = []
    for section in sections:
        t_clean = str(section.title or "").casefold()
        if "rumusan masalah" not in t_clean or "jawaban" in t_clean:
            continue'''

content = content.replace(old_code, new_code)
p.write_text(content, encoding="utf-8")
print("Updated _rumusan_items in format_spec.py")
