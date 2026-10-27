from pathlib import Path

p = Path("src/generator/format_spec.py")
content = p.read_text(encoding="utf-8")

content = content.replace(
    "r_idx = level3_counts.get(current_parent, level2_count)",
    "r_idx = (level3_counts.get(current_parent, 0) if entry.level == 3 else level2_count)"
)

p.write_text(content, encoding="utf-8")
print("Fixed r_idx in format_spec.py")
