from pathlib import Path

p = Path("src/generator/document/renderer.py")
content = p.read_text(encoding="utf-8")

old_func = '''def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    words = str(title or "").split()
    if not words:
        return str(title or "")
    cased: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]:;,.!?\'\\"\\-")
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
    return " ".join(cased)'''

new_func = '''def _academic_title_case(title: str) -> str:
    """Kapitalisasi judul akademik formal (Title Case)."""
    cleaned = placeholders.clean_text(str(title or ""))
    words = cleaned.split()
    if not words:
        return cleaned
    cased: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]:;,.!?\'\"-")
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
    return " ".join(cased)'''

content = content.replace(old_func, new_func)
p.write_text(content, encoding="utf-8")
print("Updated _academic_title_case in renderer.py")
