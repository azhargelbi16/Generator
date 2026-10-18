# Generator Laporan Akademik Implementation Plan (Revisi 5)

> **Instruksi eksekusi (OpenCode), baca dulu:**
> - Kerjakan **satu task per giliran**, urut. Jangan menggabungkan task, terutama task GUI (13, 14, 15, 16, 17a, 17b, 17c).
> - **Jalankan semua perintah dari root repo `C:\Generator`.** Beberapa tes memakai path relatif (mis. `test_run_bat` membaca `run.bat` dari direktori kerja), jadi pytest harus dijalankan dari root.
> - **Selalu pakai interpreter venv, jangan `python` global.** Aktivasi `activate` tidak bertahan antar panggilan shell. Jalankan tes dengan `.venv\Scripts\python -m pytest <file> -v` dan pasang paket dengan `.venv\Scripts\python -m pip install ...`.
> - Tiap langkah: tulis tes dulu, jalankan `.venv\Scripts\python -m pytest <file> -v`, pastikan gagal karena alasan yang benar, implementasi, jalankan lagi sampai lulus, baru commit.
> - **Berhenti bila tes gagal.** Jangan lanjut ke task berikutnya sebelum tes task ini lulus. Jangan menandai selesai tanpa menjalankan tes.
> - Jangan menebak API pustaka. Untuk rapidocr (Task 1), catat bentuk keluaran asli `RapidOCR()(image)` sebelum mengunci versi.
> - Skill `superpowers:*` mungkin tidak terpasang di OpenCode. Bila tidak ada, jalankan plan ini manual mengikuti instruksi di atas, dan pakai skill OpenCode yang tersedia (`executing-plans`, `test-driven-development`, `requesting-code-review`, `finishing-a-development-branch`).

**Goal:** Membangun aplikasi desktop (Python + Tkinter) yang mengubah sumber PDF dan link web menjadi isi laporan akademik beserta sitasi dan daftar pustaka APA 7th yang terverifikasi, lalu menghasilkan file DOCX proper dengan logo kampus 5x5 cm, tanpa user menyentuh terminal.

**Architecture:** Lapisan inti yang murni dan mudah ditest (paths, config, logging, database SQLite, pembaca sumber, OCR, chunking, sitasi, verifikasi, penanda, validasi template, render DOCX, draf) dipisahkan dari lapisan AI (klien OpenAI-compatible) dan lapisan GUI (Tkinter). GUI hanya memanggil fungsi inti. Verifikasi cuplikan dan penempatan sitasi dilakukan oleh kode, bukan oleh AI.

**Tech Stack:** Python 3.12, Tkinter (bawaan), sqlite3 (bawaan), python-docx, pypdf, pypdfium2, rapidocr, onnxruntime, requests, beautifulsoup4, pytest, Pillow (runtime renderer untuk logo, sekaligus fixture tes).

**Spec:** `docs/superpowers/specs/2026-10-18-generator-laporan-design.md` (Revisi 5 + Putaran 6). Plan ini menggantikan versi 13 task sebelumnya dan menyerap revisi putaran 2, 3, 4, 5, dan 6.

## Struktur File

Mengikuti bagian 13 dokumen desain, ditambah `drafts.py` untuk draf sementara (bagian 8 dan 20):

```
src/generator/
  paths.py            lokasi folder data, dengan fallback (12.8, 20)
  config.py           muat/simpan konfigurasi AI
  logging_setup.py    log ke data/app.log tanpa API key
  database.py         SQLite: profil_mahasiswa, dosen, mata_kuliah, logo, template, schema_version
  drafts.py           simpan/muat/hapus draf sementara di data/drafts/
  verification.py     verifikasi deterministik cuplikan
  report.py           gerbang ekspor, label sitasi, daftar pustaka terpakai, isi fields
  sources/
    errors.py         kelas SourceReadError tunggal (dipakai pdf_reader dan web_reader)
    ocr.py            render halaman (pypdfium2) + OCR (rapidocr)
    pdf_reader.py     ekstrak teks PDF, deteksi scan, metadata
    web_reader.py     ambil teks dan metadata dari URL
    chunking.py       pemotongan teks panjang
  ai/
    client.py         klien OpenAI-compatible + tes koneksi
    prompts.py        template prompt (teks sumber = data)
    bibliography.py   ekstrak + gabung metadata bibliografi
    citation.py       sitasi APA 7th (murni, mudah ditest)
    content.py        tulis isi laporan berbasis sumber + tempatkan sitasi
  document/
    placeholders.py   cari/ganti penanda lintas run
    template.py       baca dan validasi template DOCX
    renderer.py       isi penanda, buat DOCX (logo, TOC, hanging indent)
  gui/
    app.py            jendela utama dan menu
    worker.py         jalankan operasi lama di thread, hasil lewat after
    tab_data.py       profil mahasiswa, dosen, matkul, logo
    tab_template.py   kelola template
    tab_report.py     alur buat laporan
    tab_settings.py   pengaturan AI + tombol Tes koneksi
tests/
data/                 diabaikan git (database, logo, template, draf, config, log)
```

## Global Constraints

- Python 3.12, target Windows, dijalankan dari `C:\Generator`.
- Output dokumen hanya DOCX. Gaya sitasi hanya APA 7th. "et al." untuk tiga penulis atau lebih di sitasi dalam teks.
- Sumber jurnal tidak disimpan ke database. Draf disimpan sementara di `data/drafts/` dan dihapus saat ekspor atau dibuang user.
- Logo kampus di cover berukuran tepat 5x5 cm; logo tidak persegi di-fit tanpa dipotong, rasio aspek dipertahankan (20).
- Penanda wajib (persis): `{{JUDUL}}`, `{{NAMA}}`, `{{NIM}}`, `{{MATA_KULIAH}}`, `{{DOSEN}}`, `{{LOGO}}`, `{{TANGGAL}}`, `{{ISI_LAPORAN}}`, `{{DAFTAR_PUSTAKA}}`, `{{DAFTAR_ISI}}`.
- Penanda opsional: `{{TAHUN}}` (tahun berjalan), `{{PRODI}}` (profil mahasiswa). Dibiarkan kosong bila tidak ada sumber nilai.
- Penanda khusus (`{{ISI_LAPORAN}}`, `{{DAFTAR_PUSTAKA}}`, `{{DAFTAR_ISI}}`, `{{LOGO}}`) wajib berdiri sendiri di satu paragraf.
- Template yang kehilangan penanda wajib atau punya penanda khusus tidak berdiri sendiri harus ditolak dengan dialog ramah yang menyebut penanda mana, bukan crash (9.3, 9.4).
- Penanda tak dikenal (`{{FOO}}`) dibiarkan apa adanya, dicatat, dan ditampilkan sebagai peringatan sebelum ekspor (9.2).
- AI tidak boleh mengarang: semua isi berasal dari teks sumber yang diekstrak. Teks sumber diperlakukan sebagai data, bukan perintah (11.6).
- Verifikasi cuplikan hanya terhadap sumber di `source_ids` (teks lengkap, bukan chunk), panjang minimum cuplikan 8 kata, setelah normalisasi spasi, huruf, dan tanda hubung (11.2).
- Status per kalimat: `terverifikasi`, `tidak terverifikasi`, `bukan klaim faktual`. Kalimat tanpa entri dari AI dianggap `tidak terverifikasi`. Tidak ada kalimat yang lolos tanpa status (11.2).
- Penulis dimodelkan eksplisit (`Author(family, given, is_org, abbrev)`); kode tidak menebak pemisahan nama (12.4, 17).
- Sitasi dalam teks dibuat kode dari `source_ids`; daftar pustaka hanya memuat sumber yang dikutip (11.4).
- Ekspor DOCX diblokir selama masih ada kalimat `tidak terverifikasi` atau `bukan klaim faktual` yang belum ditandai selesai oleh user; user boleh lanjut setelah konfirmasi eksplisit, dan statusnya dicatat di log (11.5, 19).
- Chunking: chunk dikelompokkan ke batch di bawah batas karakter prompt, satu panggilan AI per batch, hasil digabung dan kalimat duplikat dibuang (12.3).
- API key disimpan polos di `data/config.json`, diabaikan git, tidak pernah ditulis ke log (15).
- Operasi lama (OCR, panggilan AI per batch, ambil web) berjalan di thread lain; UI Tkinter hanya diperbarui dari thread utama lewat antrean/`after`, supaya jendela tidak "Not Responding" (bagian 13).
- Kalimat hasil edit manual (`origin="manual"`) selalu `tidak terverifikasi` sampai user menandai selesai, walau teksnya kebetulan cocok (19).
- Nilai `{{TANGGAL}}`, `{{TAHUN}}`, `{{PRODI}}` diisi kode dari profil dan tanggal sistem, bukan oleh AI; penanda opsional tanpa nilai diganti string kosong supaya penanda mentah tidak tercetak (18).
- Renderer memakai style Heading yang ada di template; bila template tidak punya, renderer membuat atau fallback tanpa crash (18.1).
- Tidak memakai karakter em dash pada teks yang ditulis proyek (antislop).
- `config.example.json` tidak dipakai lagi; konfigurasi lewat tab Pengaturan (13).

## Review Focus

Lima kelas input atau mode kegagalan yang tidak diuji langsung task lain tetapi paling mungkin menjebak pemakai. Tiap baris dipasangkan tes di task pemilik kodenya.

1. PDF scan tanpa lapisan teks dan OCR gagal: `extract_text_or_ocr` melempar `SourceReadError` berpesan tempel manual, sumber lain tetap diproses (12.1). Tes di Task 4.
2. Website diblokir atau butuh JavaScript: `fetch_text` melempar `SourceReadError` per sumber (12.2). Tes di Task 4.
3. Respons AI bukan JSON valid: retry sekali lalu `BibliographyError`; content mengembalikan daftar kosong, bukan crash (12.7). Tes di Task 7 dan Task 8.
4. Template DOCX rusak atau bukan .docx: `TemplateError` ramah (12.5). Tes di Task 11.
5. Logo bukan gambar, tidak ditemukan, atau tidak persegi: dilewati atau di-fit tanpa menggagalkan render (12.6, 20). Tes di Task 12.

Mode kegagalan lain yang sudah punya tes langsung: penanda terpecah antar run dan penanda tak dikenal (Task 10, 11), chunking teks panjang (Task 4), folder data tidak bisa ditulis (Task 2), edit manual menghapus sitasi (Task 17b).

---

### Task 0: Persiapan repo (git, venv, dependensi, letak dokumen)

Tidak ada tes; ini prasyarat supaya Task 1 bisa `.venv\Scripts\python -m pip install` dan `git commit`.

**Langkah:**

- [ ] Pastikan `git` ada. Di `C:\Generator`:
```bash
git init
git config user.name "Generator Dev"
git config user.email "dev@example.com"
```
- [ ] Buat virtualenv (pakai Python global sekali saja, di luar venv):
```bash
python -m venv .venv
```
- [ ] Jangan bergantung pada aktivasi `activate` (tidak bertahan antar panggilan shell). Selanjutnya selalu panggil interpreter venv langsung:
```bash
.venv\Scripts\python -m pip install --upgrade pip
```
- [ ] **Stop condition:** dua dokumen inti **wajib** ada di path yang dirujuk plan: `docs/superpowers/specs/2026-10-18-generator-laporan-design.md` dan `docs/superpowers/plans/2026-10-18-generator-laporan.md`. Bila salah satunya tidak ada, **berhenti** dan minta file itu dulu; jangan menetapkan path yang belum ada. `docs/superpowers/CHECKPOINT-2026-10-18.md` bersifat opsional (catatan sesi): bila tidak ada, cukup catat di log dan lanjut, **jangan berhenti**.
- [ ] Buat `.gitignore` awal: `data/`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.superpowers/`.
- [ ] Commit awal:
```bash
git add docs .gitignore
git commit -m "docs: design, plan, and checkpoint"
```

Catatan: `requirements.txt` dan `pyproject.toml` dibuat di Task 1. Instalasi pertama (termasuk unduhan model rapidocr) butuh internet.

---

### Task 1: Pipeline OCR (spike pertama) dan kunci requirements.txt

Dikerjakan lebih dulu supaya kualitas OCR aksara Indonesia terbukti sebelum dependensi dikunci (12.1, putaran 3).

**Files:**
- Create: `src/generator/__init__.py`, `src/generator/sources/__init__.py`
- Create: `src/generator/sources/ocr.py`
- Create: `requirements.txt`, `.gitignore`, `pyproject.toml`
- Create: `tests/__init__.py`, `tests/fixtures/__init__.py`, `tests/fixtures/scan.py`
- Test: `tests/test_ocr.py`

**Interfaces:**
- Produces:
  - `ocr.ocr_pdf(pdf_path: Path) -> str`
  - `ocr.normalize(text: str) -> str` (lowercase, rapikan spasi)
  - `ocr.OcrError(Exception)`

- [ ] **Step 1: Tulis konfigurasi pytest dan tes yang gagal**

Konfigurasi ini wajib: tanpa `pythonpath`, `from generator...` (ada di `src/`) dan `from tests.fixtures...` tidak bisa diimpor.

```toml
# pyproject.toml
[tool.pytest.ini_options]
pythonpath = ["src", "."]
testpaths = ["tests"]
```

```python
# tests/fixtures/scan.py
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_scanned_pdf(path: Path, text: str) -> Path:
    img = Image.new("RGB", (1200, 260), "white")
    font = ImageFont.load_default(size=44)
    ImageDraw.Draw(img).text((40, 100), text, fill="black", font=font)
    img.save(path, "PDF", resolution=150)
    return path
```

```python
# tests/test_ocr.py
import pytest
from tests.fixtures.scan import make_scanned_pdf
from generator.sources import ocr

WORDS = ["laporan", "pertanian", "organik", "indonesia", "penelitian"]

def test_ocr_reads_indonesian_scan(tmp_path):
    pdf = make_scanned_pdf(tmp_path / "scan.pdf",
                           "Laporan penelitian pertanian organik Indonesia")
    text = ocr.normalize(ocr.ocr_pdf(pdf))
    assert sum(w in text for w in WORDS) >= 3

def test_ocr_missing_file_raises(tmp_path):
    with pytest.raises(ocr.OcrError):
        ocr.ocr_pdf(tmp_path / "nope.pdf")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_ocr.py -v`
Expected: FAIL, modul atau dependensi belum ada.

- [ ] **Step 3: Pasang dependensi dan implementasikan `ocr.py`**

Pasang dulu: `.venv\Scripts\python -m pip install pypdfium2 rapidocr onnxruntime Pillow`.
`ocr_pdf`: buka PDF dengan `pypdfium2.PdfDocument`, render tiap halaman ke `numpy`/PIL image pada ~200 DPI, jalankan `rapidocr.RapidOCR()(image)`, gabung teks hasil tiap halaman dengan newline. Bungkus kegagalan apa pun menjadi `OcrError` berpesan Indonesia (file tidak ada, PDF rusak, model gagal). Simpan instance `RapidOCR` sekali (module-level lazy) supaya tidak memuat model tiap panggilan. Bila rapidocr mengunduh model saat pertama jalan, arahkan cache ke `data/` dan catat di README (task 18). API rapidocr 3.x belum diverifikasi di plan ini: catat bentuk keluaran asli `RapidOCR()(image)` (tipe hasil dan kunci teksnya) di catatan task sebelum mengunci versi di Step 5. Instalasi dan unduhan model pertama kali butuh internet; bila offline atau unduhan gagal, tangkap dan lempar `OcrError` berpesan ramah, jangan crash.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_ocr.py -v`
Expected: PASS. Spike ini membuktikan kualitas OCR aksara Indonesia (12.1). Bila gagal karena mutu OCR, jangan lanjut: catat temuan dan diskusikan sebelum mengunci dependensi. **Jangan menyimpulkan rapidocr tidak cocok hanya dari fixture PDF berfont bawaan Pillow**; PDF berfont sintetis bisa lebih sulit dibaca daripada scan asli. Uji juga satu PDF scan Indonesia asli (mis. hasil pindai dokumen kampus) dan catat hasilnya di catatan task sebelum memutuskan.

