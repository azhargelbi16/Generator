# Brief Eksekusi: Generator Laporan

Untuk agen pelaksana. Isinya temuan yang sudah diverifikasi di kode, urutan pekerjaan, dan kriteria selesai. Kerjakan berurutan per fase; jangan lanjut sebelum kriteria fase sebelumnya lulus.

## Konteks

Aplikasi desktop Windows (pywebview + React 19 + Tailwind, backend Python 3.12) yang menyusun laporan akademik berbahasa Indonesia dari PDF, DOI, web, atau teks manual, lalu mengekspor DOCX lewat template.

Alur inti:

1. `sources/` membaca sumber (`pdf_reader.py`, `ocr.py`, `doi_resolver.py`, `web_reader.py`).
2. `sources/chunking.py` memotong teks.
3. `ai/content.py` memanggil LLM per batch lalu `_merge_sections`.
4. `format_spec.py` menormalkan struktur bab.
5. `verification.py` memberi status per kalimat.
6. `report.py` dan `preflight.py` menentukan gerbang ekspor.
7. `document/renderer.py` mengisi template DOCX.

Perintah:

```
run.bat                                  # jalankan aplikasi
.venv\Scripts\python -m pytest -q        # tes
cd frontend; npm run build               # bangun UI
```

## Aturan kerja

- Jangan mengubah `.venv/`, `data/config.json`, `output/`, atau `data/drafts/`.
- Jangan pernah mencetak API key atau isi `config.json` ke log, tes, atau commit.
- Setiap task selesai hanya jika tes baru dan tes lama lulus. Sertakan output perintah di laporan.
- Pertahankan bahasa UI dan pesan yang sudah ada (Indonesia).
- Satu task, satu commit. Jangan gabungkan fase dalam satu commit.

## Fase 0: Rapikan repo

### T0.1 Masukkan file yang hilang

`git status` menunjukkan file untracked yang dibutuhkan aplikasi: `src/generator/sources/doi_resolver.py`, `tests/test_doi_resolver.py`, `frontend/src/lib/toast.ts`. Tanpa file ini, clone repo tidak bisa memakai fitur DOI dan toast.

Selesai bila: `git add` ketiga file, commit, dan `git status --porcelain` tidak lagi memuatnya.

### T0.2 Putuskan nasib `frontend/dist`

Saat ini `dist/` di-commit tetapi basi: ada aset lama dan dua file hash baru untracked (`index-CPl3ED0B.js`, `index-CxpbmYdQ.css`), sementara `run.bat` tidak pernah menjalankan `npm run build`.

Pilihan yang dipakai: `dist/` tetap di-commit untuk pengguna tanpa Node, tetapi wajib dibangun ulang setiap kali `frontend/src` berubah.

Selesai bila: `npm run build`, hapus aset hash lama, commit `dist/`, dan `frontend/dist/index.html` merujuk file hash yang benar-benar ada.

### T0.3 Pastikan baseline hijau

```
.venv\Scripts\python -m pytest -q
cd frontend; npm run build; npx tsc --noEmit
```

Catat jumlah tes lulus dan error yang sudah ada sebelum perubahan. Jangan memperbaiki hal di luar brief ini.

## Fase 1: Verifikasi klaim, bukan sekadar kutipan

### Masalah

`verification.py:78-88` hanya mengecek `sentence.quote` sebagai substring teks sumber. Akibatnya:

- Kalimat halusinasi yang menempelkan kutipan asli tetap berstatus "terverifikasi".
- Kutipan kurang dari 8 kata langsung gagal (`verification.py:21,79`).
- Selisih satu tanda baca, angka, atau noise OCR menggagalkan pencocokan.
- Kalimat hasil suntingan manual selalu merah (`verification.py:76`).

Dampak nyata: `data/app.log` mencatat ekspor dipaksa dua kali dengan 13 dan 48 kalimat belum selesai. Gerbang verifikasi sedang dilewati rutin oleh pengguna.

### T1.1 Skor dukungan klaim

Tambahkan pemeriksaan lokal di `verification.py` yang membandingkan **kalimat** dengan jendela teks di sekitar kutipan, bukan hanya kutipan.

Aturan:

- Kandidat jendela: 400 karakter sebelum dan sesudah posisi kutipan di sumber.
- Skor: rasio kata kalimat yang muncul di jendela, setelah normalisasi yang sudah ada. Abaikan kata fungsi Indonesia (`yang`, `dan`, `di`, `ke`, `dari`, `untuk`, `dengan`, `pada`, `adalah`, `ini`, `itu`, `tidak`).
- Status baru: `terverifikasi` bila kutipan ditemukan dan skor >= 0,6; `perlu_ditinjau` bila kutipan ditemukan tetapi skor < 0,6; `tidak_terverifikasi` bila kutipan tidak ditemukan.
- `perlu_ditinjau` tetap memblokir ekspor, tetapi tampil beda dan punya alasan yang bisa dibaca pengguna.
- Jangan mengubah status `bukan_klaim_faktual` dan `origin != "ai"`.

