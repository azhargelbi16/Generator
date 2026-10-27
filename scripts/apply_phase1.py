import docx
from pathlib import Path

# 1. Update src/generator/web/api_bridge.py
path_bridge = Path('src/generator/web/api_bridge.py')
text = path_bridge.read_text(encoding='utf-8')
text = text.replace('Dosen Pembimbing:', 'Dosen Pengampu:')
text = text.replace('dosen pembimbing akademik senior', 'dosen pengampu mata kuliah senior')
path_bridge.write_text(text, encoding='utf-8')
print("api_bridge.py updated")

# 2. Update src/generator/web/contract.py
path_contract = Path('src/generator/web/contract.py')
if path_contract.exists():
    text = path_contract.read_text(encoding='utf-8')
    text = text.replace('Daftar dosen pembimbing', 'Daftar dosen pengampu')
    text = text.replace('dosen pembimbing', 'dosen pengampu')
    path_contract.write_text(text, encoding='utf-8')
    print("contract.py updated")

# 3. Update src/generator/ai/dosen.py
path_dosen = Path('src/generator/ai/dosen.py')
if path_dosen.exists():
    text = path_dosen.read_text(encoding='utf-8')
    text = text.replace('dosen pembimbing', 'dosen pengampu')
    text = text.replace('Dosen Pembimbing', 'Dosen Pengampu')
    text = text.replace('pembimbing cerewet', 'pengampu teliti')
    text = text.replace('ditanyakan pembimbing', 'ditanyakan dosen pengampu')
    path_dosen.write_text(text, encoding='utf-8')
    print("dosen.py updated")

# 4. Update data/templates/Template_Standar_Akademik.docx
path_tpl = Path('data/templates/Template_Standar_Akademik.docx')
if path_tpl.exists():
    doc = docx.Document(path_tpl)
    replaced = False
    for p in doc.paragraphs:
        if 'Dosen Pembimbing:' in p.text:
            p.text = p.text.replace('Dosen Pembimbing:', 'Dosen Pengampu:')
            replaced = True
    if replaced:
        doc.save(path_tpl)
        print("Template_Standar_Akademik.docx updated to 'Dosen Pengampu:'")

# 5. Update frontend components
path_laporan = Path('frontend/src/components/TabLaporan.tsx')
if path_laporan.exists():
    text = path_laporan.read_text(encoding='utf-8')
    text = text.replace('Dosen Pembimbing', 'Dosen Pengampu')
    path_laporan.write_text(text, encoding='utf-8')
    print("TabLaporan.tsx updated")

path_tabdata = Path('frontend/src/components/TabData.tsx')
if path_tabdata.exists():
    text = path_tabdata.read_text(encoding='utf-8')
    text = text.replace('Dosen Pembimbing/Pengampu', 'Dosen Pengampu')
    text = text.replace('Dosen Pembimbing', 'Dosen Pengampu')
    path_tabdata.write_text(text, encoding='utf-8')
    print("TabData.tsx updated")
