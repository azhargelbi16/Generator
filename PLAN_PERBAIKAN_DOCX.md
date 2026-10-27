# Rencana Implementasi Perbaikan Tata Letak Dokumen DOCX & Halaman Sampul

Dokumen ini memuat panduan teknis langkah demi langkah untuk merekayasa ulang modul perender dokumen (`renderer.py`) dan template laporan akademik (`api_bridge.py`), sehingga dokumen DOCX yang dihasilkan rapi, formal, dan memenuhi standar akademik perguruan tinggi di Indonesia.

---

## 1. Analisis Akar Masalah (Root Causes)

Berdasarkan inspeksi mendalam terhadap berkas keluaran `.docx` (`output/Laporan_AI_dan_Literasi_Data_Pertanian_20261025_121658.docx`):

1. **Placeholders Sampul Tidak Terganti**:
   * `renderer.render_report()` (`src/generator/document/renderer.py`) hanya menyalin kunci dari `fields`. Jika pemanggil mengirim kunci tanpa kurung kurawal ganda (misal `{"JUDUL": "..."}`), `placeholders.replace_in_paragraph()` (`src/generator/document/placeholders.py`) gagal mencocokkannya karena mencari pola `{{JUDUL}}`.
   * Akibatnya teks mentah `{{JUDUL}}`, `{{NAMA}}`, `{{NIM}}`, `{{DOSEN}}`, `{{MATA_KULIAH}}`, dan `{{TANGGAL}}` tetap tercetak apa adanya di sampul.
2. **Ketiadaan Halaman Baru (Page Break) Antar-Bab**:
   * `_place_body()` (`src/generator/document/renderer.py`) langsung menyisipkan heading Bab tanpa menambahkan *Page Break*. Seluruh bab bersambung di satu halaman yang sama.
3. **Format Paragraf Tubuh Dokumen Polos**:
   * Paragraf disisipkan dengan style `"Normal"` default yang rata kiri (tidak *Justified*), spasi tunggal (1.0), dan tanpa lekukan baris pertama (*first line indent*).
4. **Desain Sampul Bawaan Rusak / Bertumpuk**:
   * Seluruh identitas sampul di `_create_academic_template_docx()` (`src/generator/web/api_bridge.py`) dimuat ke dalam satu paragraf dengan 8 baris pemisah `<w:br/>` terpusat di tengah halaman.
   * Informasi institusi bawah (Program Studi, Fakultas, Universitas, dan Tahun) hilang dari template, padahal data profil tersedia di database SQLite.
5. **Lubang Vertikal Akibat Logo Kosong**:
   * Jika tidak ada logo, paragraf `{{LOGO}}` hanya dikosongkan teksnya namun menyisakan margin kosong 2 cm di tengah sampul.

---

## 2. Rencana Perubahan Berkas (Step-by-Step Action Plan)

### Langkah 1: Perbaikan Normalisasi Penanda & Layout pada `src/generator/document/renderer.py`

#### A. Normalisasi Penanda Otomatis (Dua Arah)
Pada fungsi `render_report()`, bangun `mapping` yang menjamin kunci selalu tersedia baik dalam bentuk kurung kurawal ganda maupun tanpa kurung:

```python
# Lokasi: src/generator/document/renderer.py -> render_report()
mapping: dict[str, str] = {}
for raw_k, val in fields.items():
    k = str(raw_k).strip()
    with_braces = k if k.startswith("{{") and k.endswith("}}") else f"{{{{{k}}}}}"
    without_braces = k[2:-2].strip() if k.startswith("{{") and k.endswith("}}") else k
    
    if with_braces not in template.SPECIAL_PLACEHOLDERS:
        mapping[with_braces] = str(val or "")
        mapping[without_braces] = str(val or "")

# Isi nilai default untuk penanda opsional bila belum ada
for name in template.OPTIONAL_PLACEHOLDERS:
    without = name[2:-2].strip()
    mapping.setdefault(name, "")
    mapping.setdefault(without, "")
```

#### B. Penghapusan Paragraf Logo Kosong
Perbarui fungsi `_place_logo()` agar jika `logo_path is None`, paragraf dihapus sepenuhnya dari dokumen alih-alih disisakan sebagai ruang kosong:

```python
def _place_logo(paragraph: DocxParagraph, logo_path: Path | None) -> None:
    if logo_path is None or not Path(logo_path).is_file():
        _remove_paragraph(paragraph)
        return
    try:
        width, height = _logo_size(logo_path)
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        run.add_picture(str(logo_path), width=width, height=height)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception as error:
        _log.warning("Logo dilewati karena tidak bisa dimuat (%s): %s", logo_path, error)
        _remove_paragraph(paragraph)
```

#### C. Page Break Otomatis Sebelum Heading Level 1 (Bab Baru) & Format Paragraf Akademik
Perbarui fungsi `_place_body()` agar:
1. Menambahkan *Page Break* sebelum Bab baru (kecuali Bab pertama yang sudah diawali oleh halaman pemisah dari template).
2. Menerapkan format tipografi akademik pada paragraf isi:
   * Perataan: `WD_ALIGN_PARAGRAPH.JUSTIFY` (Rata Kiri-Kanan)
   * Spasi Baris: `1.5`
   * Indentasi Baris Pertama: `Cm(1.0)` atau `Cm(1.27)`
   * Jarak Setelah Paragraf: `Pt(0)`

