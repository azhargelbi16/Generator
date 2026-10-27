from pathlib import Path

p = Path("src/generator/document/renderer.py")
content = p.read_text(encoding="utf-8")
bad = 'core = word.strip("()[]:;,.!?"\'\-")'
# Let's inspect around line 334
lines = content.splitlines(True)
for i, line in enumerate(lines):
    if "core = word.strip" in line:
        lines[i] = '        core = word.strip("()[]:;,.!?\'\\"\\-")\n'
p.write_text("".join(lines), encoding="utf-8")
print("Fixed line in renderer.py")
