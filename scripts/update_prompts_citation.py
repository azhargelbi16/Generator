from pathlib import Path

p = Path("src/generator/ai/prompts.py")
content = p.read_text(encoding="utf-8")

old_text = '"Jangan menulis sitasi di dalam teks; sitasi ditambahkan aplikasi dari source_ids. "'
new_text = (
    '"Jangan menulis sitasi di dalam teks; sitasi ditambahkan aplikasi dari source_ids. '
    'WAJIB SITASI DI BAB 2 DAN BAB 3: Seluruh subbab naratif pada BAB 2 (TINJAUAN PUSTAKA) dan BAB 3 (PEMBAHASAN) WAJIB mengutip sumber literatur (isi quote persis dan source_ids valid); DILARANG mengosongkan source_ids pada subbab tinjauan pustaka. "'
)

content = content.replace(old_text, new_text)
p.write_text(content, encoding="utf-8")
print("prompts.py updated with mandatory citation rule for Bab 2 & 3!")