```python
def _place_body(doc, paragraph: DocxParagraph, sections, labels, label_forms=None) -> None:
    defined: set[int] = set()
    for i, section in enumerate(sections):
        # Berikan page break sebelum setiap Bab baru (level 1), kecuali bila bab pertama
        if section.level == 1 and i > 0:
            p_break = _insert_paragraph_before(paragraph, "", "Normal")
            p_break.paragraph_format.page_break_before = True

        heading_style = _heading_style(doc, section.level)
        heading = _insert_paragraph_before(paragraph, section.title, heading_style)
        if heading_style == "Normal":
            for run in heading.runs:
                run.bold = True
        
        # Format heading bab: Rata tengah untuk Level 1, Rata kiri untuk Subbab
        if section.level == 1:
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            heading.paragraph_format.space_before = Pt(12)
            heading.paragraph_format.space_after = Pt(12)
        else:
            heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
            heading.paragraph_format.space_before = Pt(12)
            heading.paragraph_format.space_after = Pt(6)

        for block in section.paragraphs:
            block_labels = labels
            if label_forms:
                block_labels = {
                    index: (pendek if index in defined else panjang)
                    for index, (panjang, pendek) in label_forms.items()
                }
            text = content.compose(block, block_labels)
            if text:
                p_body = _insert_paragraph_before(paragraph, text, "Normal")
                # Aturan tipografi akademik Indonesia:
                p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_body.paragraph_format.line_spacing = 1.5
                p_body.paragraph_format.first_line_indent = Cm(1.0)
                p_body.paragraph_format.space_after = Pt(0)
            
            if label_forms:
                for sentence in block.sentences:
                    if sentence.is_factual and sentence.citation:
                        defined.update(sentence.source_ids)

    _remove_paragraph(paragraph)
```

---

### Langkah 2: Desain Ulang Template Bawaan di `src/generator/web/api_bridge.py`

Perbarui fungsi `_create_academic_template_docx()` di `src/generator/web/api_bridge.py` agar menyusun halaman sampul standar Dikti / Universitas di Indonesia:

Struktur Sampul:
1. JUDUL LAPORAN (Huruf Kapital, Tebal 14–16 pt, Spasi 1.15)
2. KETERANGAN ("LAPORAN AKADEMIK")
3. `{{LOGO}}` (Ukuran 5x5 cm di Tengah)
4. BLOK PENYUSUN:
   "Disusun Oleh:"
   `{{NAMA}}`
   "NIM " `{{NIM}}`
5. BLOK PEMBIMBING:
   "Dosen Pembimbing:"
   `{{DOSEN}}`
6. BLOK INSTITUSI (Bagian Bawah Halaman):
   "PROGRAM STUDI " `{{PRODI}}`
   "FAKULTAS " `{{FAKULTAS}}`
   `{{INSTITUSI}}`
   `{{TAHUN}}`

---

### Langkah 3: Penyelarasan Penanda di `src/generator/document/template.py`

Pastikan daftar penanda opsional memuat identitas institusi:

```python
# Lokasi: src/generator/document/template.py
OPTIONAL_PLACEHOLDERS: list[str] = [
    "{{TAHUN}}",
    "{{PRODI}}",
    "{{FAKULTAS}}",
    "{{INSTITUSI}}",
    "{{MATA_KULIAH}}",
    "{{DOSEN}}",
    "{{TANGGAL}}",
]
```

---

### Langkah 4: Regenerasi Template Standar Akademik

Setelah kode diperbarui, buat ulang berkas template standar:
1. Hapus template lama di `data/templates/Template_Standar_Akademik.docx`.
2. Jalankan pembuatan template baru melalui bridge:
```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python -c "from generator.database import Database; from generator.paths import DB_PATH; from generator.web.api_bridge import ApiBridge; bridge = ApiBridge(Database(DB_PATH)); bridge.create_default_template()"
```

---

## 3. Rencana Pengujian & Verifikasi (Verification Checklist)

### 1. Uji Coba Unit Otomatis (Pytest)
```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python -m pytest tests/test_renderer.py tests/test_placeholders.py tests/test_template.py -v
```
*Kriteria Sukses*: Seluruh tes lulus (100% PASSED).

### 2. Uji Integrasi Render Dokumen Lengkap
```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python scratch/generate_agriculture_report.py
```

### 3. Verifikasi Inspeksi Dokumen (Acceptance Criteria)
Jalankan skrip inspeksi teks DOCX dan periksa hal-hal berikut:
* [ ] **Penanda Terganti 100%**: Tidak boleh ada teks `{{...}}` yang tersisa di seluruh dokumen Word.
* [ ] **Cover Rapi**:
  * Judul tertera jelas dengan format tebal.
  * Nama mahasiswa dan NIM terformat rapi.
  * Nama dosen pembimbing tercetak jelas.
  * Program studi, fakultas, universitas, dan tahun tertera di kaki halaman cover.
* [ ] **Page Break Antar-Bab**: BAB 1, BAB 2, BAB 3, BAB 4, dan DAFTAR PUSTAKA masing-masing berawal pada halaman baru yang bersih.
* [ ] **Tipografi Paragraf**: Paragraf beralinea masuk (first line indent 1 cm), spasi 1.5, dan rata kanan-kiri (*Justified*).