- [ ] **Step 5: Tulis `requirements.txt` (kunci versi), `.gitignore`, dan `pyproject.toml`**

Pastikan `pyproject.toml` dari Step 1 ada (konfigurasi `pythonpath` pytest wajib). Pin versi yang benar-benar terpasang (mis. `pypdfium2==5.14.0`, `rapidocr==3.10.0`, `onnxruntime==1.31.0`). Daftar lengkap: `python-docx`, `pypdf`, `pypdfium2`, `rapidocr`, `onnxruntime`, `requests`, `beautifulsoup4`, `pytest`, `Pillow`. **Pillow adalah dependensi runtime**, bukan hanya tes: renderer memakainya untuk menghitung rasio logo (20); pytest juga memakainya untuk fixture. `.gitignore`: `data/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.superpowers/`.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore pyproject.toml src/generator/__init__.py src/generator/sources/__init__.py src/generator/sources/ocr.py tests/__init__.py tests/fixtures tests/test_ocr.py
git commit -m "feat: OCR pipeline for scanned Indonesian PDFs; lock dependencies"
```

---

### Task 2: Config, paths dengan fallback, dan logging

**Files:**
- Create: `src/generator/paths.py`, `src/generator/config.py`, `src/generator/logging_setup.py`
- Test: `tests/test_paths.py`, `tests/test_config.py`, `tests/test_logging.py`

**Interfaces:**
- Consumes: tidak ada.
- Produces:
  - `paths.PROJECT_ROOT`, `paths.DATA_DIR`, `paths.DB_PATH`, `paths.LOGOS_DIR`, `paths.TEMPLATES_DIR`, `paths.DRAFTS_DIR`, `paths.OUTPUT_DIR`, `paths.CONFIG_PATH`, `paths.LOG_PATH` (semua `Path`)
  - `paths.ensure_dirs() -> None`, `paths.set_data_dir(base: Path) -> None`, `paths.PathsError(Exception)`
  - `config.Config` (dataclass: `ai_base_url: str`, `ai_api_key: str`, `ai_model: str`, `ai_temperature: float`)
  - `config.load_config(path: Path) -> Config`, `config.save_config(cfg: Config, path: Path) -> None`, `config.default_config() -> Config`
  - `logging_setup.setup_logging(log_path: Path) -> None`, `logging_setup.get_logger(name: str) -> logging.Logger`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_paths.py
import pytest
from generator import paths

def test_ensure_dirs_creates_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path / "data" / "logos")
    monkeypatch.setattr(paths, "TEMPLATES_DIR", tmp_path / "data" / "templates")
    monkeypatch.setattr(paths, "DRAFTS_DIR", tmp_path / "data" / "drafts")
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")
    paths.ensure_dirs()
    assert paths.DRAFTS_DIR.is_dir() and paths.OUTPUT_DIR.is_dir()

def test_set_data_dir_repoints_paths(tmp_path, monkeypatch):
    for name in ["DATA_DIR", "DB_PATH", "LOGOS_DIR", "TEMPLATES_DIR",
                 "DRAFTS_DIR", "CONFIG_PATH", "LOG_PATH"]:
        monkeypatch.setattr(paths, name, getattr(paths, name))
    paths.set_data_dir(tmp_path)
    assert paths.DB_PATH == tmp_path / "app.db"
    assert paths.CONFIG_PATH == tmp_path / "config.json"

def test_ensure_dirs_wraps_oserror(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path / "data" / "logos")
    monkeypatch.setattr(paths, "TEMPLATES_DIR", tmp_path / "data" / "templates")
    monkeypatch.setattr(paths, "DRAFTS_DIR", tmp_path / "data" / "drafts")
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")
    def boom(self, *a, **k): raise OSError("read-only")
    monkeypatch.setattr(paths.Path, "mkdir", boom)
    with pytest.raises(paths.PathsError):
        paths.ensure_dirs()
```

```python
# tests/test_config.py
from generator import config

def test_roundtrip_config(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.Config("http://localhost:1234/v1", "k", "m", 0.2)
    config.save_config(cfg, p)
    assert config.load_config(p) == cfg

def test_load_missing_returns_default(tmp_path):
    assert config.load_config(tmp_path / "nope.json").ai_temperature == 0.2
```

```python
# tests/test_logging.py
from generator import logging_setup

def test_logging_writes_to_file(tmp_path):
    log = tmp_path / "app.log"
    logging_setup.setup_logging(log)
    logging_setup.get_logger("x").error("boom")
    assert "boom" in log.read_text(encoding="utf-8")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_paths.py tests/test_config.py tests/test_logging.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan ketiga modul**

`paths.py`: `PROJECT_ROOT = Path(__file__).resolve().parents[2]`; `DATA_DIR = PROJECT_ROOT / "data"`; turunkan sisanya (`DB_PATH = DATA_DIR / "app.db"`, `LOGOS_DIR`, `TEMPLATES_DIR`, `DRAFTS_DIR`, `OUTPUT_DIR = PROJECT_ROOT / "output"`, `CONFIG_PATH = DATA_DIR / "config.json"`, `LOG_PATH = DATA_DIR / "app.log"`). `ensure_dirs()` memakai `mkdir(parents=True, exist_ok=True)`; bila gagal lempar `PathsError`. `set_data_dir(base)` menghitung ulang `DATA_DIR`, `DB_PATH`, `LOGOS_DIR`, `TEMPLATES_DIR`, `DRAFTS_DIR`, `CONFIG_PATH`, `LOG_PATH` (menjawab 12.8 dan 20); GUI yang menangani pemilihan folder user.

`config.py`: `Config` sebagai `@dataclass`; `load_config` mengembalikan `default_config()` bila file tidak ada atau rusak; `save_config` menulis JSON rapi (`indent=2`). `default_config()`: base url contoh, api key kosong, model contoh, `ai_temperature=0.2` (temperatur rendah, 11.7).

`logging_setup.py`: `setup_logging` memasang `FileHandler` ke `log_path` dengan format ringkas, level INFO, dan mengganti handler lama agar tidak menggandakan. `get_logger(name)` mengembalikan `logging.getLogger(name)`. Jangan pernah mencatat nilai API key.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_paths.py tests/test_config.py tests/test_logging.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/paths.py src/generator/config.py src/generator/logging_setup.py tests/test_paths.py tests/test_config.py tests/test_logging.py
git commit -m "feat: paths with fallback, config, and logging"
```

---

### Task 3: Lapisan database (profil mahasiswa, dosen, matkul, logo, template)

**Files:**
- Create: `src/generator/database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `paths.DB_PATH` (Task 2).
- Produces:
  - `database.Profil(nama: str, nim: str, prodi: str)`
  - `database.Dosen(id: int, nama: str, gelar: str, identitas: str)`
  - `database.MataKuliah(id: int, nama: str, kode: str)`
  - `database.Logo(id: int, nama: str, path: str)`
  - `database.Template(id: int, nama: str, deskripsi: str, path: str)`
  - `database.Database(db_path)` dengan `init_schema()`, `get_profil() -> Profil`, `set_profil(p: Profil) -> None`, dan untuk dosen/matkul/logo/template: `add_*` (mengembalikan `int` lastrowid), `list_*`, `update_*`, `delete_*`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_database.py
from generator.database import Database, Dosen, Profil

def test_profil_roundtrip(tmp_path):
    db = Database(tmp_path / "t.db"); db.init_schema()
    db.set_profil(Profil("Budi", "123", "Agroteknologi"))
    assert db.get_profil().prodi == "Agroteknologi"
    assert db.get_profil().nama == "Budi"

def test_add_update_delete_dosen(tmp_path):
    db = Database(tmp_path / "t.db"); db.init_schema()
    rid = db.add_dosen(Dosen(0, "Budi", "", ""))
    db.update_dosen(Dosen(rid, "Budi Santoso", "S.P.", ""))
    assert db.list_dosen()[0].nama == "Budi Santoso"
    db.delete_dosen(rid)
    assert db.list_dosen() == []

def test_schema_version_recorded(tmp_path):
    db = Database(tmp_path / "t.db"); db.init_schema()
    assert db.schema_version() >= 1
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_database.py -v`
Expected: FAIL, `Database` belum ada.

- [ ] **Step 3: Implementasikan `database.py`**

Dataclass seperti pada Interfaces. `init_schema()` memakai `CREATE TABLE IF NOT EXISTS` untuk `profil_mahasiswa(nama, nim, prodi)`, `dosen(nama, gelar, identitas)`, `mata_kuliah(nama, kode)`, `logo(nama, path)`, `template(nama, deskripsi, path)`, dan `schema_version(version)` (menjawab 20, migrasi database). `get_profil` mengembalikan satu baris (baris kosong bila belum ada); `set_profil` menulis ulang baris tunggal. Gunakan koneksi sqlite dengan `check_same_thread=False` bila nanti dipakai GUI.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_database.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/database.py tests/test_database.py
git commit -m "feat: sqlite database with profil mahasiswa and schema_version"
```

---

### Task 4: Pembaca sumber (PDF, web) + deteksi scan + chunking

**Files:**
- Create: `src/generator/sources/errors.py`, `src/generator/sources/pdf_reader.py`, `src/generator/sources/web_reader.py`, `src/generator/sources/chunking.py`
- Test: `tests/test_sources.py`, `tests/test_chunking.py`

**Interfaces:**
- Consumes: `ocr.ocr_pdf` (Task 1).
- Produces:
  - `errors.SourceReadError(Exception)` (kelas tunggal; `pdf_reader` dan `web_reader` mengimpornya, bukan mendefinisikan sendiri, supaya penanganan di GUI menangkap keduanya)
  - `pdf_reader.SourceReadError` (alias impor dari `errors`), `pdf_reader.has_text_layer(pdf_path: Path) -> bool`, `pdf_reader.extract_text(pdf_path: Path) -> str`, `pdf_reader.extract_text_or_ocr(pdf_path: Path) -> str`, `pdf_reader.extract_metadata(pdf_path: Path) -> dict[str, str]`
  - `web_reader.SourceReadError` (alias impor dari `errors`), `web_reader.fetch_text(url: str) -> str`, `web_reader.fetch_metadata(url: str) -> dict[str, str]`
  - `chunking.Chunk(id: int, text: str)`, `chunking.chunk_text(text: str, max_chars: int = 3000) -> list[Chunk]`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_sources.py
import pytest
from generator.sources import web_reader, pdf_reader, errors

def test_source_read_error_is_single_class():
    assert pdf_reader.SourceReadError is web_reader.SourceReadError is errors.SourceReadError

def test_fetch_text_extracts_html(monkeypatch):
    class Resp:
        headers = {"Content-Type": "text/html"}
        text = "<html><head><title>Judul</title></head><body><p>Halo</p><script>x()</script></body></html>"
        def raise_for_status(self): pass
    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: Resp())
    assert "Halo" in web_reader.fetch_text("http://x")
    assert "x()" not in web_reader.fetch_text("http://x")
    assert web_reader.fetch_metadata("http://x")["title"] == "Judul"

def test_extract_text_missing_file_raises(tmp_path):
    with pytest.raises(pdf_reader.SourceReadError):
        pdf_reader.extract_text(tmp_path / "nope.pdf")

def test_scan_detected_and_ocr_called(tmp_path, monkeypatch):
    from tests.fixtures.scan import make_scanned_pdf
    pdf = make_scanned_pdf(tmp_path / "s.pdf", "Laporan penelitian")
    assert pdf_reader.has_text_layer(pdf) is False
    monkeypatch.setattr(pdf_reader.ocr, "ocr_pdf", lambda p: "hasil ocr")
    assert pdf_reader.extract_text_or_ocr(pdf) == "hasil ocr"

def test_ocr_failure_becomes_source_error(tmp_path, monkeypatch):
    from tests.fixtures.scan import make_scanned_pdf
    from generator.sources import ocr
    pdf = make_scanned_pdf(tmp_path / "s.pdf", "Laporan penelitian")
    def boom(p): raise ocr.OcrError("gagal")
    monkeypatch.setattr(pdf_reader.ocr, "ocr_pdf", boom)
    with pytest.raises(pdf_reader.SourceReadError):
        pdf_reader.extract_text_or_ocr(pdf)

def test_web_request_error_becomes_source_error(monkeypatch):
    def boom(*a, **k): raise web_reader.requests.RequestException("blocked")
    monkeypatch.setattr(web_reader.requests, "get", boom)
    with pytest.raises(web_reader.SourceReadError):
        web_reader.fetch_text("http://x")
```

```python
# tests/test_chunking.py
from generator.sources.chunking import chunk_text

def test_chunk_text_splits_long_text():
    chunks = chunk_text("a" * 7000, max_chars=3000)
    assert [c.id for c in chunks] == [0, 1, 2]
    assert all(len(c.text) <= 3000 for c in chunks)

def test_chunk_text_short_is_single():
    assert len(chunk_text("pendek")) == 1
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_sources.py tests/test_chunking.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan keempat modul**

`sources/errors.py`: definisikan `class SourceReadError(Exception)` sekali di sini. `pdf_reader.py` dan `web_reader.py` mengimpor `from .errors import SourceReadError` (atau `from generator.sources.errors import SourceReadError`) dan tidak mendefinisikan kelas sendiri; GUI (Task 16) cukup menangkap `sources.errors.SourceReadError` untuk kedua jenis sumber.

`web_reader.fetch_text`: `requests.get(url, timeout=30)`, `raise_for_status()`, pilih parser sesuai `Content-Type` (`html.parser` untuk HTML), `BeautifulSoup(...).get_text(" ", strip=True)`. Bungkus `requests.RequestException` menjadi `SourceReadError` berpesan Indonesia (12.2). `fetch_metadata`: ambil `<title>` dan meta `citation_author`, `citation_publication_date`, `citation_title`, `citation_journal_title`, `citation_doi` bila ada.

`pdf_reader`: `has_text_layer` membaca `pypdf.PdfReader` dan cek total teks tidak kosong; `extract_text` menggabung `page.extract_text()` dan melempar `SourceReadError` bila file hilang, rusak, atau tidak punya teks (pesan "PDF tidak punya teks"). `extract_text_or_ocr`: bila `has_text_layer` False, panggil `ocr.ocr_pdf`; bila OCR gagal, lempar `SourceReadError` berpesan "OCR gagal, tempel teks manual" (12.1). `extract_metadata`: baca `reader.metadata` (author, title, creation date) dan informasi DOI pada teks bila terdeteksi.

`chunking.chunk_text`: bila `len(text) <= max_chars` kembalikan satu `Chunk(0, text)`. Selain itu potong per `max_chars` karakter, usahakan potong di batas spasi terdekat, beri `id` berurutan dari 0 (12.3).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_sources.py tests/test_chunking.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/sources/errors.py src/generator/sources/pdf_reader.py src/generator/sources/web_reader.py src/generator/sources/chunking.py tests/test_sources.py tests/test_chunking.py
git commit -m "feat: pdf/web source readers, scan detection, and chunking"
```

---

### Task 5: Klien AI (OpenAI-compatible) dan tes koneksi

**Files:**
- Create: `src/generator/ai/__init__.py`, `src/generator/ai/client.py`
- Test: `tests/test_ai_client.py`

**Interfaces:**
- Consumes: `config.Config` (Task 2).
- Produces:
  - `client.AIClient(cfg: Config)` dengan `chat(messages: list[dict], json_mode: bool = False) -> str`
  - `client.AIError(Exception)`
  - `client.check_connection(client: AIClient) -> tuple[bool, str]`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_ai_client.py
import pytest
from generator.config import Config
from generator.ai.client import AIClient, AIError, check_connection

def _cfg():
    return Config("http://x/v1", "k", "m", 0.2)

def test_chat_returns_content(monkeypatch):
    class Resp:
        status_code = 200
        def json(self): return {"choices": [{"message": {"content": "halo"}}]}
        def raise_for_status(self): pass
    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    assert AIClient(_cfg()).chat([{"role": "user", "content": "hai"}]) == "halo"

def test_chat_http_error_raises_ai_error(monkeypatch):
    class Resp:
        status_code = 500
        text = "boom"
        def json(self): return {}
        def raise_for_status(self): raise Exception("500")
    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    with pytest.raises(AIError):
        AIClient(_cfg()).chat([{"role": "user", "content": "hai"}])

