from pathlib import Path

p = Path("src/generator/document/renderer.py")
content = p.read_text(encoding="utf-8")

old_func_start = "def _academic_title_case(title: str) -> str:"
old_func_end = "return \" \".join(cased)"

start_idx = content.find(old_func_start)
end_idx = content.find(old_func_end, start_idx) + len(old_func_end)

new_func = '''def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    cleaned = placeholders.clean_text(str(title or ""))
    words = cleaned.split()
    if not words:
        return cleaned
    letters = [c for c in cleaned if c.isalpha()]
    all_caps = bool(letters) and all(c.isupper() for c in letters)
    cased: list[str] = []
    for index, word in enumerate(words):
        core = word.strip('()[]:;,.!?"\\'-')
        if not core:
            cased.append(word)
        elif len(core) >= 2 and core.isupper() and not all_caps:
            cased.append(word)  # akronim tetap kapital
        elif not all_caps and any(c.isupper() for c in core[1:]):
            cased.append(word)  # kata berkapital internal (LaporanX, iPhone) dipertahankan
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
    return " ".join(cased)'''

content = content[:start_idx] + new_func + content[end_idx:]
p.write_text(content, encoding="utf-8")
print("Replaced _academic_title_case")
