# Checkpoint: Generator Laporan Akademik

Tanggal: 2026-10-18
Gunakan file ini untuk memulai sesi baru.

## 1. Status terakhir

**Lokasi kerja:** `C:\Generator` (git sudah di-init, belum ada commit).
Python 3.12.10, git 2.55.0. Semua eksekusi ada di folder ini.

**Belum ada satu baris kode implementasi.** Repo masih kosong selain `docs/`.

**Dokumen:**
- Desain: `docs/superpowers/specs/2026-10-18-generator-laporan-design.md`
  (Revisi 5 + Putaran 6, status: MENUNGGU PERSETUJUAN USER).
- Plan: `docs/superpowers/plans/2026-10-18-generator-laporan.md`
  (Revisi 5 + Putaran 6, Task 0 sampai 18 ditambah 8b dan 17a/b/c, sudah
  disesuaikan penuh, termasuk instruksi eksekusi OpenCode di header dan
  "Addendum Eksekusi" di akhir).

**Tujuan:** aplikasi desktop ramah pemula (tanpa terminal) untuk menyusun
laporan akademik dari sumber PDF dan link web. AI menulis isi, kode membuat
sitasi APA 7th dan memverifikasi cuplikan, output DOCX proper (cover + logo
5x5 cm, daftar isi, bab, daftar pustaka).

**Teknologi (bagian 6 desain):** Python 3.12, Tkinter, SQLite, python-docx,
pypdf, pypdfium2 (BUKAN PyMuPDF karena AGPL), rapidocr + onnxruntime (bukan
Tesseract), requests + beautifulsoup4, pytest, Pillow (fixture tes).

**Keputusan yang sudah final:**
1. Instalasi: `run.bat` bootstrap (`.exe` = opsi masa depan).
2. Struktur bab laporan: outline dari user.
3. OCR PDF scan: ada di versi 1.
4. Konfigurasi AI lewat tab Pengaturan; `config.example.json` dihapus.
5. Penulis dimodelkan eksplisit: `Author(family, given, is_org, abbrev)`.
   Kode tidak menebak pemisahan nama (syarat B).
6. Keluaran AI per kalimat:
   `Sentence(text, quote, source_ids, is_factual, uid, origin="ai", citation=True)`.
   Kode tidak memisah kalimat sendiri. `origin` menandai hasil AI atau edit
   manual; kalimat manual selalu `tidak terverifikasi` sampai ditandai selesai.
7. Status per kalimat ada tiga: `terverifikasi`, `tidak terverifikasi`,
   `bukan klaim faktual`. Tidak ada kalimat yang lolos tanpa status.
8. Gerbang ekspor memblokir sampai kalimat belum selesai ditandai selesai
   lewat tombol Tandai selesai.
9. Chunking: batch di bawah batas karakter, satu panggilan AI per batch,
   hasil digabung dan didedup.

**Database menyimpan:** `profil_mahasiswa` (nama, NIM, prodi), `dosen`,
`mata_kuliah`, `logo`, `template`, `schema_version`. Sumber jurnal TIDAK
disimpan. Draf disimpan sementara di `data/drafts/`.

**Penanda template.**
Wajib: JUDUL, NAMA, NIM, MATA_KULIAH, DOSEN, LOGO, TANGGAL, ISI_LAPORAN,
DAFTAR_PUSTAKA, DAFTAR_ISI.
Opsional: TAHUN, PRODI.
Khusus (wajib berdiri sendiri): ISI_LAPORAN, DAFTAR_PUSTAKA, DAFTAR_ISI, LOGO.
Tak dikenal: dibiarkan, diperingatkan sebelum ekspor.

## 2. Apa yang terjadi di sesi ini

1. Plan lama (13 task, pra-Revisi 2) diganti plan baru 18 task yang menyerap
   Revisi 2, 3, 4.