def test_chat_wraps_unexpected_exception(monkeypatch):
    def boom(*a, **k): raise Exception("jaringan putus")
    monkeypatch.setattr("generator.ai.client.requests.post", boom)
    with pytest.raises(AIError):
        AIClient(_cfg()).chat([{"role": "user", "content": "hai"}])

def test_check_connection_reports_failure(monkeypatch):
    def boom(*a, **k): raise AIError("offline")
    monkeypatch.setattr("generator.ai.client.AIClient.chat", lambda self, *a, **k: boom())
    ok, msg = check_connection(AIClient(_cfg()))
    assert ok is False and msg
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_ai_client.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `client.py`**

POST ke `{ai_base_url}/chat/completions` dengan header `Authorization: Bearer <key>`, JSON body `model`, `messages`, `temperature`; bila `json_mode`, tambahkan `response_format={"type": "json_object"}`. Ambil `choices[0].message.content`. Bungkus error jaringan, timeout, dan HTTP menjadi `AIError` berpesan Indonesia. **Periksa `response.status_code >= 400` secara eksplisit dan lempar `AIError` dengan kode status** sebelum memakai isi respons; jangan bergantung pada `raise_for_status` saja. Bungkus seluruh panggilan `requests.post` dan pembacaan respons dalam `try/except Exception as exc: raise AIError(...)` supaya exception umun (termasuk yang dilempar tes seperti `raise Exception("500")`) tidak bocor mentah. Bila respons tidak punya `choices`, lempar `AIError`. Nilai API key tidak boleh masuk log. `check_connection` (bukan `test_connection`, supaya pytest tidak mengumpulkannya sebagai tes): kirim pesan uji singkat, kembalikan `(True, "Koneksi berhasil")` atau `(False, alasan singkat)` (15).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_ai_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/ai/__init__.py src/generator/ai/client.py tests/test_ai_client.py
git commit -m "feat: openai-compatible ai client with connection test"
```

---

### Task 6: Format sitasi APA 7th (aturan lengkap)

**Files:**
- Create: `src/generator/ai/citation.py`
- Test: `tests/test_citation.py`

**Interfaces:**
- Consumes: tidak ada.
- Produces:
  - `citation.Author` (frozen dataclass: `family: str`, `given: str = ""`, `is_org: bool = False`, `abbrev: str = ""`)
  - `citation.Source` (frozen dataclass: `authors: list[Author]`, `year: str`, `title: str`, `container: str = ""`, `doi: str = ""`, `url: str = ""`)
  - `citation.LabeledSource` (dataclass: `source: Source`, `source_index: int`, `suffix: str`, `in_text: str`, `reference: str`)
  - `citation.initials(given: str) -> str`
  - `citation.in_text(source: Source, *, first_use: bool = True, family_with: Sequence[Source] = (), suffix: str = "") -> str`
  - `citation.reference(source: Source, *, suffix: str = "") -> str`
  - `citation.order_and_label(sources: Sequence[Source], cite: set[int] | None = None) -> list[LabeledSource]` (urut alfabetis, `source_index` menyimpan indeks asli di `sources`, tetapkan sufiks a/b/c lalu hitung `in_text` dan `reference`)

Nama keluarga eksplisit di `Author.family`; `is_org` menandai penulis organisasi; `abbrev` diisi hanya bila organisasi punya singkatan. Kode tidak menebak pemisahan nama (12.4). Aturan: 17.1 sampai 17.4 dokumen desain.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_citation.py
from generator.ai.citation import Author, Source, in_text, reference, order_and_label

def A(family, given="", is_org=False, abbrev=""):
    return Author(family, given, is_org, abbrev)

def S(authors, year="2020", title="Judul", container="Jurnal", doi="", url=""):
    return Source(authors, year, title, container, doi, url)

def test_one_two_three_authors():
    assert in_text(S([A("Santoso", "Budi")])) == "(Santoso, 2020)"
    assert in_text(S([A("Santoso", "Budi"), A("Wijaya", "Ani")])) == "(Santoso & Wijaya, 2020)"
    assert in_text(S([A("Santoso", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")])) == "(Santoso et al., 2020)"

def test_no_year_is_nd():
    assert in_text(S([A("Sukarno")], year="")) == "(Sukarno, n.d.)"

def test_reference_lists_all_authors():
    r = reference(S([A("Santoso", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")], doi="10.1/x"))
    assert "Santoso, B." in r and "&" in r and "et al." not in r
    assert "(2020)" in r and "https://doi.org/10.1/x" in r

def test_twenty_one_authors():
    r = reference(S([A(f"Fam{i}", f"P{i}") for i in range(1, 22)]))
    assert "Fam1" in r and "Fam19" in r and "Fam20" not in r
    assert "…" in r and "&" not in r and "Fam21" in r

def test_no_author_uses_title():
    assert reference(S([], title="Judul Tanpa Penulis")).startswith("Judul Tanpa Penulis")

def test_website_uses_url_when_no_doi():
    r = reference(S([A("Wijaya", "Ani")], title="T", container="", url="https://contoh.id/a"))
    assert "https://contoh.id/a" in r and "https://doi.org" not in r

def test_organization_with_abbrev():
    s = S([A("Kementerian Pertanian", is_org=True, abbrev="Kementan")])
    assert in_text(s, first_use=True) == "(Kementerian Pertanian [Kementan], 2020)"
    assert in_text(s, first_use=False) == "(Kementan, 2020)"

def test_organization_without_abbrev():
    assert in_text(S([A("Stanford University", is_org=True)])) == "(Stanford University, 2020)"

def test_single_word_author():
    assert in_text(S([A("Sukarno")])) == "(Sukarno, 2020)"

def test_order_is_alphabetical():
    labels = order_and_label([S([A("Zed")], title="Z"), S([A("Abadi", "T")], title="A")])
    assert labels[0].source.title == "A"
    assert labels[0].source_index == 1 and labels[1].source_index == 0

def test_labels_keyed_by_original_index_not_sorted_position():
    labels = order_and_label([S([A("Zed")], title="Z"), S([A("Abadi", "T")], title="A")])
    by_index = {l.source_index: l.source.title for l in labels}
    assert by_index == {0: "Z", 1: "A"}

def test_suffix_only_among_cited_sources():
    src = [S([A("Santoso", "Budi")], title="A"),
           S([A("Santoso", "Budi")], title="B"),
           S([A("Wijaya", "Ani")], year="2021", title="C")]
    labels = order_and_label(src, cite={0, 2})
    assert {l.source_index: l.suffix for l in labels} == {0: "", 2: ""}
    assert {l.source_index: l.in_text for l in labels}[0] == "(Santoso, 2020)"

def test_same_author_year_gets_suffix():
    labels = order_and_label([S([A("Santoso", "Budi")], title="B"),
                              S([A("Santoso", "Budi")], title="A")])
    assert {l.suffix for l in labels} == {"a", "b"}
    assert "2020a" in labels[0].in_text

def test_first_author_same_second_differs_disambiguates():
    a = S([A("Cooper", "A"), A("Lee", "B"), A("X", "C")], year="2015")
    b = S([A("Cooper", "A"), A("Ross", "Y"), A("X", "C")], year="2015")
    assert in_text(a, family_with=[a, b]) == "(Cooper, Lee, et al., 2015)"
    assert in_text(b, family_with=[a, b]) == "(Cooper, Ross, et al., 2015)"
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_citation.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `citation.py`**

`initials(given)`: inisial tiap kata nama depan, mis. "Budi Setiawan" jadi "B. S.". `in_text`: satu penulis, dua penulis (`&`), tiga atau lebih (`et al.`); organisasi dengan `abbrev` memakai bentuk `Nama Penuh [Singkatan]` pada `first_use` lalu singkatan; organisasi tanpa `abbrev` memakai nama penuh; disambiguasi bila penulis pertama sama dengan sumber lain di `family_with` (tambah penulis kedua, ketiga, sampai beda, lalu `et al.`); sufiks a/b/c disisipkan setelah tahun. `reference`: penulis individu ditulis `Family, G.`; organisasi ditulis nama penuh; nama satu kata (given kosong) ditulis apa adanya; sampai 20 penulis cantumkan semua dengan `&` terakhir; 21 atau lebih pakai 19, `…`, penulis terakhir tanpa `&`; tanpa penulis pakai judul; DOI menjadi `https://doi.org/<doi>`, jika tidak ada pakai URL. `order_and_label`: masukkan tiap sumber bersama indeks aslinya (posisi di `sources`). Bila `cite` diberikan, sisakan hanya sumber yang indeksnya ada di `cite` sebelum apa pun dihitung, supaya sumber yang tidak dikutip tidak ikut menentukan sufiks a/b/c. Urutkan sisanya menurut nama keluarga penulis pertama lalu tahun lalu judul, tetapkan sufiks a/b/c hanya untuk penulis dan tahun yang sama di dalam himpunan yang tersisa, lalu hitung `in_text` (first_use, `family_with` = himpunan yang tersisa) dan `reference` tiap sumber. `source_index` selalu indeks asli, bukan posisi hasil pengurutan.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_citation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/ai/citation.py tests/test_citation.py
git commit -m "feat: full APA 7th citation rules incl. organization and disambiguation"
```

---

### Task 7: Ekstraksi bibliografi via AI, gabung metadata, dan retry

**Files:**
- Create: `src/generator/ai/prompts.py`, `src/generator/ai/bibliography.py`
- Test: `tests/test_bibliography.py`

**Interfaces:**
- Consumes: `client.AIClient`/`AIError` (Task 5), `citation.Source` (Task 6), `pdf_reader.extract_metadata`/`web_reader.fetch_metadata` (Task 4).
- Produces:
  - `prompts.bibliography_prompt(text: str) -> list[dict]`
  - `bibliography.excerpt(text: str, max_chars: int = 6000, tail_chars: int = 500) -> str` (awal `max_chars` karakter ditambah ekor `tail_chars` karakter bila teks lebih panjang, supaya prompt tidak melewati batas konteks)
  - `bibliography.extract_source(text: str, client: AIClient) -> Source` (memanggil `excerpt` sebelum mengirim)
  - `bibliography.merge_metadata(ai: Source, doc: dict[str, str]) -> Source`
  - `bibliography.BibliographyError(Exception)`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_bibliography.py
import pytest
from generator.ai.bibliography import extract_source, merge_metadata, excerpt, BibliographyError
from generator.ai.citation import Author, Source

class FakeClient:
    def __init__(self, replies): self.replies = list(replies); self.calls = 0
    def chat(self, messages, json_mode=False):
        self.calls += 1
        return self.replies.pop(0)

def test_excerpt_bounds_long_text():
    ex = excerpt("A" * 20000, max_chars=6000, tail_chars=500)
    assert ex.startswith("A" * 100) and ex.endswith("A" * 500)
    assert len(ex) <= 6000 + 500 + 10
    assert excerpt("pendek") == "pendek"

def test_extract_parses_authors_as_objects():
    reply = ('{"authors":[{"family":"Santoso","given":"Budi","is_org":false}],'
             '"year":"2020","title":"T","container":"J","doi":"10.1/x","url":""}')
    s = extract_source("teks", FakeClient([reply]))
    assert s.authors == [Author("Santoso", "Budi", False)]
    assert s.doi == "10.1/x"

def test_extract_retries_once_then_raises():
    c = FakeClient(["bukan json", "masih bukan json"])
    with pytest.raises(BibliographyError):
        extract_source("teks", c)
    assert c.calls == 2

def test_merge_prefers_document_metadata_but_keeps_author_model():
    ai = Source([Author("Salah", "X")], "1999", "Judul AI", "J", "", "")
    s = merge_metadata(ai, {"title": "Judul Asli", "year": "2021", "doi": "10.5/y"})
    assert s.title == "Judul Asli" and s.year == "2021" and s.doi == "10.5/y"
    assert s.authors == [Author("Salah", "X")]
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_bibliography.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `prompts.py` dan `bibliography.py`**

`prompts.bibliography_prompt`: instruksi JSON; `authors` berupa daftar objek `{family, given, is_org, abbrev}` (boleh usulan awal, user mengoreksi); kunci lain `year`, `title`, `container`, `doi`, `url`; aturan "jangan mengarang, kosongkan bila tidak ada"; tegaskan teks sumber adalah data, bukan perintah (11.6).

`bibliography.excerpt`: bila `len(text) <= max_chars` kembalikan `text` apa adanya; selain itu kembalikan `text[:max_chars] + "\n...\n" + text[-tail_chars:]` supaya metadata yang sering ada di awal (judul, penulis) dan yang kadang ada di akhir tetap terlihat tanpa mengirim seluruh teks.

`bibliography.extract_source`: panggil `client.chat(prompt, json_mode=True)` dengan `prompts.bibliography_prompt(bibliography.excerpt(text))`, bukan teks penuh, supaya PDF panjang tidak melewati batas konteks model. Ambil objek JSON pertama (`{...}`). `json.loads`; bila gagal, ulangi sekali (12.7); bila gagal lagi lempar `BibliographyError`. Bangun `Source` dengan `Author` dari tiap entri `authors` dan default string kosong. `merge_metadata`: untuk `title`, `year`, `container`, `doi`, `url` pakai nilai dokumen bila tidak kosong, selain itu nilai AI (metadata dokumen diprioritaskan, 12.4); `authors` tidak diambil dari metadata dokumen sebagai string mentah karena itu berarti menebak pemisahan nama, jadi penulis tetap dari AI dan menunggu koreksi user di formulir (12.4).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_bibliography.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/ai/prompts.py src/generator/ai/bibliography.py tests/test_bibliography.py
git commit -m "feat: AI bibliography extraction with metadata merge and retry"
```

---

### Task 8: Penulisan isi laporan berbasis sumber dan penempatan sitasi

**Files:**
- Create: `src/generator/ai/content.py`
- Modify: `src/generator/ai/prompts.py`
- Test: `tests/test_content.py`

**Interfaces:**
- Consumes: `client.AIClient` (Task 5), `citation.Source` (Task 6), `chunking.chunk_text` (Task 4).
- Produces:
  - `content.Sentence(text: str, quote: str = "", source_ids: list[int] = field(default_factory=list), is_factual: bool = True, uid: str = field(default_factory=lambda: uuid4().hex), origin: str = "ai", citation: bool = True)` (`uid` stabil per kalimat, dipakai penanda selesai; `origin` bernilai `"ai"` atau `"manual"`; `citation` benar bila sitasi otomatis dipasang)
  - `content.Paragraph(sentences: list[Sentence])`
  - `content.Section(level: int, title: str, paragraphs: list[Paragraph])`
  - `content.generate_sections(topic: str, outline: list[str], sources: list[Source], source_texts: list[str], client: AIClient, max_prompt_chars: int = 12000) -> list[Section]`
  - `content.compose(paragraph: Paragraph, labels: dict[int, str]) -> str` (`labels`: kunci = indeks sumber asli, urutan kunci = urutan sitasi/reference)
  - `prompts.content_prompt(topic, outline, sources, chunk_refs: list[tuple[int, str]]) -> list[dict]` (tiap chunk dipasangkan dengan id sumbernya)

Bentuk JSON internal per kalimat (batas 11.1 dan 18.1): AI mengembalikan paragraf berupa daftar kalimat, jadi kode tidak memisahkan kalimat sendiri dan tidak salah pecah pada "dkk." atau "Dr.". Chunking: teks sumber dipecah lalu dikelompokkan ke batch di bawah `max_prompt_chars`; satu panggilan AI per batch; hasil digabung dan kalimat duplikat dibuang (12.3).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_content.py
import pytest
from generator.ai.content import generate_sections, compose, Sentence, Paragraph
from generator.ai.citation import Author, Source

class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies); self.calls = 0; self.messages = []
    def chat(self, messages, json_mode=False):
        self.calls += 1; self.messages.append(messages)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

REPLY = ('{"sections":[{"level":1,"title":"Pendahuluan","paragraphs":[{"sentences":['
         '{"text":"Pertanian organik meningkat.","quote":"q1","source_ids":[0],"is_factual":true},'
         '{"text":"Pupuk alami lebih baik.","quote":"q2","source_ids":[1],"is_factual":true}]}]}]}')

