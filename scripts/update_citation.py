from pathlib import Path

p = Path("src/generator/ai/citation.py")
content = p.read_text(encoding="utf-8")

known_acronyms_code = '''
_KNOWN_ACRONYMS = frozenset({
    "AI", "IOT", "GPS", "GIS", "CNN", "RNN", "LSTM", "SVM", "ANN",
    "FAO", "WHO", "UNESCO", "PBB", "BPS", "USA", "UK", "EU", "COVID-19",
    "DNA", "RNA", "NPK", "PH", "GPA",
})
'''

if "_KNOWN_ACRONYMS" not in content:
    content = content.replace("_TITLE_PROPER_NOUN_CANON = {name.casefold(): name for name in _TITLE_PROPER_NOUNS}",
                              "_TITLE_PROPER_NOUN_CANON = {name.casefold(): name for name in _TITLE_PROPER_NOUNS}" + known_acronyms_code)

old_sentence_case = '''def _sentence_case_title(title: str) -> str:
    """Judul artikel gaya sentence case APA 7 secara deterministik.

    Semua kata dihuruf-kecilkan KECUALI (i) kata pertama judul, (ii) kata
    pertama setelah titik dua, (iii) akronim (kata yang SEMULA seluruhnya
    kapital >= 2 huruf, mis. GPA/COVID-19), dan (iv) nama diri pada daftar
    putih. Tanda kutip dan tanda baca di tepi kata dipertahankan.
    """
    words = str(title or "").split()
    cased: list[str] = []
    at_sentence_start = True
    for word in words:
        core = word.strip(_TITLE_EDGE_PUNCT)
        if not core:
            cased.append(word)
            at_sentence_start = False
            continue
        start = word.find(core)
        prefix, suffix = word[:start], word[start + len(core):]
        if _is_uppercase_acronym(core):
            body = core
        elif core.casefold() in _TITLE_PROPER_NOUN_CANON:
            body = _TITLE_PROPER_NOUN_CANON[core.casefold()]
        elif at_sentence_start:
            body = _capitalize_first_alpha(core.lower())
        else:
            body = core.lower()
        cased.append(prefix + body + suffix)
        at_sentence_start = word.rstrip().endswith(":")
    return " ".join(cased)'''

new_sentence_case = '''def _sentence_case_title(title: str) -> str:
    """Judul artikel gaya sentence case APA 7 secara deterministik.

    Semua kata dihuruf-kecilkan KECUALI (i) kata pertama judul, (ii) kata
    pertama setelah titik dua, (iii) akronim (kata yang SEMULA seluruhnya
    kapital >= 2 huruf, mis. GPA/COVID-19), dan (iv) nama diri pada daftar
    putih. Bila seluruh judul berasal dari header jurnal yang ALL CAPS, kata-kata
    dikonversi ke huruf kecil terlebih dahulu kecuali akronim baku.
    Tanda kutip dan tanda baca di tepi kata dipertahankan.
    """
    words = str(title or "").split()
    if not words:
        return ""

    # Deteksi bila judul secara dominan berupa ALL CAPS (dari header jurnal)
    alpha_words = [w.strip(_TITLE_EDGE_PUNCT) for w in words if any(c.isalpha() for c in w)]
    caps_count = sum(1 for w in alpha_words if len(w) >= 2 and w.isupper())
    is_all_caps_title = len(alpha_words) >= 3 and (caps_count / len(alpha_words)) >= 0.6

    cased: list[str] = []
    at_sentence_start = True
    for word in words:
        core = word.strip(_TITLE_EDGE_PUNCT)
        if not core:
            cased.append(word)
            at_sentence_start = False
            continue
        start = word.find(core)
        prefix, suffix = word[:start], word[start + len(core):]
        if is_all_caps_title:
            if core.upper() in _KNOWN_ACRONYMS:
                body = core.upper()
            elif core.casefold() in _TITLE_PROPER_NOUN_CANON:
                body = _TITLE_PROPER_NOUN_CANON[core.casefold()]
            elif at_sentence_start:
                body = _capitalize_first_alpha(core.lower())
            else:
                body = core.lower()
        else:
            if _is_uppercase_acronym(core):
                body = core
            elif core.casefold() in _TITLE_PROPER_NOUN_CANON:
                body = _TITLE_PROPER_NOUN_CANON[core.casefold()]
            elif at_sentence_start:
                body = _capitalize_first_alpha(core.lower())
            else:
                body = core.lower()
        cased.append(prefix + body + suffix)
        at_sentence_start = word.rstrip().endswith(":")
    return " ".join(cased)'''

content = content.replace(old_sentence_case, new_sentence_case)
p.write_text(content, encoding="utf-8")
print("citation.py updated successfully!")