2. User memberi review P0/P1/P2 atas plan baru. Semua temuan dinilai sah dan
   sudah diperbaiki:
   - P0-1: empat tes yang bertentangan dengan `MIN_WORDS = 8` diperbaiki
     (cuplikan minimal 8 kata).
   - P0-2: model penulis diganti ke `Author` eksplisit; `surname()` dihapus.
   - P0-3: `test_connection` diganti `check_connection`.
   - P0-4: ditambah `pyproject.toml` (`pythonpath = ["src", "."]`) dan
     `tests/__init__.py`.
   - P1-5: status ketiga eksplisit + aturan kalimat tanpa entri.
   - P1-6: JSON per kalimat, `compose` tidak memisah kalimat.
   - P1-7: tombol Tandai selesai + `report.can_export(statuses, done)`.
   - P1-8: strategi batch chunk (gabung + dedup).
   - P1-9: kontrak `fields` renderer (kunci penanda khusus diabaikan).
   - P2: monkeypatch di test paths, cek `first_line_indent` negatif,
     `if __name__ == "__main__": main()`, catatan verifikasi API rapidocr.
3. Desain diperbarui ke Revisi 5 (bagian 11.1, 11.2, 11.5, 12.3, 12.4, 17,
   19, dan catatan "Putaran 4 (Revisi 5)" di bagian 23).
4. Catatan addendum menyusul, juga dinilai sah dan sudah diperbaiki:
   - `Sentence.source_ids` memakai `field(default_factory=list)` (default list
     mutable bikin dataclass gagal saat impor).
   - `render_report` menerima `labels`; renderer yang memanggil
     `content.compose` (sebelumnya tidak jelas siapa memasang sitasi).
   - `content_prompt` menerima `chunk_refs=[(source_id, teks)]` dan menulis
     label `[sumber <id>]`; ukuran chunk mengikuti `max_prompt_chars`.
   - Id sumber asing tidak crash: `source_texts.get(...)` dan `labels.get(...)`.
   Semuanya dirangkum di bagian "Addendum Eksekusi" plan.
5. Bug indeks label dan catatan kecil, juga sudah diperbaiki:
   - `LabeledSource.source_index` + `order_and_label(sources, cite=...)`: label
     tidak lagi memakai posisi hasil `enumerate` (yang tertukar), dan sufiks
     a/b/c hanya dihitung dari sumber yang dikutip.
   - `report.labels_for` menggantikan pola `enumerate(order_and_label(...))`
     di GUI dan e2e.
   - `compose` menggabungkan beberapa sumber satu kalimat dalam satu kurung
     dipisah titik koma (APA 7), bukan dua kurung berurutan.
   - `DraftState.done` menyimpan tanda selesai agar bertahan antar sesi.
   - `authors` tetap `list` (bukan tuple). Singkatan organisasi dicatat sebagai
     batasan di README.
   Desain mencatat ini di bagian "Putaran 5 (Revisi 5, lanjutan)".
6. Putaran lanjutan (sudah diperbaiki juga):
   - Tanda selesai kini memakai `Sentence.uid` yang stabil, bukan nomor posisi.
     `done` disimpan sebagai daftar `uid` di draf (termasuk `uid` tiap kalimat
     di `sections`), dan `can_export`/`pending` memakai `uid`. Ini mencegah
     tanda selesai berpindah kalimat setelah sisip/hapus/regenerate.
   - Tombol massal "Tandai semua bukan klaim faktual selesai" lewat
     `report.non_factual_uids`.
   - `source_ids` dikoersi ke `int` saat parsing (AI kadang mengirim "0").
   - Catatan README: `is_factual` ditentukan AI (user penjaga terakhir), dan
     kualitas isi bisa turun pada PDF sangat panjang (trade-off batch 12.3).
   - Ketidakcocokan desain diperbaiki: bagian 10 langkah 9 dan kriteria 10 di
     bagian 21 kini menyebut tiga status; bagian 13 mencantumkan `drafts.py`
     dan `report.py`; 11.4 memuat aturan titik koma; 17.1 memuat batasan
     singkatan organisasi; 17.4 menambah kasus uji `source_index` dan
     sitasi ganda.