def test_generate_parses_sections():
    src = [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "U", "J")]
    secs = generate_sections("tema", ["Pendahuluan"], src, ["teks1", "teks2"], FakeClient([REPLY]))
    assert secs[0].level == 1 and secs[0].title == "Pendahuluan"
    assert secs[0].paragraphs[0].sentences[0].quote == "q1"

def test_generate_coerces_string_source_ids_and_drops_invalid():
    reply = ('{"sections":[{"level":1,"title":"B","paragraphs":[{"sentences":['
             '{"text":"a.","quote":"q","source_ids":["0","x"],"is_factual":true}]}]}]}')
    secs = generate_sections("tema", ["B"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             ["teks"], FakeClient([reply]))
    assert secs[0].paragraphs[0].sentences[0].source_ids == [0]

def test_sentence_uid_is_unique_and_overridable():
    a, b = Sentence("x."), Sentence("x.")
    assert a.uid and b.uid and a.uid != b.uid
    assert Sentence("x.", uid="tetap").uid == "tetap"

def test_generate_requires_source_text():
    with pytest.raises(ValueError):
        generate_sections("tema", ["X"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                          [], FakeClient([REPLY]))

def test_generate_rejects_mismatched_sources_and_texts():
    with pytest.raises(ValueError):
        generate_sections("tema", ["X"],
                          [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
                           Source([Author("Wijaya", "Ani")], "2021", "U", "J")],
                          ["hanya satu teks"], FakeClient([REPLY]))

def test_generate_batches_long_sources_and_dedups():
    long_text = "kalimat " * 2000
    c = FakeClient([REPLY, REPLY])
    secs = generate_sections("tema", ["Pendahuluan"],
                             [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             [long_text], c, max_prompt_chars=500)
    assert c.calls >= 2
    texts = [s.text for s in secs[0].paragraphs[0].sentences]
    assert len(texts) == len(set(texts))

def test_compose_places_citation_before_period():
    p = Paragraph([Sentence("Pertanian organik meningkat.", "q1", [0]),
                   Sentence("Pupuk alami lebih baik.", "q2", [1])])
    out = compose(p, {0: "(Santoso, 2020)", 1: "(Wijaya, 2021)"})
    assert out == "Pertanian organik meningkat (Santoso, 2020). Pupuk alami lebih baik (Wijaya, 2021)."

def test_compose_skips_non_factual():
    p = Paragraph([Sentence("Bab ini membahas pertanian.", is_factual=False)])
    assert compose(p, {}) == "Bab ini membahas pertanian."

def test_compose_ignores_unknown_source_id():
    p = Paragraph([Sentence("Pernyataan tanpa sumber dikenal.", "x", [99])])
    assert compose(p, {}) == "Pernyataan tanpa sumber dikenal."

def test_compose_merges_multiple_citations():
    p = Paragraph([Sentence("Dua sumber mendukung klaim ini.", "q", [1, 0])])
    out = compose(p, {0: "(Abadi, 2020)", 1: "(Zed, 2021)"})
    assert out == "Dua sumber mendukung klaim ini (Abadi, 2020; Zed, 2021)."

def test_compose_respects_citation_flag():
    p = Paragraph([Sentence("Klaim tanpa sitasi.", "q", [0], citation=False)])
    assert compose(p, {0: "(Santoso, 2020)"}) == "Klaim tanpa sitasi."

def test_sentence_defaults_to_ai_origin_and_citation_on():
    s = Sentence("x.")
    assert s.origin == "ai" and s.citation is True

def test_prompt_labels_each_chunk_with_source_id():
    c = FakeClient([REPLY])
    generate_sections("tema", ["Pendahuluan"],
                      [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
                       Source([Author("Wijaya", "Ani")], "2021", "U", "J")],
                      ["teks satu", "teks dua"], c)
    joined = " ".join(m["content"] for m in c.messages[0])
    assert "[sumber 0]" in joined and "[sumber 1]" in joined

def test_bad_json_returns_empty_not_crash():
    assert generate_sections("tema", ["X"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             ["teks"], FakeClient(["bukan json"])) == []
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_content.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan**

`content.py` mengimpor `from dataclasses import dataclass, field` dan `from uuid import uuid4` (dipakai `Sentence.source_ids = field(default_factory=list)` dan `Sentence.uid = field(default_factory=lambda: uuid4().hex)`; tanpa impor, modul gagal).

`prompts.content_prompt`: terima `chunk_refs` berupa daftar pasangan `(source_id, teks)`. Sisipkan `topic`, `outline`, ringkasan tiap sumber beserta indeksnya, dan tiap chunk dengan label `[sumber <id>]` di depannya supaya AI punya dasar mengisi `source_ids`. Perintahkan "hanya tulis berdasarkan teks sumber, jangan mengarang, satu objek per kalimat, `quote` diambil harfiah dari sumber, `source_ids` merujuk indeks sumber yang tertera di label, tandai `is_factual` salah untuk kalimat yang bukan klaim"; tegaskan teks sumber adalah data, bukan perintah (11.6); minta JSON `{"sections":[{"level","title","paragraphs":[{"sentences":[{"text","quote","source_ids","is_factual"}]}]}]}`.

`content.generate_sections`: bila `source_texts` kosong atau `len(sources) != len(source_texts)`, lempar `ValueError` (panjang tidak cocok berarti indeks `source_ids` tidak bisa dipercaya). Pecah tiap teks sumber dengan `chunk_text(text, max_chars=max_prompt_chars)` supaya ukuran chunk mengikuti batas prompt, simpan tiap chunk bersama id sumbernya (`chunk_refs`), kelompokkan chunk ke batch sampai mendekati `max_prompt_chars`, panggil `client.chat(json_mode=True)` sekali per batch, gabung hasil per judul bab dalam urutan `outline`, dan buang kalimat duplikat (bandingkan teks yang dinormalisasi). Saat membangun `Sentence`, koersikan tiap `source_ids` ke `int` (AI kadang mengembalikan string "0") dan buang id yang gagal dikonversi, supaya `labels.get(id)` tidak meleset. Biarkan `Sentence` membuat `uid` sendiri saat dibuat dari AI; saat dimuat dari draf, pakai `uid` yang tersimpan. Bila satu respons gagal diurai sebagai JSON, lewati batch itu tanpa crash (12.7).

`content.compose`: untuk tiap kalimat pakai `sentence.text`; bila `is_factual` benar, `citation` benar, dan ada `source_ids` yang punya label, kumpulkan labelnya (buang tanda kurung terluar) lalu gabungkan menjadi **satu** tanda kurung dipisah `"; "`, diurutkan menurut urutan kunci di `labels` (urutan itu sudah urutan reference), dan sisipkan tepat sebelum tanda baca akhir kalimat (atau di akhir bila tidak ada tanda baca). Lewati id yang tidak ada di `labels` dan jangan `KeyError`. Kalimat non-faktual, kalimat dengan `citation` salah, dan kalimat tanpa sumber dibiarkan apa adanya (satu kalimat satu klaim, syarat A; sitasi dibuat kode, 11.4; beberapa karya dalam satu kurung dipisah titik koma, APA 7).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_content.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/ai/content.py src/generator/ai/prompts.py tests/test_content.py
git commit -m "feat: grounded report content generation and code-placed citations"
```

---

### Task 8b: Parafrase AI, usul outline AI, dan gabung hasil regenerate

**Files:**
- Modify: `src/generator/ai/content.py`, `src/generator/ai/prompts.py`
- Test: `tests/test_content_extra.py`

**Interfaces:**
- Consumes: tipe dan `generate_sections` dari `content` (Task 8), `client.AIClient` (Task 5), `citation.Source` (Task 6).
- Produces:
  - `prompts.outline_prompt(topic: str, sources: list[Source], source_samples: list[tuple[int, str]]) -> list[dict]`
  - `content.suggest_outline(topic: str, sources: list[Source], source_texts: list[str], client: AIClient, max_items: int = 12) -> list[str]`
  - `content.paraphrase(paragraph: Paragraph, sources: list[Source], source_texts: list[str], client: AIClient) -> Paragraph` (kalimat hasil `origin="ai"` supaya masih harus lulus verifikasi cuplikan)
  - `content.merge_regenerated(old_sections: list[Section], new_sections: list[Section], overwrite_all: bool = False) -> list[Section]` (pertahankan kalimat `origin="manual"`, kecuali `overwrite_all` benar)

Ketiga fungsi ini menutup fitur spec yang sebelumnya tanpa task: usul outline (18.2), parafrase (19), dan "tulis ulang semua" (19).

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_content_extra.py
from generator.ai.content import (Sentence, Paragraph, Section, suggest_outline,
    paraphrase, merge_regenerated)
from generator.ai.citation import Author, Source

class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies); self.calls = 0
    def chat(self, messages, json_mode=False):
        self.calls += 1
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

SRC = [Source([Author("Santoso", "Budi")], "2020", "T", "J")]

def test_suggest_outline_returns_titles():
    c = FakeClient(['{"outline":["Pendahuluan","Metode","Pembahasan"]}'])
    assert suggest_outline("tema", SRC, ["teks sumber"], c) == ["Pendahuluan", "Metode", "Pembahasan"]

def test_suggest_outline_bad_json_returns_empty():
    assert suggest_outline("tema", SRC, ["teks"], FakeClient(["bukan json"])) == []

def test_paraphrase_returns_ai_sentences():
    old = Paragraph([Sentence("Teks asli.", "q", [0])])
    c = FakeClient(['{"sentences":[{"text":"Teks yang diparafrase.","quote":"q","source_ids":[0],"is_factual":true}]}'])
    new = paraphrase(old, SRC, ["teks sumber pertanian organik meningkat pesat"], c)
    assert new.sentences[0].text == "Teks yang diparafrase."
    assert new.sentences[0].origin == "ai"

def test_merge_regenerated_keeps_manual_by_default():
    old = [Section(1, "Bab", [Paragraph([Sentence("hasil ai lama.", origin="ai")]),
                               Paragraph([Sentence("catatan manual.", origin="manual")])])]
    new = [Section(1, "Bab", [Paragraph([Sentence("hasil ai baru.", origin="ai")])])]
    merged = merge_regenerated(old, new)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "hasil ai baru." in texts and "catatan manual." in texts and "hasil ai lama." not in texts

def test_merge_regenerated_overwrite_all_drops_manual():
    old = [Section(1, "Bab", [Paragraph([Sentence("catatan manual.", origin="manual")])])]
    new = [Section(1, "Bab", [Paragraph([Sentence("hasil ai baru.")])])]
    merged = merge_regenerated(old, new, overwrite_all=True)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "catatan manual." not in texts and "hasil ai baru." in texts
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_content_extra.py -v`
Expected: FAIL, fungsi belum ada.

- [ ] **Step 3: Implementasikan**

`prompts.outline_prompt`: minta JSON `{"outline":["..."]}` berisi maksimal `max_items` judul bab, hanya dari topik dan ringkasan sumber; teks sumber tetap diperlakukan sebagai data (11.6). `content.suggest_outline`: bangun label `[sumber <id>]` seperti `content_prompt`, panggil `client.chat(json_mode=True)`, urai `outline`, kembalikan daftar string; bila JSON gagal diurai kembalikan `[]` tanpa crash.

`content.paraphrase`: kirim `paragraph` (kalimat beserta `source_ids` dan `quote` lama sebagai petunjuk) ke AI, minta JSON `{"sentences":[{"text","quote","source_ids","is_factual"}]}`; bangun `Sentence` baru dengan `origin="ai"`, koersikan `source_ids` seperti di Task 8, biarkan `uid` baru dibuat; bila JSON gagal, kembalikan paragraf lama tanpa crash.

`content.merge_regenerated`: gabungkan `new_sections` dengan kalimat `origin="manual"` dari `old_sections` yang judul babnya sama; kalimat manual dari bab yang tidak ada di hasil baru tetap dipertahankan di babnya sendiri; kalimat hasil AI lama dibuang; bila `overwrite_all` benar, hanya `new_sections` yang dipakai. Jaga urutan bab sesuai hasil baru.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_content_extra.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/ai/content.py src/generator/ai/prompts.py tests/test_content_extra.py
git commit -m "feat: ai paraphrase, outline suggestion, and regenerate merge"
```

---

### Task 9: Verifikasi deterministik cuplikan per kalimat

**Files:**
- Create: `src/generator/verification.py`
- Test: `tests/test_verification.py`

**Interfaces:**
- Consumes: `content.Sentence`/`Paragraph`/`Section` (Task 8).
- Produces:
  - `verification.STATUS_VERIFIED = "terverifikasi"`, `verification.STATUS_UNVERIFIED = "tidak_terverifikasi"`, `verification.STATUS_NON_FACTUAL = "bukan_klaim_faktual"`
  - `verification.MIN_WORDS = 8`
  - `verification.normalize(text: str) -> str`
  - `verification.verify_sentence(sentence: Sentence, source_texts: dict[int, str], min_words: int = 8) -> str`
  - `verification.SentenceStatus` (dataclass: `index: int`, `sentence: Sentence`, `status: str`)
  - `verification.verify_sections(sections: list[Section], source_texts: dict[int, str]) -> list[SentenceStatus]` (daftar datar, `index` global berurutan)

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_verification.py
from generator.verification import (normalize, verify_sentence, verify_sections,
    STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_NON_FACTUAL)
from generator.ai.content import Sentence, Paragraph, Section

GOOD = "pertanian organik di indonesia sangat penting bagi petani"

def test_normalize_collapses_and_casefolds():
    assert normalize("Halo   DUNIA\nini") == "halo dunia ini"

def test_normalize_joins_hyphen_breaks():
    assert "pertanian" in normalize("pertani-\nan organik")

def test_verify_uses_only_referenced_source():
    texts = {0: "laporan penelitian " + GOOD,
             1: "topik lain sama sekali berbeda dan tidak berkaitan lagi"}
    assert verify_sentence(Sentence("x", GOOD, [0]), texts) == STATUS_VERIFIED
    assert verify_sentence(
        Sentence("x", "topik lain sama sekali berbeda dan tidak berkaitan", [0]), texts
    ) == STATUS_UNVERIFIED

def test_short_quote_is_unverified():
    assert verify_sentence(Sentence("x", "kata pendek ada", [0]), {0: "kata pendek ada"}) == STATUS_UNVERIFIED

def test_factual_without_source_is_unverified():
    assert verify_sentence(Sentence("x", "", []), {0: GOOD}) == STATUS_UNVERIFIED

def test_manual_sentence_is_unverified():
    assert verify_sentence(Sentence("x", GOOD, [0], origin="manual"), {0: GOOD}) == STATUS_UNVERIFIED

def test_unknown_source_id_is_unverified_not_crash():
    assert verify_sentence(Sentence("x", GOOD, [99]), {0: GOOD}) == STATUS_UNVERIFIED

def test_non_factual_status():
    assert verify_sentence(Sentence("x", is_factual=False), {}) == STATUS_NON_FACTUAL

def test_verify_sections_indexes_every_sentence():
    sec = Section(1, "B", [Paragraph([Sentence("a.", GOOD, [0]),
                                      Sentence("b.", is_factual=False)])])
    statuses = verify_sections([sec], {0: GOOD})
    assert [s.status for s in statuses] == [STATUS_VERIFIED, STATUS_NON_FACTUAL]
    assert [s.index for s in statuses] == [0, 1]
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_verification.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `verification.py`**

`normalize`: lowercase, gabung kata yang terpenggal tanda hubung di akhir baris (`-\n`), rapikan semua spasi putih berlebih menjadi satu spasi (11.2). `verify_sentence`: bila `is_factual` salah kembalikan `STATUS_NON_FACTUAL`; bila `origin != "ai"` (kalimat hasil edit manual) kembalikan `STATUS_UNVERIFIED` tanpa memeriksa cuplikan, karena verifikasi otomatis hanya berlaku untuk teks AI (11.2, 19); bila `quote` kosong, jumlah katanya kurang dari `min_words`, atau `source_ids` kosong, kembalikan `STATUS_UNVERIFIED`; selain itu kembalikan `STATUS_VERIFIED` bila quote ternormalisasi adalah substring dari gabungan teks lengkap sumber yang dirujuk `source_ids` saja (bukan semua sumber, bukan per chunk), dan `STATUS_UNVERIFIED` bila tidak. Ambil teks sumber dengan `source_texts.get(sid, "")` supaya id yang tidak dikenal (misalnya AI mengarang id) dianggap `STATUS_UNVERIFIED`, bukan `KeyError`. `verify_sections`: kembalikan daftar datar `SentenceStatus` untuk setiap kalimat di semua paragraf dengan `index` global berurutan, sehingga tidak ada kalimat yang terlewat. Ingat arti status: cuplikan ada, bukan klaim benar (11.3). Gerbang ekspor ada di Task 17c.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_verification.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/verification.py tests/test_verification.py
git commit -m "feat: deterministic snippet verification and export gate"
```

---

### Task 10: Pencarian dan penggantian penanda lintas run

**Files:**
- Create: `src/generator/document/__init__.py`, `src/generator/document/placeholders.py`
- Test: `tests/test_placeholders.py`

**Interfaces:**
- Consumes: tidak ada.
- Produces:
  - `placeholders.PLACEHOLDER_RE` (pola teks `{{...}}`)
  - `placeholders.find_names(text: str) -> list[str]`
  - `placeholders.iter_paragraphs(doc) -> Iterator[Paragraph]` (body, sel tabel, header, footer)
  - `placeholders.collect_names(doc) -> list[str]`
  - `placeholders.replace_in_paragraph(paragraph, mapping: dict[str, str]) -> list[str]` (mengembalikan nama penanda yang tergantikan)
  - `placeholders.is_standalone(paragraph, name: str) -> bool`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_placeholders.py
from docx import Document
from generator.document import placeholders

def test_replaces_split_runs_and_keeps_neighbours():
    doc = Document(); p = doc.add_paragraph()
    p.add_run("A {{JU"); p.add_run("DUL}} B")
    replaced = placeholders.replace_in_paragraph(p, {"{{JUDUL}}": "X"})
    assert replaced == ["{{JUDUL}}"]
    assert p.text == "A X B"

def test_multiple_placeholders_one_paragraph():
    doc = Document(); p = doc.add_paragraph(); p.add_run("{{NAMA}} dan {{NIM}}")
    placeholders.replace_in_paragraph(p, {"{{NAMA}}": "Budi", "{{NIM}}": "1"})
    assert p.text == "Budi dan 1"

def test_is_standalone():
    doc = Document()
    a = doc.add_paragraph("{{LOGO}}"); a.add_run("")
    b = doc.add_paragraph("lihat {{LOGO}} ini")
    assert placeholders.is_standalone(a, "{{LOGO}}") is True
    assert placeholders.is_standalone(b, "{{LOGO}}") is False

def test_collect_names_includes_table_cells():
    doc = Document(); t = doc.add_table(rows=1, cols=1)
    t.cell(0, 0).paragraphs[0].add_run("{{DOSEN}}")
    assert "{{DOSEN}}" in placeholders.collect_names(doc)
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_placeholders.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `placeholders.py`**

Untuk tiap paragraf, gabung teks seluruh `run`, cari penanda pada teks gabungan (termasuk yang terpotong antar run), lalu ganti. Teks sebelum penanda tetap di run pertama, teks sesudah penanda tetap di run terakhir, hanya run yang seluruhnya di dalam penanda yang dikosongkan; pertahankan format run pertama (9.1). Tangani beberapa penanda berbeda dalam satu paragraf. `iter_paragraphs` mencakup body, sel tabel, header, dan footer (9.2; text box dan shape tidak didukung dan dicatat di README). `is_standalone`: setelah semua penanda diganti tempat, paragraf itu hanya berisi satu penanda dan tanpa teks lain.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_placeholders.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/document/__init__.py src/generator/document/placeholders.py tests/test_placeholders.py
git commit -m "feat: cross-run placeholder search and replace"
```

---

### Task 11: Validasi template DOCX

**Files:**
- Create: `src/generator/document/template.py`
- Test: `tests/test_template.py`

**Interfaces:**
- Consumes: `placeholders` (Task 10).
- Produces:
  - `template.REQUIRED_PLACEHOLDERS`, `template.SPECIAL_PLACEHOLDERS`, `template.OPTIONAL_PLACEHOLDERS` (semua `list[str]`)
  - `template.ValidationResult` (dataclass: `missing: list[str]`, `not_standalone: list[str]`, `unknown: list[str]`, properti `is_processable: bool`)
  - `template.validate_template(path: Path) -> ValidationResult`
  - `template.load_template(path: Path) -> docx.Document`
  - `template.TemplateError(Exception)`

`SPECIAL_PLACEHOLDERS = ["{{ISI_LAPORAN}}", "{{DAFTAR_PUSTAKA}}", "{{DAFTAR_ISI}}", "{{LOGO}}"]`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_template.py
import pytest
from docx import Document
from generator.document import template

def _doc(path, lines):
    d = Document()
    for ln in lines: d.add_paragraph(ln)
    d.save(path)
    return path

def test_missing_reported(tmp_path):
    p = _doc(tmp_path / "t.docx", ["{{JUDUL}} {{NAMA}}"])
    res = template.validate_template(p)
    assert "{{DOSEN}}" in res.missing and "{{JUDUL}}" not in res.missing
    assert res.is_processable is False

def test_special_must_be_standalone(tmp_path):
    p = _doc(tmp_path / "t.docx", template.REQUIRED_PLACEHOLDERS + [])
    # ganti ISI_LAPORAN jadi tidak berdiri sendiri
    d = Document(p)
    for par in d.paragraphs:
        if par.text == "{{ISI_LAPORAN}}":
            par.text = "lihat {{ISI_LAPORAN}} di sini"
    d.save(p)
    res = template.validate_template(p)
    assert "{{ISI_LAPORAN}}" in res.not_standalone

def test_unknown_flagged_but_ok(tmp_path):
    p = _doc(tmp_path / "t.docx", template.REQUIRED_PLACEHOLDERS + ["{{FOO}}"])
    res = template.validate_template(p)
    assert "{{FOO}}" in res.unknown and res.is_processable is True

def test_all_present_is_processable(tmp_path):
    p = _doc(tmp_path / "t.docx", template.REQUIRED_PLACEHOLDERS)
    assert template.validate_template(p).is_processable is True

def test_bad_file_raises(tmp_path):
    p = tmp_path / "bad.docx"; p.write_text("bukan docx")
    with pytest.raises(template.TemplateError):
        template.load_template(p)
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_template.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `template.py`**

`load_template`: buka dengan python-docx; bungkus kegagalan menjadi `TemplateError` berpesan "File template tidak valid atau bukan .docx" (12.5). `validate_template`: kumpulkan semua nama penanda dengan `placeholders.collect_names`; `missing` = penanda wajib yang tidak ada; `not_standalone` = penanda khusus yang ada tetapi tidak berdiri sendiri (pakai `placeholders.is_standalone`, 9.4); `unknown` = penanda di luar wajib, khusus, dan opsional (9.2). `is_processable` = `not missing and not not_standalone`. Perilaku tunggal: missing atau not_standalone sama-sama ditolak dengan dialog ramah (9.3, syarat C).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_template.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/document/template.py tests/test_template.py
git commit -m "feat: template validation with required, special, and unknown placeholders"
```

---

### Task 12: Renderer DOCX (logo 5x5 cm, TOC, hanging indent, heading berlevel)

**Files:**
- Create: `src/generator/document/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `placeholders` (Task 10), `template.load_template`/`REQUIRED_PLACEHOLDERS`/`OPTIONAL_PLACEHOLDERS` (Task 11), `content.Section` dan `content.compose` (Task 8).
- Produces:
  - `renderer.render_report(template_path: Path, fields: dict[str, str], sections: list[Section], references: list[str], logo_path: Path | None, output_path: Path, labels: dict[int, str] | None = None) -> Path`
  - `renderer.TOC_FIELD_XML` (string XML field TOC Word)
  - `renderer._heading_style(doc, level: int) -> str` (kembalikan nama style Heading yang aman dipakai)

`fields` hanya berisi nilai penanda sederhana (`{{JUDUL}}`, `{{NAMA}}`, `{{NIM}}`, `{{MATA_KULIAH}}`, `{{DOSEN}}`, `{{TANGGAL}}`, dan opsional `{{TAHUN}}`, `{{PRODI}}`). Kunci penanda khusus (`{{LOGO}}`, `{{DAFTAR_ISI}}`, `{{ISI_LAPORAN}}`, `{{DAFTAR_PUSTAKA}}`) diabaikan bila ada di `fields`; keempatnya selalu ditangani renderer secara khusus.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_renderer.py
import base64
from docx import Document
from docx.shared import Cm
from generator.document import renderer, template
from generator.ai.content import Sentence, Paragraph, Section

def _tmpl(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.save(p)
    return p

def _png(path, w, h):
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    path.write_bytes(png); return path

def test_render_fills_fields_and_body(tmp_path):
    secs = [Section(1, "Pendahuluan", [Paragraph([Sentence("Isi bab.", "x", [0])])])]
    out = renderer.render_report(_tmpl(tmp_path),
        {"{{JUDUL}}": "Laporan X", "{{NAMA}}": "Budi", "{{NIM}}": "1",
         "{{MATA_KULIAH}}": "Agro", "{{DOSEN}}": "Dr. X", "{{TANGGAL}}": "2026"},
        secs, ["Santoso, B. (2020)."], None, tmp_path / "out.docx")
    doc = Document(out)
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Laporan X" in text and "{{" not in text
    assert "Pendahuluan" in text and "Isi bab." in text and "Santoso, B. (2020)." in text
    assert any(p.style.name == "Heading 1" for p in doc.paragraphs)

def test_render_places_citations_from_labels(tmp_path):
    secs = [Section(1, "Bab", [Paragraph([Sentence("Pertanian organik meningkat pesat di Indonesia.", "q", [0])])])]
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 secs, ["Santoso, B. (2020)."], None, tmp_path / "o.docx",
                                 labels={0: "(Santoso, 2020)"})
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert "Pertanian organik meningkat pesat di Indonesia (Santoso, 2020)." in text

def test_toc_field_present(tmp_path):
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], None, tmp_path / "o.docx")
    assert "TOC" in Document(out).element.xml

def test_special_placeholder_keys_in_fields_ignored(tmp_path):
    logo = _png(tmp_path / "l.png", 1, 1)
    fields = {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS}
    out = renderer.render_report(_tmpl(tmp_path), fields, [], [], logo, tmp_path / "o.docx")
    doc = Document(out)
    assert len(doc.inline_shapes) == 1
    assert "TOC" in doc.element.xml

def test_logo_square_is_5cm(tmp_path):
    logo = _png(tmp_path / "l.png", 1, 1)
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], logo, tmp_path / "o.docx")
    shape = Document(out).inline_shapes[0]
    assert shape.width == Cm(5) and shape.height == Cm(5)

def test_logo_non_square_fits_within_5cm(tmp_path):
    from PIL import Image
    logo = tmp_path / "wide.png"; Image.new("RGB", (200, 100), "black").save(logo)
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], logo, tmp_path / "o.docx")
    shape = Document(out).inline_shapes[0]
    assert shape.width == Cm(5) and shape.height <= Cm(5)

def test_bad_logo_skipped(tmp_path):
    bad = tmp_path / "l.txt"; bad.write_text("nope")
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], bad, tmp_path / "o.docx")
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert out.exists() and "{{LOGO}}" not in text and "nope" not in text

def test_missing_heading_style_falls_back(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    st = d.styles["Heading 1"].element
    st.getparent().remove(st)
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.save(p)
    secs = [Section(1, "Bab Tanpa Style", [Paragraph([Sentence("Isi bab.", "x", [0])])])]
    out = renderer.render_report(p, {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 secs, [], None, tmp_path / "o.docx")
    text = "\n".join(par.text for par in Document(out).paragraphs)
    assert "Bab Tanpa Style" in text and "Isi bab." in text

def test_missing_optional_placeholder_is_blanked(tmp_path):
    p = tmp_path / "t.docx"
    d = Document()
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.add_paragraph("Tahun {{TAHUN}} prodi {{PRODI}}")
    d.save(p)
    out = renderer.render_report(p, {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], [], None, tmp_path / "o.docx")
    text = "\n".join(par.text for par in Document(out).paragraphs)
    assert "{{" not in text and "Tahun" in text and "prodi" in text

def test_references_hanging_indent(tmp_path):
    out = renderer.render_report(_tmpl(tmp_path), {ph: "x" for ph in template.REQUIRED_PLACEHOLDERS},
                                 [], ["Santoso, B. (2020)."], None, tmp_path / "o.docx")
    doc = Document(out)
    ref = [p for p in doc.paragraphs if "Santoso, B. (2020)." in p.text][0]
    assert ref.paragraph_format.left_indent is not None
    assert ref.paragraph_format.first_line_indent is not None
    assert ref.paragraph_format.first_line_indent < 0
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_renderer.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `renderer.py`**

Muat template, ganti penanda sederhana dengan `placeholders.replace_in_paragraph` memakai `fields`. Setelah mengganti semua penanda yang punya nilai, **kosongkan penanda opsional yang tidak punya nilai** (`{{TAHUN}}`, `{{PRODI}}`) dengan menggantinya menjadi string kosong lewat fungsi yang sama, supaya penanda mentah tidak pernah tercetak (18.5, putaran 6 temuan 4). `{{LOGO}}`: bila `logo_path` ada dan bisa dibaca, sisipkan pada paragraf penanda; hitung rasio (`PIL.Image.open`) dan skala agar masuk kotak 5x5 cm tanpa memotong, lalu pusatkan (20); bila gagal (bukan gambar atau tidak ditemukan) **kosongkan paragraf penanda** dan lanjut dengan peringatan tanpa menggagalkan render (12.6, 18.5). `{{DAFTAR_ISI}}`: ganti dengan field TOC Word (`TOC_FIELD_XML`, 18.3). `{{ISI_LAPORAN}}`: ganti dengan blok: tiap `Section` menjadi paragraf Heading sesuai `level` (`level 1` ke Heading 1, `level 2` ke Heading 2) berisi `section.title`, lalu tiap `Paragraph` menjadi paragraf Normal berisi `content.compose(paragraph, labels or {})` sehingga sitasi dipasang di sini (18.1, 11.4). Tentukan style lewat `_heading_style(doc, level)`: bila style `Heading <level>` tidak ada, buat style itu (berbasis Normal, tebal) atau jatuh ke Normal tebal; jangan melempar `KeyError` dari `add_paragraph(style=...)` (18.1, putaran 6 temuan 5). `{{DAFTAR_PUSTAKA}}`: ganti dengan daftar entri `references`, tiap entri paragraf dengan hanging indent (18.4, set `left_indent` dan `first_line_indent` negatif). Kunci penanda khusus di `fields` diabaikan. Simpan ke `output_path` dan kembalikan path.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_renderer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/document/renderer.py tests/test_renderer.py
git commit -m "feat: docx renderer with fitted logo, TOC field, and hanging indent"
```

---

### Task 13: GUI shell, tab Data, worker latar, dan run.bat bootstrap

**Files:**
- Create: `src/generator/gui/__init__.py`, `src/generator/gui/app.py`, `src/generator/gui/tab_data.py`
- Create: `src/generator/gui/worker.py`
- Create: `run.bat`
- Test: `tests/test_gui_import.py`, `tests/test_run_bat.py`, `tests/test_gui_worker.py`

**Interfaces:**
- Consumes: `paths`/`config` (Task 2), `database.Database`/`Profil` (Task 3), `logging_setup` (Task 2).
- Produces:
  - `app.build_app() -> tkinter.Tk` (Notebook dengan tab Data, Template, Laporan, Pengaturan)
  - `app.main() -> None`
  - `tab_data.DataTab(parent, db)` (sub-tab Profil Mahasiswa, Dosen, Mata Kuliah, Logo dengan tombol Tambah/Ubah/Hapus)
  - `worker.run_in_thread(widget, work: Callable[[], T], on_success=None, on_error=None) -> None` (jalankan `work` di thread lain, hasil diserahkan ke callback lewat `widget.after`)
  - `worker._drain(q: queue.Queue, on_success, on_error) -> bool` (ambil satu hasil dari antrean; True bila ada)

Aturan responsivitas (putaran 6, temuan 6): operasi lama (OCR, panggilan AI per batch, ambil web, render) tidak boleh dijalankan di thread utama Tkinter. Semua pemanggilan itu lewat `worker.run_in_thread`; widget hanya disentuh dari callback `on_success`/`on_error` yang dijalankan `after`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_gui_import.py
def test_gui_imports_without_tk_root():
    import generator.gui.app as app
    import generator.gui.tab_data as tab_data
    assert hasattr(app, "build_app") and hasattr(app, "main")
    assert hasattr(tab_data, "DataTab")
```

```python
# tests/test_run_bat.py
from pathlib import Path

def test_run_bat_bootstraps_and_launches():
    txt = Path("run.bat").read_text(encoding="utf-8").lower()
    assert "python" in txt
    assert "venv" in txt
    assert "requirements.txt" in txt
    assert "generator.gui.app" in txt
    assert "ocr" in txt or "onnx" in txt  # pesan progres dependensi besar (16)
```

```python
# tests/test_gui_worker.py
import queue
import threading
import time
from generator.gui import worker

class FakeWidget:
    def __init__(self):
        self.after_ms = []
    def after(self, ms, fn):
        self.after_ms.append(ms)
        time.sleep(0.001)  # beri kesempatan thread pekerja menyelesaikan hasil
        fn()

def test_drain_calls_success():
    q = queue.Queue(); q.put(("ok", 7)); got = []
    assert worker._drain(q, got.append, None) is True
    assert got == [7]

def test_drain_returns_false_when_empty():
    assert worker._drain(queue.Queue(), lambda v: None, None) is False

def test_run_in_thread_delivers_result_via_after():
    w = FakeWidget(); done = threading.Event(); box = []
    def on_success(v): box.append(v); done.set()
    worker.run_in_thread(w, lambda: 42, on_success=on_success)
    assert done.wait(2.0) and box == [42]
    assert w.after_ms  # pembaruan UI lewat after, bukan thread pekerja
```

Catatan keandalan: `FakeWidget.after` memanggil callback secara sinkron, jadi tes `test_run_in_thread_delivers_result_via_after` bergantung pada thread pekerja menyelesaikan hasil dalam beberapa putaran polling (bisa dalam rekursi). Tes ini hampir pasti lulus, tetapi rapuh. Bila gagal, periksa tes dan `FakeWidget` ini lebih dulu sebelum menyalahkan `worker.py`; `test_drain_calls_success` dan `test_drain_returns_false_when_empty` yang deterministik adalah bukti utama logika `_drain`.

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py tests/test_run_bat.py tests/test_gui_worker.py -v`
Expected: FAIL, modul dan run.bat belum ada.

- [ ] **Step 3: Implementasikan GUI shell, tab Data, worker, dan run.bat**

`app.build_app()`: panggil `paths.ensure_dirs()`; bila `PathsError`, tampilkan dialog minta user memilih folder lalu `paths.set_data_dir(pilihan)` (12.8); pasang `logging_setup.setup_logging(paths.LOG_PATH)`; **buat `db = database.Database(paths.DB_PATH)` lalu panggil `db.init_schema()`** (satu-satunya tempat pembuatan koneksi; `db` yang sama diteruskan ke tiap tab), buat `Tk`, `ttk.Notebook`, tambahkan `DataTab` dan (nanti) tab lain via import bertahap agar task ini tetap hijau. Bila `config.load_config(paths.CONFIG_PATH).ai_api_key` kosong, tampilkan petunjuk menuju tab Pengaturan, tanpa crash (10, 15). `app.main()` memanggil `build_app()` lalu `mainloop()`; tambahkan blok `if __name__ == "__main__": main()` di akhir `app.py` supaya `python -m generator.gui.app` benar-benar berjalan. `DataTab`: empat sub-tab dengan listbox, entri, dan tombol Tambah, Ubah, Hapus; Logo memakai `filedialog.askopenfilename`.

`worker.py`: `run_in_thread(widget, work, on_success=None, on_error=None)` menjalankan `work()` di `threading.Thread(daemon=True)`, menaruh hasil `("ok", nilai)` atau `("err", exception)` ke `queue.Queue`, lalu memanggil `_poll` yang mengambil hasil lewat `_drain` dan menjadwalkan ulang dirinya dengan `widget.after(50, ...)` selama antrean kosong. `_drain(q, on_success, on_error)` mengembalikan `False` bila antrean kosong, selain itu memanggil `on_success(nilai)` atau `on_error(exception)` dan mengembalikan `True`. UI tidak pernah disentuh dari dalam thread pekerja. Tab Laporan (Task 16, 17a, 17b, 17c) memakai `run_in_thread` untuk OCR, panggilan AI, ambil web, dan render.

`run.bat` sesuai bagian 16: (1) deteksi Python 3.12, bila tidak ada tampilkan tautan pemasangan dan berhenti rapi; (2) buat virtual environment di folder aplikasi bila belum ada; (3) pasang dependensi dari `requirements.txt` saat pertama kali; (4) tampilkan pesan progres saat mengunduh dan memasang dependensi, khususnya OCR dan mesin ONNX; (5) jalankan `.venv\Scripts\python -m generator.gui.app` dengan `PYTHONPATH` diarahkan ke `src`. Tidak ada `bootstrap.bat`.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py tests/test_run_bat.py tests/test_gui_worker.py -v`
Expected: PASS.

- [ ] **Step 4b: Uji manual singkat sebelum lanjut ke tab lain (wajib)**

Tes otomatis task ini hanya memeriksa "atribut ada", jadi perilaku GUI belum terbukti. Jalankan `run.bat` sekali dan klik-klik sebentar: buka tab Data, tambah satu dosen, tambah satu mata kuliah, muat satu logo, tutup aplikasi. Pastikan jendela muncul, tidak crash, dan data tersimpan setelah dibuka ulang. **Catat hasilnya.** Bila ada yang gagal, perbaiki di sini sebelum menambah tab berikutnya; jangan lanjut ke Task 14 dengan GUI yang belum pernah dijalankan.

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui run.bat tests/test_gui_import.py tests/test_run_bat.py tests/test_gui_worker.py
git commit -m "feat: gui shell, data tab, background worker, and run.bat bootstrap launcher"
```

---

### Task 14: GUI, tab Pengaturan (AI)

**Files:**
- Create: `src/generator/gui/tab_settings.py`
- Modify: `src/generator/gui/app.py` (pasang `SettingsTab`)
- Test: `tests/test_gui_import.py` (tambah assertion)

**Interfaces:**
- Consumes: `config.load_config`/`save_config`/`Config` (Task 2), `client.AIClient`/`check_connection` (Task 5), `paths.CONFIG_PATH` (Task 2).
- Produces:
  - `tab_settings.SettingsTab(parent, config_path)` widget: entri URL endpoint, API key, nama model, temperatur; tombol Simpan; tombol Tes koneksi

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_settings_tab_exists():
    import generator.gui.tab_settings as t
    assert hasattr(t, "SettingsTab")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py::test_settings_tab_exists -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `tab_settings.py`**

Isi field dari `config.load_config(config_path)`. Simpan memakai `config.save_config` (menulis `data/config.json`, diabaikan git). Tombol Tes koneksi memanggil `client.check_connection` dan menampilkan hasil ramah ("Koneksi berhasil" atau "Gagal: alasan singkat"). Tampilkan catatan: API key tersimpan polos (belum terenkripsi) dan teks sumber dikirim ke layanan AI sesuai endpoint (15, 20). Jangan menulis API key ke log.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui/tab_settings.py src/generator/gui/app.py tests/test_gui_import.py
git commit -m "feat: settings tab with AI connection test"
```

---

### Task 15: GUI, tab Kelola Template

**Files:**
- Create: `src/generator/gui/tab_template.py`
- Modify: `src/generator/gui/app.py` (pasang `TemplateTab`)
- Test: `tests/test_gui_import.py` (tambah assertion)

**Interfaces:**
- Consumes: `database.Database`/`Template` (Task 3), `template.validate_template`/`TemplateError` (Task 11), `paths.TEMPLATES_DIR` (Task 2).
- Produces:
  - `tab_template.TemplateTab(parent, db)` widget: daftar template dengan status validasi yang **dihitung ulang saat daftar ditampilkan** (`validate_template` atas path tersimpan), tombol Tambah (upload DOCX), Hapus

Status validasi tidak disimpan sebagai kolom database (menjawab putaran 6). `Template` hanya menyimpan `nama`, `deskripsi`, `path` (bagian 7).

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_template_tab_exists():
    import generator.gui.tab_template as t
    assert hasattr(t, "TemplateTab")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py::test_template_tab_exists -v`
Expected: FAIL.

- [ ] **Step 3: Implementasikan `tab_template.py`**

Tombol Tambah: `filedialog.askopenfilename` (.docx), panggil `validate_template`. Bila `missing` atau `not_standalone` tidak kosong, tampilkan `messagebox.showwarning` yang menyebut penanda mana dan **tetap izinkan simpan** dengan status "tidak lengkap" (9.3). Bila `unknown` tidak kosong, sebutkan penanda tak dikenal itu. Salin file ke `TEMPLATES_DIR`, simpan metadata (`nama`, `deskripsi`, `path`) ke database; jangan simpan kolom status, karena status dihitung ulang dengan `validate_template` saat daftar ditampilkan. Daftar menampilkan nama dan status hasil hitung itu. Penolakan pemakaian template tidak lengkap terjadi belakangan, saat template dipilih di tab Buat Laporan (Task 16), bukan saat disimpan di sini (9.3, putaran 6). Tangani `TemplateError` dengan dialog ramah (12.5).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui/tab_template.py src/generator/gui/app.py tests/test_gui_import.py
git commit -m "feat: template management tab with validation warnings"
```

---

### Task 16: Draf sementara dan tab Buat Laporan bagian 1 (sumber, OCR fallback, koreksi metadata)

**Files:**
- Create: `src/generator/drafts.py`
- Create: `src/generator/gui/tab_report.py`
- Modify: `src/generator/gui/app.py` (pasang `ReportTab`)
- Test: `tests/test_drafts.py`, `tests/test_gui_import.py` (tambah assertion)

**Interfaces:**
- Consumes: `paths.DRAFTS_DIR` (Task 2), `database` (Task 3), `pdf_reader`/`web_reader` (Task 4), `config`/`client` (Task 2, 5), `bibliography` (Task 7), `citation.Source` (Task 6).
- Produces:
  - `drafts.DraftState` (dataclass: `draft_id: str`, `fields: dict`, `sources: list[dict]`, `sections: list[dict]`, `done: list[str] = field(default_factory=list)`) (`done` berisi `uid` kalimat, bukan nomor posisi; tidak ada `manual_edits` karena teks dan asal tersimpan di `sections`)
  - `drafts.save_draft(state: DraftState) -> Path`, `drafts.load_draft(draft_id: str) -> DraftState`, `drafts.list_drafts() -> list[str]`, `drafts.delete_draft(draft_id: str) -> None`
  - `tab_report.ReportTab(parent, db)` dengan: pilih template, pilih profil mahasiswa, dosen, mata kuliah, logo; kotak judul; kotak outline bab; tombol **Usulkan Outline** (memakai `content.suggest_outline`, Task 8b); tombol Tambah Sumber PDF, Tambah Sumber Link, Tempel Teks Manual; daftar sumber; formulir koreksi metadata per sumber (metadata umum, plus per penulis: nama keluarga, nama depan, penanda organisasi, singkatan)

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_drafts.py
from generator import drafts

def test_draft_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    state = drafts.DraftState("d1", {"judul": "X"}, [{"title": "T"}], [])
    drafts.save_draft(state)
    assert drafts.load_draft("d1").fields["judul"] == "X"
    assert "d1" in drafts.list_drafts()
    drafts.delete_draft("d1")
    assert drafts.list_drafts() == []

def test_draft_roundtrips_done_marks(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.save_draft(drafts.DraftState("d2", {}, [], [], done=["a1", "b2"]))
    assert drafts.load_draft("d2").done == ["a1", "b2"]

def test_load_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    assert drafts.load_draft("nope") is None
```

```python
# tests/test_gui_import.py  (tambahan)
def test_report_tab_exists():
    import generator.gui.tab_report as t
    assert hasattr(t, "ReportTab")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_drafts.py tests/test_gui_import.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `drafts.py` dan bagian sumber pada `tab_report.py`**

`drafts.py`: simpan tiap draf sebagai JSON di `paths.DRAFTS_DIR / f"{draft_id}.json"`; `save/load/list/delete`. Teks sumber hanya ikut di dalam file draf, bukan database (8). Sertakan juga `done` (daftar `uid` kalimat yang ditandai selesai) supaya tanda selesai tidak hilang saat aplikasi ditutup. Saat menyimpan `sections`, tulis juga `uid`, `origin`, dan `citation` tiap kalimat, dan saat memuatnya bangun ulang `Sentence` dengan nilai yang sama; ini yang menjaga `done` tetap menempel pada kalimat yang benar walau urutan berubah, dan menjaga asal manual tidak hilang (8, 19). Tidak ada field `manual_edits`; teks dan asal memang sudah ada di `sections`. `load_draft` mengembalikan `None` bila tidak ada.

`ReportTab` bagian ini: pemilih template (panggil `validate_template` saat dipilih; bila `missing` atau `not_standalone` tidak kosong, tampilkan dialog ramah dan **jangan lanjutkan** sampai user memilih template lain, 9.3, putaran 6), profil mahasiswa, dosen, mata kuliah, logo (Combobox dari database), kotak judul, kotak outline. Tombol **Usulkan Outline** muncul bila kotak outline kosong: panggil `content.suggest_outline` (Task 8b) di latar lewat `worker.run_in_thread` dan isi kotak outline dengan hasilnya untuk disetujui user. Tambah Sumber PDF: `filedialog`, baca dengan `extract_text_or_ocr` di latar lewat `worker.run_in_thread` supaya jendela tidak membeku saat OCR; bila `SourceReadError` menandakan scan atau OCR gagal, tawarkan tombol Tempel Teks Manual untuk sumber itu (12.1), sumber lain tetap diproses (12.2, kriteria 4). Tambah Sumber Link: `fetch_text` di latar; bila gagal, pesan per sumber dan opsi tempel manual. Untuk tiap sumber, gabung metadata dokumen (`extract_metadata`/`fetch_metadata`) dengan hasil AI (`extract_source` + `merge_metadata`), juga di latar. Tampilkan formulir koreksi metadata: `year`, `title`, `container`, `doi`, `url`, dan untuk tiap penulis empat bidang yang dapat diedit user yaitu nama keluarga, nama depan, penanda organisasi, dan singkatan. Kode tidak menebak pemisahan nama Indonesia; nilai awal dari AI hanyalah usulan (12.4, syarat B). Simpan/segarkan draf lewat `drafts` setiap kali sumber berubah. Semua aksi dibungkus penanganan error dengan `messagebox` ramah, dan semua operasi lama memakai `worker.run_in_thread` (bagian 10, putaran 6).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_drafts.py tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/drafts.py src/generator/gui/tab_report.py src/generator/gui/app.py tests/test_drafts.py tests/test_gui_import.py
git commit -m "feat: drafts storage and report tab source intake with metadata correction"
```

---

### Task 17a: report.py inti, tombol Generate, dan tampilan status

**Files:**
- Create: `src/generator/report.py`
- Modify: `src/generator/gui/tab_report.py`, `src/generator/gui/app.py`
- Test: `tests/test_report.py`, `tests/test_gui_import.py`

**Interfaces:**
- Consumes: `content` (Task 8), `verification` (Task 9), `citation` (Task 6), `drafts` (Task 16), `worker` (Task 13).
- Produces:
  - `report.can_export(statuses: list[SentenceStatus], done: frozenset[str] = frozenset()) -> tuple[bool, str]` (`done` berisi `uid` kalimat)
  - `report.pending(statuses: list[SentenceStatus], done: frozenset[str]) -> list[int]` (hanya kalimat yang statusnya bukan `STATUS_VERIFIED` dan `uid`-nya belum ada di `done`)
  - `report.non_factual_uids(statuses: list[SentenceStatus]) -> list[str]`
  - `report.references_for(sources: list[Source], cited_ids: set[int]) -> list[str]`
  - `report.labels_for(sources: list[Source], cited_ids: set[int]) -> dict[int, str]` (kunci = indeks asli sumber, urutan kunci = urutan sitasi/reference)
  - `report.uncited_ids(sources: list[Source], cited_ids: set[int]) -> list[int]`
  - `report.cited_ids(statuses: list[SentenceStatus]) -> set[int]` (indeks sumber yang benar-benar dirujuk kalimat)
  - `tab_report.ReportTab` lanjutan: tombol Generate (dijalankan di latar lewat `worker.run_in_thread`), tampilan kalimat dengan status terverifikasi / tidak terverifikasi / bukan klaim faktual

Task ini hanya berisi logika murni `report.py` dan tombol Generate beserta tampilan status. Edit manual, tanda selesai, dan ekspor dipisah ke 17b dan 17c supaya tiap task kecil dan bisa ditest sendiri.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_report.py
from generator.report import (can_export, pending, references_for, labels_for,
    uncited_ids, non_factual_uids, cited_ids)
from generator.verification import verify_sections, STATUS_VERIFIED
from generator.ai.content import Sentence, Paragraph, Section
from generator.ai.citation import Author, Source

GOOD = "pertanian organik di indonesia sangat penting bagi petani"

def test_can_export_blocks_when_unverified():
    s = Section(1, "B", [Paragraph([Sentence("x", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: "teks lain sama sekali berbeda dan tidak berkaitan lagi"})
    ok, msg = can_export(st)
    assert ok is False and msg

def test_can_export_allows_when_verified():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert can_export(st) == (True, "")

def test_pending_excludes_verified_sentences():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0]),
                                    Sentence("y", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: GOOD})
    assert st[0].status == STATUS_VERIFIED
    assert pending(st, frozenset()) == [1]

def test_non_factual_blocks_until_marked_done():
    s = Section(1, "B", [Paragraph([Sentence("Bab ini membahas.", is_factual=False)])])
    st = verify_sections([s], {})
    assert can_export(st)[0] is False
    assert can_export(st, done=frozenset({st[0].sentence.uid}))[0] is True

def test_done_keyed_by_stable_uid_survives_insertion():
    a = Sentence("kalimat asli.", is_factual=False)
    st = verify_sections([Section(1, "B", [Paragraph([a])])], {})
    done = frozenset({st[0].sentence.uid})
    assert can_export(st, done=done)[0] is True

    st2 = verify_sections([Section(1, "B", [Paragraph([Sentence("kalimat baru.", is_factual=False), a])])], {})
    assert st2[1].sentence.uid == a.uid
    assert pending(st2, done) == [0]

def test_non_factual_uids_for_bulk_mark():
    s = Section(1, "B", [Paragraph([Sentence("pengantar.", is_factual=False),
                                    Sentence("klaim.", GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert non_factual_uids(st) == [st[0].sentence.uid]
    assert can_export(st, done=frozenset(non_factual_uids(st)))[0] is True

def test_cited_ids_collects_referenced_sources():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0, 1]),
                                    Sentence("y", is_factual=False)])])
    st = verify_sections([s], {0: GOOD})
    assert cited_ids(st) == {0, 1}

def test_cited_ids_ignores_citation_suppressed():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0], citation=False),
                                    Sentence("y", GOOD, [1])])])
    st = verify_sections([s], {0: GOOD, 1: GOOD})
    assert cited_ids(st) == {1}