Selesai bila ada tes di `tests/test_verification.py` yang membuktikan: kutipan asli + kalimat yang tidak didukung sumber menghasilkan `perlu_ditinjau`, bukan `terverifikasi`.

### T1.2 Toleransi teks

Rendahkan `MIN_WORDS` menjadi 5, dan bandingkan juga setelah membuang semua karakter selain huruf dan angka agar typo tanda baca serta pemisah ribuan tidak menggagalkan verifikasi.

Selesai bila tes membuktikan kutipan 6 kata dengan perbedaan tanda baca tetap lolos.

### T1.3 Tampilkan alasan di UI

`frontend/src/components/TabReview.tsx` sudah menampilkan status per kalimat. Tambahkan teks alasan singkat untuk `perlu_ditinjau` (contoh: "Kutipan ada, kalimatnya tidak sepenuhnya didukung sumber"). Jangan mengubah tata letak lain.

Selesai bila status baru muncul dengan warna dan label yang berbeda, dan `npx tsc --noEmit` lulus.

### T1.4 Turunkan beban penandaan

Tambahkan aksi "tandai semua yang bukan klaim" yang memakai `is_factual == false` dari AI, bukan menandai semua kalimat merah. Aksi massal untuk kalimat `perlu_ditinjau` tidak boleh ada.

Selesai bila tes `tests/test_report_edit.py` atau tes baru membuktikan kalimat `perlu_ditinjau` tidak ikut tertandai.

## Fase 2: Keandalan generate

### T2.1 Chunking sadar kalimat dengan overlap

`chunking.py:14-30` memotong di spasi terakhir tanpa overlap dan tanpa batas kalimat. Bukti yang melewati batas chunk jadi mustahil dikutip.

Aturan: potong di batas kalimat sedekat mungkin dengan `max_chars`; jatuh ke batas kata bila perlu; overlap 200 karakter antar chunk; jangan pernah memotong di tengah kata; `Chunk.id` tetap berurutan.

Selesai bila tes baru di `tests/test_chunking.py` membuktikan tidak ada kata terpotong, kalimat utuh tidak terbelah, dua chunk berurutan berbagi overlap, dan teks pendek tetap satu chunk.

### T2.2 Kirim hanya bab relevan per batch

`ai/content.py:376` mengirim seluruh outline untuk setiap batch, dan `prompts.py:64` mewajibkan semua bab ditulis. Pada PDF panjang setiap batch menulis ulang seluruh laporan sehingga biaya token naik dan isi bab bercampur.

Aturan: petakan chunk ke bab lewat kecocokan kata kunci judul dan isi; kirim 1 sampai 3 bab target per batch; pertahankan urutan lewat `_order_by_outline`; bila ragu, kirim seluruh outline seperti sekarang.

Selesai bila tes di `tests/test_content.py` membuktikan batch dengan sumber berbeda hanya meminta bab relevan dan urutan akhir tetap sesuai outline.

### T2.3 Retry, batas token, output terpotong

`ai/client.py:13` memakai satu `TIMEOUT = 120` untuk semua permintaan dan tidak ada retry. `content.py:393` tidak mencoba ulang, sehingga satu HTTP 429 menggagalkan batch.

Aturan: retry maksimal 3 kali dengan backoff 2, 4, 8 detik untuk 429, 500, 502, 503, 504, dan timeout; hormati `Retry-After`; kirim `max_tokens` eksplisit (default 4096); perlakukan `finish_reason == "length"` sebagai batch gagal; timeout baca streaming 300 detik.

Selesai bila tes di `tests/test_ai_client.py` membuktikan 429 lalu sukses berakhir sukses, 429 tiga kali berakhir `AIError`, dan output terpotong memicu kegagalan batch.

### T2.4 Pembatalan benar-benar berhenti

Pembatalan hanya dicek di antara chunk (`client.py:112`, `content.py:275`), sehingga klik Batal saat menunggu respons tidak berpengaruh sampai timeout.

Aturan: pakai stream dengan timeout baca pendek (5 detik) dan periksa `cancel` tiap potongan. Jangan ubah tanda tangan publik `generate_sections` dan `chat_stream`.

Selesai bila tes membuktikan pembatalan menghentikan pembacaan stream dalam kurang dari 10 detik.

### T2.5 Merge tanpa duplikat semantik

`content.py:197-204` hanya membuang kalimat identik. Parafrase duplikat lolos dan menumpuk sebagai paragraf tambahan.

Aturan: buang kalimat baru bila kemiripan token dengan kalimat yang ada >= 0,85, tetapi jangan buang kalimat dengan sitasi berbeda.

Selesai bila tes di `tests/test_content.py` membuktikan dua parafrase ringan hanya menyisakan satu kalimat.

## Fase 3: Data dan privasi

### T3.1 Jangan kirim API key ke frontend