Tidak ada temuan yang ditolak. Tidak ada temuan yang belum ditangani.

7. Putaran 6 (review sebelum GUI) sudah diperbaiki:
   - Fitur spec tanpa task dipertahankan dengan task sendiri: Task 8b
     (parafrase AI, usul outline, gabung regenerate + "tulis ulang semua").
   - Model edit manual dijelaskan: `Sentence.origin` (`"ai"`/`"manual"`) dan
     `Sentence.citation`; `DraftState.manual_edits` dihapus. Kalimat manual
     selalu `tidak terverifikasi` sampai ditandai selesai; tombol Pulihkan
     sitasi menyalakan `citation`.
   - `report.pending` hanya kalimat bukan `STATUS_VERIFIED` yang belum di
     `done`; ada tes khusus.
   - Pengisian fields ditugaskan ke kode: `report.build_fields` +
     `report.format_tanggal` (bahasa Indonesia). Penanda opsional tanpa
     nilai dan `{{LOGO}}` gagal dimuat dikosongkan (bagian 18.5).
   - Style Heading yang tidak ada di template dibuat/di-fallback, bukan
     `KeyError`; ada tes (bagian 18.1).
   - GUI tidak membeku: modul `gui/worker.py` (`run_in_thread`, `_drain`),
     operasi lama di thread, UI lewat `after` (bagian 10, 13).
   - Task GUI besar dipecah: 17a (generate + status), 17b (edit, tandai
     selesai, pulihkan sitasi, parafrase), 17c (gerbang ekspor, fields,
     simpan DOCX).
   - Temuan kecil: `AIClient` menangkap exception umum + cek `status_code`;
     status template dihitung saat ditampilkan dan penolakan saat dipilih di
     tab Laporan; model rapidocr butuh internet saat pertama jalan; header
     plan diganti instruksi eksekusi manual OpenCode; ditambah Task 0 (git
     init, venv, pip, letak dokumen).

8. Putaran 6b (perbaikan lanjutan sebelum GUI) sudah diperbaiki:
   - Perintah selalu pakai `.venv\Scripts\python -m pytest` dan
     `.venv\Scripts\python -m pip` (aktivasi `activate` tidak bertahan antar
     panggilan shell).
   - Satu kelas `SourceReadError` di `sources/errors.py`, diimpor
     `pdf_reader` dan `web_reader` (ada tes identitas kelas).
   - Edit manual per kalimat, satu kotak teks per kalimat (bukan per
     paragraf).
   - Ekstraksi bibliografi dibatasi: `excerpt` = 6000 karakter awal + 500
     ekor, bukan seluruh teks.
   - Pillow ditandai dependensi runtime (renderer logo), bukan hanya tes.
   - `build_app` membuat `Database(paths.DB_PATH)` dan memanggil
     `init_schema()` sekali.
   - `generate_sections` melempar `ValueError` bila jumlah sumber dan teks
     tidak sama.
   - `cited_ids` hanya menghitung kalimat `is_factual` dan `citation` benar,
     sehingga sumber yang sitasinya dimatikan tidak muncul di daftar
     pustaka.
   - Wajib uji manual `run.bat` setelah Task 13; catatan bahwa kegagalan OCR
     pada fixture berfont Pillow belum cukup untuk menyimpulkan rapidocr
     tidak cocok.

## 3. Langkah berikutnya

1. **Minta persetujuan user** atas desain Revisi 5 + Putaran 6 dan plan.
   Jangan menulis kode sebelum disetujui.
2. **Eksekusi plan** task-by-task dengan skill `executing-plans` (bila tidak
   ada, manual sesuai header plan): TDD, satu task per giliran, jalankan
   `.venv\Scripts\python -m pytest` dari root `C:\Generator` sebelum commit,
   berhenti bila tes gagal, jangan menggabungkan task GUI. Mulai dari
   **Task 0** (git init, venv, pip, letak dokumen), lalu **Task 1**.