def test_references_only_cited_sources():
    src = [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "U", "J")]
    refs = references_for(src, {0})
    assert len(refs) == 1 and uncited_ids(src, {0}) == [1]

def test_labels_keyed_by_original_source_index():
    src = [Source([Author("Zed")], "2020", "Z", "J"),
           Source([Author("Abadi", "T")], "2020", "A", "J")]
    labels = labels_for(src, {0, 1})
    assert set(labels) == {0, 1}
    assert labels[0].startswith("(Zed") and labels[1].startswith("(Abadi")

def test_labels_no_suffix_from_uncited_source():
    src = [Source([Author("Santoso", "Budi")], "2020", "A", "J"),
           Source([Author("Santoso", "Budi")], "2020", "B", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "C", "J")]
    labels = labels_for(src, {0, 2})
    assert labels[0] == "(Santoso, 2020)" and labels[2] == "(Wijaya, 2021)"
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_report.py -v`
Expected: FAIL, modul belum ada.

- [ ] **Step 3: Implementasikan `report.py` (inti) dan tombol Generate**

`report.py`: `can_export` mengembalikan `(True, "")` bila setiap `SentenceStatus` berstatus `STATUS_VERIFIED` atau `uid` kalimatnya ada di `done`; selain itu `(False, pesan)` yang menyebut berapa kalimat belum selesai (11.5). `pending` mengembalikan `index` kalimat yang statusnya **bukan** `STATUS_VERIFIED` **dan** `uid`-nya belum ada di `done`, supaya kalimat terverifikasi tidak ikut dihitung tertunda (menjawab putaran 6, temuan 3). `non_factual_uids` mengembalikan `uid` semua kalimat berstatus `STATUS_NON_FACTUAL`. `cited_ids` mengumpulkan `source_ids` kalimat yang `is_factual` benar **dan** `citation` benar, yaitu tepat kalimat yang akan mendapat sitasi dari `compose`; kalimat non-faktual dan kalimat yang sitasinya dimatikan user tidak memaksa sumbernya muncul di daftar pustaka (keputusan dibuat di sini, menjawab putaran 6). `labels_for` mengembalikan `{l.source_index: l.in_text for l in citation.order_and_label(sources, cite=cited_ids)}`; kunci adalah indeks asli sumber, bukan posisi hasil pengurutan alfabetis, supaya cocok dengan `source_ids` dari AI, dan urutan kunci mengikuti urutan reference. `references_for` memakai `order_and_label(sources, cite=cited_ids)` lalu mengambil `.reference`; karena hanya sumber yang dikutip yang masuk, sumber tak dikutip tidak bisa memicu sufiks a/b/c. `uncited_ids` mengembalikan indeks sumber yang dimasukkan tapi tidak dikutip untuk ditampilkan sebagai peringatan (11.4).

`tab_report.py` (bagian Generate): tombol Generate menjalankan `content.generate_sections` di latar lewat `worker.run_in_thread` supaya jendela tidak membeku (putaran 6), lalu `verification.verify_sections` dan menampilkan tiap kalimat dengan statusnya (terverifikasi, tidak terverifikasi, bukan klaim faktual) memakai penanda jelas. Simpan hasil ke draf (`drafts.save_draft`). Semua aksi dibungkus penanganan error dengan `messagebox` ramah.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_report.py tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/report.py src/generator/gui/tab_report.py src/generator/gui/app.py tests/test_report.py tests/test_gui_import.py
git commit -m "feat: report core and generation with per-sentence status display"
```

