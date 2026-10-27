from pathlib import Path

# 1. Update src/generator/format_spec.py
p_spec = Path("src/generator/format_spec.py")
content = p_spec.read_text(encoding="utf-8")

# Expand _CLAUSE_MARKERS
old_clause = '''_CLAUSE_MARKERS = frozenset({
    "yang", "telah", "adalah", "dapat", "dalam", "karena", "sehingga", "agar",
    "dengan", "merupakan", "berfungsi", "menjadi",
    "memberikan", "memfasilitasi", "mendorong", "meningkatkan", "menyebabkan",
    "mempengaruhi", "memiliki",
})'''

new_clause = '''_CLAUSE_MARKERS = frozenset({
    "yang", "telah", "adalah", "dapat", "dalam", "karena", "sehingga", "agar",
    "dengan", "merupakan", "berfungsi", "menjadi",
    "memberikan", "memfasilitasi", "mendorong", "meningkatkan", "menyebabkan",
    "mempengaruhi", "memiliki", "seperti", "bahwa", "yakni", "yaitu",
})'''

content = content.replace(old_clause, new_clause)

# Expand _FUNCTION_WORDS
old_func_words = '''_FUNCTION_WORDS = frozenset({
    "yang", "di", "ke", "dari", "dan", "atau", "pada", "dengan", "untuk",
    "serta", "adalah", "telah", "tidak", "juga", "masih", "akan", "dapat",
    "harus", "karena", "sehingga", "agar", "ini", "itu",
    "dalam", "sebagai", "terhadap", "bagi", "oleh", "antara", "selama",
    "hingga", "sampai", "maupun", "tetapi", "namun", "bahwa", "berbagai",
    "banyak", "sebuah", "seorang", "para",
})'''

new_func_words = '''_FUNCTION_WORDS = frozenset({
    "yang", "di", "ke", "dari", "dan", "atau", "pada", "dengan", "untuk",
    "serta", "adalah", "telah", "tidak", "juga", "masih", "akan", "dapat",
    "harus", "karena", "sehingga", "agar", "ini", "itu",
    "dalam", "sebagai", "terhadap", "bagi", "oleh", "antara", "selama",
    "hingga", "sampai", "maupun", "tetapi", "namun", "bahwa", "berbagai",
    "banyak", "sebuah", "seorang", "para", "seperti", "yakni", "yaitu",
    "diperkenalkan", "diterapkan", "dilakukan", "ditemukan", "disajikan",
})'''

content = content.replace(old_func_words, new_func_words)

# Prioritize rumusan_items for dynamic subbab in normalize_sections
old_norm_dynamic = '''                if not _title_valid(title):
                    # (i) frasa kata konten dari kalimat pertama isi section.
                    phrase = _sanitize_title(_content_phrase(first_text))
                    if _title_valid(phrase) and not _clashes(phrase):
                        title = phrase'''

new_norm_dynamic = '''                if not _title_valid(title):
                    # Khusus bab Pembahasan: prioritaskan derivasi judul dari Rumusan Masalah Bab 1
                    if ("PEMBAHASAN" in chapter.title.upper() or "PEMBAHASAN" in (current_parent or parent)) and rumusan_items:
                        r_idx = level3_counts.get(current_parent, level2_count)
                        if r_idx < len(rumusan_items):
                            derived = _heading_from_rumusan(rumusan_items[r_idx])
                            if derived and not _clashes(derived):
                                title = derived
                    if not _title_valid(title):
                        # (i) frasa kata konten dari kalimat pertama isi section.
                        phrase = _sanitize_title(_content_phrase(first_text))
                        if _title_valid(phrase) and not _clashes(phrase):
                            title = phrase'''

content = content.replace(old_norm_dynamic, new_norm_dynamic)
p_spec.write_text(content, encoding="utf-8")
print("format_spec.py updated!")

# 2. Update src/generator/ai/content.py
p_content = Path("src/generator/ai/content.py")
c_text = p_content.read_text(encoding="utf-8")

old_plan_loop = '''            if progress is not None:
                progress.batch_started(step_index, total_steps)
            messages = prompts.content_prompt(
                topic, sub_titles, sources, ref_chunks,
                variant=variant_spec.code if variant_spec is not None else None,
                context=context,
                chapter_focus=chap_title,
            )'''

new_plan_loop = '''            if progress is not None:
                progress.batch_started(step_index, total_steps)

            # Resolusi judul dinamis Bab 3 dari Rumusan Masalah Bab 1 yang telah dihasilkan
            effective_sub_titles = list(sub_titles)
            if "PEMBAHASAN" in chap_title.upper() and hasattr(format_spec, "_rumusan_items"):
                rumusan_items = format_spec._rumusan_items(sections)
                if rumusan_items:
                    resolved = []
                    for st in effective_sub_titles:
                        m = re.match(r"^\\s*(\\d+\\.\\d+)\\s*\\{?[Jj]awaban\\s+rumusan\\s+masalah\\s*(\\d*)\\}?", st)
                        if m:
                            num_str = m.group(1)
                            idx_str = m.group(2)
                            idx = (int(idx_str) - 1) if idx_str else (int(num_str.split(".")[-1]) - 1)
                            if 0 <= idx < len(rumusan_items):
                                heading = format_spec._heading_from_rumusan(rumusan_items[idx])
                                resolved.append(f"{num_str} {heading}")
                            else:
                                resolved.append(st)
                        else:
                            resolved.append(st)
                    effective_sub_titles = resolved

            messages = prompts.content_prompt(
                topic, effective_sub_titles, sources, ref_chunks,
                variant=variant_spec.code if variant_spec is not None else None,
                context=context,
                chapter_focus=chap_title,
            )'''

c_text = c_text.replace(old_plan_loop, new_plan_loop)
p_content.write_text(c_text, encoding="utf-8")
print("content.py updated with dynamic sub_titles resolution!")