`api_bridge.py` mengembalikan konfigurasi lengkap, termasuk `ai_api_key`, ke UI. UI hanya perlu tahu apakah key sudah diisi.

Aturan: respons baca konfigurasi mengembalikan `ai_api_key` kosong dan field boolean `ai_api_key_set`. Simpan tetap menerima key baru; key kosong saat menyimpan berarti "jangan ubah".

Selesai bila tes di `tests/test_web_api_bridge.py` membuktikan key tidak pernah muncul di respons baca, dan menyimpan key kosong tidak menghapus key lama.

### T3.2 Enkripsi draf di disk

`drafts.py` menyimpan teks sumber utuh sebagai JSON polos. Gunakan DPAPI Windows (`CryptProtectData` lewat `ctypes`, tanpa dependensi baru) untuk mengenkripsi isi draf. Sediakan fallback polos hanya bila DPAPI tidak tersedia, dan catat di log tanpa isi data.

Selesai bila tes membuktikan draf baru tidak memuat teks sumber yang bisa dibaca langsung, dan draf lama masih bisa dibuka.

### T3.3 Backup sebelum migrasi

`database.py` punya `SCHEMA_VERSION = 1` tetapi belum ada runner migrasi. Tambahkan:

- `backup_database()` yang menyalin `app.db` ke `data/backup/app-YYYYMMDD-HHMMSS.db` sebelum migrasi.
- Runner yang membandingkan versi dan menjalankan migrasi berurutan.
- Retensi maksimal 10 berkas backup.

Selesai bila tes membuktikan database versi lama dimigrasi, backup terbentuk, dan data profil/dosen/template tetap utuh.

### T3.4 Batasi akses berkas sensitif

Setelah `config.json` ditulis, set izin Windows agar hanya pengguna saat ini yang bisa membaca (ACL lewat `icacls` atau `win32security` bila sudah tersedia). Jangan memindahkan lokasi berkas pada fase ini.

Selesai bila tes memeriksa fungsi izin dipanggil setelah simpan, tanpa bergantung pada mesin CI Linux.

## Fase 4: Ekspor dan otomasi

### T4.1 Jangan diam-diam memakai template pertama

`api_bridge.py:983-984`: bila `template_id` kosong, aplikasi memakai `tpls[0]`. Pengguna bisa mengekspor dengan template yang salah tanpa sadar.

Aturan: kembalikan error "Pilih template terlebih dahulu" bila tidak ada template terpilih. Jangan mengubah pemanggil lain.

Selesai bila tes di `tests/test_web_api_bridge.py` membuktikan ekspor tanpa `template_id` gagal dengan pesan tersebut.

### T4.2 Validasi gaya sitasi di preflight

`preflight.py:128` selalu melaporkan `Check("Gaya sitasi", True, ...)`. Ganti dengan pemeriksaan nilai yang didukung (`et_al`, `dkk`), dan laporkan gagal bila di luar itu.

Selesai bila tes di `tests/test_preflight.py` membuktikan nilai tidak dikenal menghasilkan baris gagal.

### T4.3 Tes jalur ekspor sukses

`tests/test_web_api_bridge.py` belum pernah menguji `export_report` yang berhasil, dan `os.startfile` di `api_bridge.py` belum pernah di-mock.

Selesai bila ada tes yang mengekspor DOCX sungguhan ke folder sementara, memastikan berkas ada dan bisa dibuka `python-docx`, dan `os.startfile` di-mock.

### T4.4 CI

Tambahkan `.github/workflows/ci.yml`:

- Job Python: `pip install -r requirements.txt`, lalu `pytest -q`.
- Job frontend: `npm ci`, `npm run build`, `npx tsc --noEmit`.
- Tandai `tests/test_ocr.py` sebagai `slow` dan jalankan terpisah, karena mengunduh model OCR.

Selesai bila workflow lulus di commit bersih dan `pytest -m "not slow"` selesai di bawah 2 menit.

### T4.5 (Opsional) Paket instalasi

Hanya kerjakan bila diminta. Butuh PyInstaller + Inno Setup, `paths.py` sadar `sys._MEIPASS`, dan `frontend/dist` ikut dibundel. Jangan mulai tanpa persetujuan karena mengubah cara aplikasi diluncurkan.

## Definition of done keseluruhan

1. `pytest -q` lulus, termasuk tes baru untuk setiap task.
2. `cd frontend; npm run build; npx tsc --noEmit` lulus.
3. Tidak ada API key di respons UI, log, atau commit.
4. `git status` bersih setelah setiap fase.
5. Laporan akhir memuat: commit per task, output perintah, dan bukti ekspor DOCX.

## Larangan

- Jangan menambah dependensi baru kecuali disebut di brief ini.
- Jangan mengubah skema database tanpa runner migrasi dari T3.3.
- Jangan menurunkan standar verifikasi dengan menghapus gerbang ekspor.
- Jangan memperbaiki hal di luar daftar task. Catat temuan lain di bagian "Temuan tambahan" pada laporan.