---

### Task 17b: Edit manual, tandai selesai, pulihkan sitasi, dan parafrase

**Files:**
- Modify: `src/generator/report.py`, `src/generator/gui/tab_report.py`
- Test: `tests/test_report_edit.py`, `tests/test_gui_import.py`

**Interfaces:**
- Consumes: `content` (Task 8, 8b), `verification` (Task 9), `worker` (Task 13).
- Produces:
  - `report.apply_manual_edit(sentence: Sentence, new_text: str) -> Sentence` (kalimat baru `origin="manual"` dengan `uid` dan `source_ids` tetap)
  - `report.restore_citation(sentence: Sentence) -> Sentence` (kalimat dengan `citation=True`)
  - `tab_report.ReportTab` lanjutan: area edit manual, tombol Tandai selesai, tombol Tandai semua bukan klaim faktual selesai, tombol Pulihkan sitasi, tombol Parafrase

Aturan model edit manual ada di bagian 19: kalimat manual selalu `tidak terverifikasi` sampai ditandai selesai.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_report_edit.py
from generator import report
from generator.ai.content import Sentence
from generator.verification import verify_sentence, STATUS_UNVERIFIED

GOOD = "pertanian organik di indonesia sangat penting bagi petani"

def test_apply_manual_edit_marks_manual_and_keeps_uid_and_sources():
    s = Sentence("asli.", "q", [0])
    s2 = report.apply_manual_edit(s, "diubah manual.")
    assert s2.origin == "manual" and s2.uid == s.uid and s2.source_ids == [0]
    assert s2.text == "diubah manual."