3. **Gerbang OCR:** hentikan di Task 1 bila OCR gagal. Itu memang gerbangnya.
   Coba satu PDF scan Indonesia asli sebelum memutuskan, jangan hanya
   mengandalkan fixture berfont Pillow.
4. **Gerbang GUI:** setelah Task 13 selesai, jalankan `run.bat` dan
   klik-klik sebentar sebelum lanjut ke Task 14 (tes GUI hanya memeriksa
   "atribut ada").
5. **Setelah semua task:** review akhir terhadap diff (`git diff`) dengan
   `requesting-code-review` (satu reviewer fresh) bila tersedia, periksa
   terhadap kriteria penerimaan bagian 21, lalu `finishing-a-development-branch`.

**Catatan eksekusi penting:**
- Hitungan kata pada tes verifikasi masih manual (belum ada kode). Konfirmasi
  saat menjalankan tes Task 9, 17a, 18.
- API rapidocr 3.x (bentuk keluaran `RapidOCR()(image)`) belum diverifikasi.
  Implementer wajib mencatat bentuk keluaran asli di Task 1. Model diunduh
  saat pertama jalan, jadi butuh internet.
- `run.bat` hanya mengatur PYTHONPATH untuk aplikasi; tes memakai
  `pythonpath` dari `pyproject.toml`.
- Jalankan semua perintah dari root repo; beberapa tes memakai path relatif.
- Tiga dokumen sudah ada di `docs/superpowers/`; `CHECKPOINT` opsional di
  Task 0 (jangan berhenti hanya karena catatan sesi tidak ada).
- Jangan menebak API pustaka dan jangan menandai selesai tanpa menjalankan
  tes.

## 4. Skill yang relevan untuk sesi baru

`using-superpowers` (wajib, muat lebih dulu), `executing-plans`,
`writing-plans`, `receiving-code-review`, `test-driven-development`,
`requesting-code-review`, `finishing-a-development-branch`, dan `antislop`
(hindari karakter em dash pada teks yang ditulis). Bila skill `superpowers:*`
tidak terpasang di OpenCode, jalankan plan secara manual sesuai instruksi di
header plan.

## 5. Peta task (untuk referensi cepat)

0. Persiapan repo: git init, venv, pip, letak dokumen
1. Pipeline OCR + kunci requirements.txt (spike pertama, butuh internet)
2. Config, paths fallback, logging
3. Database (profil mahasiswa, dosen, matkul, logo, template, schema_version)
4. Pembaca sumber (PDF, web) + deteksi scan + chunking
5. Klien AI + `check_connection` (menangkap exception umum)
6. Sitasi APA 7th lengkap (`Author` eksplisit)
7. Ekstraksi bibliografi + gabung metadata + retry
8. Tulis isi laporan per kalimat + penempatan sitasi + batch chunk
8b. Parafrase AI, usul outline AI, gabung hasil regenerate
9. Verifikasi deterministik + tiga status (+ aturan origin manual)
10. Pencarian/penggantian penanda lintas run
11. Validasi template DOCX
12. Renderer DOCX (logo 5x5, TOC, hanging indent, heading dengan fallback)
13. GUI shell + tab Data + worker latar + run.bat bootstrap
14. GUI tab Pengaturan (AI)
15. GUI tab Kelola Template (status dihitung saat tampil)
16. Draf sementara + tab Buat Laporan bagian 1 (sumber, OCR fallback, koreksi metadata, usul outline)
17a. report.py inti + tombol Generate + tampilan status
17b. Edit manual, tandai selesai, pulihkan sitasi, parafrase
17c. Gerbang ekspor, isi fields, simpan DOCX
18. README + wiring akhir + uji end-to-end