def test_manual_edit_is_unverified():
    s = report.apply_manual_edit(Sentence("x", GOOD, [0]), "diubah manual.")
    assert verify_sentence(s, {0: GOOD}) == STATUS_UNVERIFIED

def test_restore_citation_sets_flag():
    s = Sentence("x.", "q", [0], citation=False)
    assert report.restore_citation(s).citation is True
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_report_edit.py -v`
Expected: FAIL, fungsi belum ada.

- [ ] **Step 3: Implementasikan `report.py` (edit) dan UI-nya**

`report.apply_manual_edit`: kembalikan `Sentence` baru dengan `text=new_text`, menyalin `quote`, `source_ids`, `is_factual`, `citation`, dan `uid` lama, serta `origin="manual"`. `report.restore_citation`: kembalikan salinan kalimat dengan `citation=True`. Keduanya tidak mengubah objek lama.

`tab_report.py` (bagian edit): tiap **kalimat** ditampilkan dengan **satu kotak teks sendiri** (bukan satu area untuk seluruh paragraf), sehingga pemetaan teks ke kalimat selalu satu banding satu. Menyimpan kotak itu membangun ulang kalimat lewat `report.apply_manual_edit(sentence, teks_baru)` sehingga ditandai manual dan tidak terverifikasi (19). Tombol Tandai selesai menambahkan `uid` kalimat ke himpunan `done`, berlaku untuk teks manual dan kalimat bukan klaim faktual; tombol Tandai semua bukan klaim faktual selesai menambahkan seluruh `report.non_factual_uids(statuses)` sekaligus; buka/tutup sitasi memakai `report.restore_citation`; simpan `done` dan `sections` (termasuk `origin`/`citation`) ke draf (`drafts.save_draft`) dan muat kembali saat draf dibuka supaya bertahan antar sesi; ini yang mencegah gerbang ekspor terblokir selamanya (19). Tombol Parafrase bekerja pada kalimat terpilih: panggil `content.paraphrase` di latar lewat `worker.run_in_thread`, lalu jalankan ulang `verification.verify_sections` atas bagian yang berubah. Peringatkan penanda tak dikenal sebelum ekspor (9.2). Semua aksi dibungkus penanganan error dengan `messagebox` ramah.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_report_edit.py tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/report.py src/generator/gui/tab_report.py tests/test_report_edit.py tests/test_gui_import.py
git commit -m "feat: manual edit, done marks, citation restore, and ai paraphrase"
```

---

### Task 17c: Gerbang ekspor, isi fields, dan simpan DOCX

**Files:**
- Modify: `src/generator/report.py`, `src/generator/gui/tab_report.py`, `src/generator/gui/app.py`
- Test: `tests/test_report_export.py`

**Interfaces:**
- Consumes: `report` (17a, 17b), `renderer` (Task 12), `drafts` (Task 16), `paths`/`logging_setup` (Task 2), `database` (Task 3), `worker` (Task 13).
- Produces:
  - `report.format_tanggal(d: date) -> str` (bahasa Indonesia, mis. "18 Oktober 2026")
  - `report.build_fields(judul: str, profile: dict, dosen: str, mata_kuliah: str, tanggal: date) -> dict[str, str]` (penanda wajib selalu ada; penanda opsional hanya bila nilainya tidak kosong)
  - `tab_report.ReportTab` lanjutan: tombol Simpan DOCX dengan gerbang ekspor

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_report_export.py
from datetime import date
from generator import report

def test_format_tanggal_indonesian():
    assert report.format_tanggal(date(2026, 10, 18)) == "18 Oktober 2026"

def test_build_fields_fills_placeholders():
    f = report.build_fields("Judul", {"nama": "Budi", "nim": "1", "prodi": "Agro"},
                            "Dr. X", "Agronomi", date(2026, 10, 18))
    assert f["{{JUDUL}}"] == "Judul" and f["{{NAMA}}"] == "Budi"
    assert f["{{NIM}}"] == "1" and f["{{PRODI}}"] == "Agro"
    assert f["{{DOSEN}}"] == "Dr. X" and f["{{MATA_KULIAH}}"] == "Agronomi"
    assert f["{{TANGGAL}}"] == "18 Oktober 2026" and f["{{TAHUN}}"] == "2026"

def test_build_fields_omits_empty_optional():
    f = report.build_fields("J", {"nama": "B", "nim": "1", "prodi": ""},
                            "D", "M", date(2026, 1, 2))
    assert "{{PRODI}}" not in f  # renderer mengosongkan penandanya (18.5)
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_report_export.py -v`
Expected: FAIL, fungsi belum ada.

- [ ] **Step 3: Implementasikan pengisian fields dan tombol Simpan DOCX**

`report.format_tanggal` memakai tabel nama bulan Indonesia ("Januari" sampai "Desember") dan mengembalikan `"<hari> <Bulan> <tahun>"` (18.5). `report.build_fields` mengisi `{{JUDUL}}`, `{{NAMA}}`, `{{NIM}}`, `{{MATA_KULIAH}}`, `{{DOSEN}}`, `{{TANGGAL}}`, `{{TAHUN}}`, dan `{{PRODI}}`; `{{PRODI}}` dan penanda opsional lain hanya dimasukkan bila nilainya tidak kosong, sehingga renderer mengosongkan penandanya dan tidak pernah ada penanda mentah tercetak (18.5, putaran 6).

`tab_report.py` (bagian ekspor): tombol Simpan DOCX memakai `report.cited_ids(statuses)` untuk menghitung `labels` (`report.labels_for`) dan `references` (`report.references_for`), memanggil `report.can_export(statuses, done)`; bila terblokir, `messagebox.askyesno` untuk konfirmasi eksplisit dan catat status ke log (`logging_setup`) sebelum lanjut (11.5). Susun `sections` (kalimat apa adanya, biarkan renderer memasang sitasi lewat `content.compose`), lalu panggil `renderer.render_report(template_path, report.build_fields(...), sections, references, logo_path, paths.OUTPUT_DIR / nama_file, labels=labels)` di latar lewat `worker.run_in_thread` supaya render tidak membekukan jendela. Setelah sukses, `drafts.delete_draft` (8, kriteria 10). Peringatkan penanda tak dikenal sebelum ekspor (9.2). Semua aksi dibungkus penanganan error dengan `messagebox` ramah.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `.venv\Scripts\python -m pytest tests/test_report_export.py tests/test_gui_import.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generator/report.py src/generator/gui/tab_report.py src/generator/gui/app.py tests/test_report_export.py tests/test_gui_import.py
git commit -m "feat: export gate, placeholder fields, and gated docx save"
```

---

### Task 18: README, wiring akhir, dan uji end-to-end

**Files:**
- Create: `README.md`
- Modify: `src/generator/gui/app.py` (pastikan keempat tab terpasang)
- Test: `tests/test_e2e_render.py`, `tests/test_e2e_pipeline.py`

**Interfaces:**
- Consumes: seluruh task sebelumnya.
- Produces: dokumentasi pemakaian, format template, dan konfigurasi AI.

- [ ] **Step 1: Tulis tes end-to-end yang gagal**

```python
# tests/test_e2e_render.py
from docx import Document
from generator.document import renderer, template
from generator.ai.content import Sentence, Paragraph, Section

def test_full_template_produces_clean_report(tmp_path):
    p = tmp_path / "t.docx"; d = Document()
    for ph in template.REQUIRED_PLACEHOLDERS: d.add_paragraph(ph)
    d.save(p)
    secs = [Section(1, "Bab Satu", [Paragraph([Sentence("Isi.", "x", [0])])])]
    out = renderer.render_report(p,
        {"{{JUDUL}}": "Laporan", "{{NAMA}}": "Budi", "{{NIM}}": "1",
         "{{MATA_KULIAH}}": "Agro", "{{DOSEN}}": "Dr. X", "{{TANGGAL}}": "2026"},
        secs, ["Ref."], None, tmp_path / "o.docx")
    text = "\n".join(par.text for par in Document(out).paragraphs)
    assert "{{" not in text and "Laporan" in text and "Ref." in text and "Bab Satu" in text
```

```python
# tests/test_e2e_pipeline.py
from generator.ai.content import generate_sections, compose
from generator.ai.citation import Author, order_and_label, Source
from generator.verification import verify_sections, STATUS_VERIFIED

class FakeClient:
    def chat(self, messages, json_mode=False):
        return ('{"sections":[{"level":1,"title":"Bab","paragraphs":[{"sentences":[{"text":'
                '"Pertanian organik meningkat pesat di Indonesia.","quote":'
                '"pertanian organik meningkat pesat di indonesia sangat penting","source_ids":[0],"is_factual":true}]}]}]}')

def test_pipeline_is_grounded_and_verified():
    src = [Source([Author("Zed")], "2020", "T", "J"),
           Source([Author("Abadi", "T")], "2021", "U", "J")]
    texts = {0: "laporan pertanian organik meningkat pesat di indonesia sangat penting"}
    secs = generate_sections("tema", ["Bab"], src, [texts[0], "teks sumber kedua"], FakeClient())
    statuses = verify_sections(secs, texts)
    assert all(s.status == STATUS_VERIFIED for s in statuses)
    labels = {l.source_index: l.in_text for l in order_and_label(src, cite={0})}
    out = compose(secs[0].paragraphs[0], labels)
    assert labels[0].startswith("(Zed") and out.endswith("(Zed, 2020).")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `.venv\Scripts\python -m pytest tests/test_e2e_render.py tests/test_e2e_pipeline.py -v`
Expected: FAIL bila ada penanda yang tidak tergantikan atau sitasi tidak terpasang; bila lulus, itu bukti end-to-end.

- [ ] **Step 3: Tulis `README.md`**

Isi: cara instal (`run.bat`, atau `.venv\Scripts\python -m pip install -r requirements.txt`), cara jalan (klik `run.bat`), cara mengatur AI di tab Pengaturan (endpoint, api key, model, temperatur; API key tersimpan polos di `data/config.json`, diabaikan git, tidak pernah ditulis ke log), pemberitahuan privasi (teks sumber dikirim ke layanan AI, 20), **panduan format template** (daftar penanda wajib, opsional, khusus yang harus berdiri sendiri, penanganan bila penanda hilang atau bercampur teks, penanda tak dikenal, batasan text box dan shape tidak didukung), arti tiga status kalimat (terverifikasi, tidak terverifikasi, bukan klaim faktual) dan aturan bahwa ekspor diblokir sampai kalimat yang belum selesai ditandai selesai, catatan bahwa beberapa sumber dalam satu kalimat digabung dalam satu tanda kurung dipisah titik koma sesuai APA 7, catatan OCR (kualitas bisa kurang akurat sehingga lebih banyak kalimat ditandai tidak terverifikasi, 12.1), catatan bahwa model OCR diunduh saat pertama kali menjalankan OCR sehingga butuh internet dan cache disimpan di `data/`, catatan bahwa sumber panjang diproses per batch (12.3), catatan update field TOC (klik kanan lalu Update Field, 18.3), catatan bahwa template tidak lengkap boleh disimpan tetapi tidak bisa dipakai sampai diperbaiki (9.3), catatan bahwa template tanpa style Heading tetap menghasilkan DOCX (18.1), catatan bahwa operasi lama berjalan di latar sehingga jendela tetap responsif, **batasan singkatan organisasi** (versi ini menampilkan `Nama Penuh [Singkatan]` di semua kemunculan, belum beralih ke singkatan saja setelah sitasi pertama seperti 17.1), catatan bahwa `is_factual` ditentukan AI sehingga user tetap penjaga terakhir (kalimat faktual yang salah ditandai non-faktual bisa lolos bila user menandai selesai tanpa membaca), catatan bahwa kualitas isi bisa menurun pada PDF sangat panjang karena tiap batch menulis bab yang sama dari potongan berbeda lalu digabung (12.3), dan bagian troubleshooting.

- [ ] **Step 4: Jalankan seluruh tes**

Run: `.venv\Scripts\python -m pytest -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add README.md src/generator/gui/app.py tests/test_e2e_render.py tests/test_e2e_pipeline.py
git commit -m "docs: readme and template guide; test: end-to-end render and pipeline"
```

---

## Catatan Eksekusi

- Model AI diisi user di tab Pengaturan; tidak ada `config.example.json`. Bila kredensial AI belum ada, bagian AI menampilkan pesan ramah; bagian non-AI (database, template, verifikasi, render) tetap bisa diuji.
- Mulai dari Task 0 (git init, venv, pip) sebelum Task 1, supaya `.venv\Scripts\python -m pip install` dan `git commit` di Task 1 punya pijakan.
- Selalu pakai `.venv\Scripts\python`; jangan bergantung pada `activate` yang tidak bertahan antar panggilan shell.
- Kerjakan satu task per giliran. Jalankan `.venv\Scripts\python -m pytest` sebelum tiap commit, dan **berhenti bila tes gagal**; jangan lanjut ke task berikutnya atau menandai selesai tanpa menjalankan tes. Jangan menggabungkan task GUI (13, 14, 15, 16, 17a, 17b, 17c).
- Setelah Task 13 (GUI shell) selesai, jalankan `run.bat` dan klik-klik sebentar secara manual sebelum lanjut ke Task 14, karena tes GUI task itu baru memeriksa "atribut ada".
- OCR adalah task pertama (1) supaya kualitas aksara Indonesia terbukti sebelum `requirements.txt` dikunci. Bila OCR ternyata tidak memadai, hentikan dan diskusikan sebelum lanjut. Jangan menebak API rapidocr: catat bentuk keluaran asli `RapidOCR()(image)` lebih dulu. Model OCR diunduh saat pertama kali jalan, jadi butuh internet.
- Penulis selalu dimodelkan sebagai `Author` eksplisit; tidak ada helper yang menebak nama keluarga dari string. Bila suatu tugas tergoda menebak, hentikan dan minta koreksi lewat formulir (12.4).
- Setiap kalimat wajib punya status (terverifikasi, tidak terverifikasi, bukan klaim faktual). Kalau ada kalimat tanpa status, itu bug, bukan "lolos".
- Sumber panjang diproses per batch lalu digabung dan didedup (12.3); verifikasi tetap memakai teks lengkap.
- Operasi lama (OCR, AI, ambil web, render) berjalan lewat `worker.run_in_thread`; UI hanya disentuh dari callback `after` supaya jendela tidak membeku (bagian 10, 13).
- Order modul murni (1, 2, 3, 4, 5, 6, 7, 8, 8b, 9, 10, 11, 12) cepat ditest. Lapisan GUI (13 sampai 17c) hanya memanggil fungsi inti; logika yang bisa ditest (draf, gerbang ekspor, daftar pustaka terpakai, edit manual, isi fields) diletakkan di `drafts.py` dan `report.py`.
- Jalankan semua perintah dari root repo `C:\Generator`; beberapa tes memakai path relatif (mis. `test_run_bat` membaca `run.bat` dari direktori kerja).
- Semua penanganan error memakai `messagebox` di GUI dan exception bertipe di lapisan inti. Kegagalan satu sumber tidak menghentikan sumber lain.
- Hindari karakter em dash pada teks yang ditulis proyek (antislop).
- Setelah semua task: **review akhir terhadap diff** sebelum menganggap proyek selesai. Gunakan `requesting-code-review` (satu reviewer fresh) bila skill tersedia; bila tidak ada di OpenCode, baca sendiri diff `git diff` dan periksa terhadap kriteria penerimaan bagian 21, lalu `finishing-a-development-branch`.

---

## Addendum Eksekusi

Catatan teknis yang wajib dipegang implementer. Semuanya sudah tercermin di task terkait.

1. **Default mutable pada dataclass.** `Sentence.source_ids` ditulis `field(default_factory=list)`, bukan `= []`; dataclass menolak default list dan gagal saat impor. Impor `field` dari `dataclasses` (8).

2. **Indeks label harus sama dengan `source_ids`.** `order_and_label` mengurutkan sumber secara alfabetis, jadi indeks hasil `enumerate` bukan indeks asli. `LabeledSource` punya `source_index` (indeks asli di `sources`), dan `order_and_label(sources, cite=...)` hanya melabeli sumber yang dikutip supaya sumber tak dikutip tidak memicu sufiks a/b/c. Pakai `report.labels_for(sources, cited_ids)`; jangan pernah `enumerate(order_and_label(...))` (6, 17c).

3. **Siapa yang memasang sitasi.** `render_report` menerima `labels: dict[int, str] | None = None`, dan renderer yang memanggil `content.compose(paragraph, labels or {})`. GUI hanya menyiapkan `labels` dan `references`, bukan memasang sitasi sendiri (8, 12, 17c).

4. **Asal chunk harus ikut ke prompt.** `content_prompt` menerima `chunk_refs` berupa pasangan `(source_id, teks)` dan menulis label `[sumber <id>]` sebelum tiap potongan, supaya AI punya dasar mengisi `source_ids`. `generate_sections` memakai `chunk_text(text, max_chars=max_prompt_chars)` agar ukuran chunk mengikuti batas prompt, bukan angka 3000 tetap (8, 12.3).

5. **Id sumber asing tidak boleh membuat crash.** `verify_sentence` memakai `source_texts.get(sid, "")` (id tak dikenal jadi `tidak terverifikasi`), dan `compose` memakai `labels.get(id)` lalu melewati id yang tidak ada (8, 9).

6. **Beberapa sumber dalam satu kalimat.** `compose` menggabungkan label menjadi satu kurung dipisah `"; "`, diurutkan menurut urutan kunci `labels` (urutan reference), sesuai APA 7. Bukan `"(A, 2020) (B, 2021)"` (8).

7. **Tanda selesai pakai `uid`, bukan nomor posisi.** `Sentence.uid` (uuid) stabil terhadap sisip, hapus, dan urut ulang kalimat. `done` menyimpan `uid`, bukan `SentenceStatus.index`; `can_export`/`pending` memakainya. `done` dan `uid` tiap kalimat ikut disimpan di JSON draf dan dimuat kembali saat draf dibuka (16, 17a, 17b).

8. **Jangan ubah `authors` menjadi `tuple` untuk sekarang.** Tes Task 7 membandingkan `s.authors == [Author(...)]`; perbandingan tuple dengan list bernilai salah. Baru ubah ke `tuple[Author, ...]` bila `Source` benar-benar perlu di-hash, dan sekaligus ubah tesnya.

9. **Tombol massal.** `report.non_factual_uids(statuses)` menyediakan daftar `uid` kalimat bukan klaim faktual, dipakai tombol "Tandai semua bukan klaim faktual selesai" supaya user tidak mengklik satu per satu (17b).

10. **`source_ids` bisa berupa string.** Koersikan ke `int` saat parsing dan buang id yang gagal dikonversi; tanpa itu `labels.get("0")` meleset dan kalimat bersumber dianggap tidak bersumber (8).

11. **`is_factual` ditentukan AI.** Kalimat faktual yang salah ditandai non-faktual tetap bisa lolos bila user menandai selesai tanpa membaca; user tetap penjaga terakhir. Dicatat di README (8, 18).

12. **`origin` dan `citation` per kalimat.** `Sentence.origin` (`"ai"`/`"manual"`) dan `Sentence.citation` (bool) menggantikan `DraftState.manual_edits` yang dihapus. `verify_sentence` mengembalikan `STATUS_UNVERIFIED` untuk `origin != "ai"` sebelum memeriksa cuplikan, dan `compose` tidak memasang sitasi bila `citation` salah. Ikut diserialisasi di draf (8, 9, 16, 17b, 19).

13. **`report.pending` hanya kalimat belum terverifikasi.** Kembalikan `index` kalimat yang statusnya bukan `STATUS_VERIFIED` **dan** `uid`-nya belum ada di `done`; kalimat terverifikasi tidak dihitung tertunda. Ada tes khusus (17a).

14. **Isi fields oleh kode, bukan AI.** `report.build_fields` mengisi `{{JUDUL}}`, `{{NAMA}}`, `{{NIM}}`, `{{MATA_KULIAH}}`, `{{DOSEN}}`, `{{TANGGAL}}`, `{{TAHUN}}`, dan `{{PRODI}}`; `report.format_tanggal` memakai nama bulan Indonesia ("18 Oktober 2026"). Penanda opsional bernilai kosong dihilangkan dari `fields` supaya renderer mengosongkan penandanya (18.5, 17c).

15. **Renderer memblokir penanda mentah.** Penanda opsional tanpa nilai dan `{{LOGO}}` yang gagal dimuat dikosongkan, bukan dibiarkan. Style Heading yang tidak ada dibuat atau di-fallback, tidak `KeyError` (12, 18.1, 18.5).

16. **GUI tidak membeku.** Semua operasi lama (OCR, AI, ambil web, render) lewat `worker.run_in_thread`; UI hanya disentuh dari callback `after`. `worker._drain` murni dan deterministik untuk ditest (13, 17a, 17b, 17c).

17. **Template tanpa kolom status.** Status "lengkap/tidak lengkap" dihitung ulang dengan `validate_template` saat daftar ditampilkan. Template tidak lengkap tetap boleh disimpan, tetapi ditolak saat dipilih di tab Buat Laporan (9.3, 15, 16).

18. **Task 0 dan eksekusi manual.** Header plan tidak lagi memanggil skill `superpowers:*` yang belum tentu ada di OpenCode, melainkan instruksi manual: satu task per giliran, jalankan pytest sebelum commit, berhenti bila tes gagal, jangan menebak API rapidocr, jangan menggabungkan task GUI (Task 0, header).

19. **AIClient menangkap exception umum.** Periksa `response.status_code >= 400` dan bungkus semua `Exception` dari `requests.post`/pembacaan respons menjadi `AIError`, bukan hanya `RequestException`, karena tes lama melempar `Exception("500")` (5).

20. **Selalu pakai interpreter venv.** Aktivasi `activate` tidak bertahan antar panggilan shell agen. Semua perintah tes dan pemasangan memakai `.venv\Scripts\python -m pytest` dan `.venv\Scripts\python -m pip install`; `python` global hanya sekali dipakai untuk `python -m venv .venv` (header, Task 0).

21. **Satu kelas `SourceReadError`.** Didefinisikan sekali di `sources/errors.py`; `pdf_reader` dan `web_reader` mengimpornya, bukan mendefinisikan kelas sendiri, supaya GUI menangkap kedua jenis sumber dengan satu kelas (4, 16). Ada tes identitas kelas.

22. **Edit manual per kalimat.** GUI memberi satu kotak teks per kalimat, bukan satu area per paragraf, supaya tidak ada pemetaan balik ambigu dari teks paragraf ke beberapa kalimat. Menyimpan kotak memanggil `report.apply_manual_edit(sentence, teks)` (17b, 19).

23. **Ekstraksi bibliografi dibatasi.** `bibliography.excerpt` mengirim `max_chars` (6000) karakter pertama plus ekor 500 karakter, bukan seluruh teks, supaya PDF panjang tidak melewati batas konteks; isi laporan tetap memakai chunking 12.3 (7, 12.4).

24. **`cited_ids` mengikuti sitasi yang benar-benar dipasang.** Hanya kalimat `is_factual` dan `citation` benar yang dihitung mengutip, sehingga kalimat yang sitasinya dimatikan user tidak memaksa sumbernya muncul di daftar pustaka (17a, 11.4).

25. **Pembuat koneksi database tunggal.** `app.build_app()` membuat `database.Database(paths.DB_PATH)` dan memanggil `init_schema()` satu kali, lalu meneruskan `db` ke tiap tab; tidak ada tugas lain yang membuatnya (13).

