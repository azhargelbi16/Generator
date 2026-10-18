# Generator Laporan Akademik - Dokumen Desain

Tanggal: 2026-10-18
Status: Revisi 5, menunggu persetujuan
Catatan: Revisi ini menjawab review putaran 1 (P0-1 s.d. P2), putaran 2,
putaran 3 (syarat A, B, C), dan putaran 4 (model penulis eksplisit, JSON
per kalimat, status ketiga, chunking). Lihat bagian 23.

## 1. Tujuan

Membuat aplikasi desktop ramah pemula untuk menyusun laporan tugas
perkuliahan, tanpa perlu membuka terminal atau mengetik perintah berderet.

Aplikasi harus bisa:

1. Menerima sumber berupa file PDF jurnal dan link website.
2. Memakai AI untuk mengubah sumber menjadi sitasi dalam teks dan daftar
   pustaka dengan gaya APA 7th, memakai "et al." untuk penulis banyak.
3. Memakai AI untuk menulis isi laporan yang tidak delusional, yaitu
   berbasis sumber yang diberikan, dan menampilkan bukti sumbernya.
4. Membiarkan user memparafrase atau mengedit hasil AI.
5. Menghasilkan dokumen DOCX yang tetap proper: cover (dengan logo kampus
   ukuran 5x5 cm), daftar isi, bab, dan daftar pustaka.
6. Menyimpan data yang sering dipakai ulang (dosen, mata kuliah, logo,
   template) supaya tidak diketik ulang terus.
7. Memakai template DOCX yang bisa ditambah user, dengan format penanda
   yang didokumentasikan di README.md agar aplikasi tidak crash.

## 2. Batasan (Constraints)

- Bahasa pemrograman: Python 3.12.
- Target platform: Windows (dijalankan dari `C:\Generator`).
- Output dokumen: hanya DOCX.
- Gaya sitasi: hanya APA 7th (versi 1).
- Semua eksekusi dan penyimpanan hasil ada di dalam `C:\Generator`.
- Harus ramah pemula: interaksi utama lewat klik, bukan terminal.

## 3. Non-Goals

- Tidak menyimpan sumber jurnal ke database (sumber dipakai sekali lalu
  selesai, menyimpan malah memberatkan sistem).
- Tidak mendukung format output selain DOCX.
- Tidak mendukung gaya sitasi selain APA 7th.
- Tidak mendukung kolaborasi multi-user atau layanan daring.

## 4. Anti-Goals (yang membuat proyek dianggap gagal)

- Aplikasi crash karena template atau penanda template salah.
- AI menghasilkan isi palsu yang tidak berdasar sumber (delusi).
- User tetap harus mengetik perintah terminal untuk memakai aplikasi.
- Data dosen, mata kuliah, atau logo harus diketik ulang di tiap laporan.

## 5. Pengguna dan Konteks

Mahasiswa yang mengerjakan tugas laporan mata kuliah. Tingkat keahlian
teknis: pemula. Keinginan utama: mempermudah pekerjaan, bukan belajar
perintah terminal.

## 6. Keputusan Teknologi

| Aspek | Pilihan | Alasan |
|-------|---------|--------|
| Bahasa | Python 3.12 | Banyak pustaka stabil untuk PDF, web, DOCX, dan AI |
| Antarmuka | Tkinter (bawaan Python) | Tanpa server dan tanpa instalasi tambahan, paling tidak mudah crash |
| Database | SQLite (bawaan) | Sederhana, satu file, tanpa server |
| Dokumen | python-docx | Pustaka DOCX yang matang dan stabil |
| Baca PDF | pypdf | Ringan, murni Python |
| Render PDF ke gambar (OCR) | pypdfium2 | Merender halaman tanpa biner eksternal; lisensi BSD-3-Clause / Apache-2.0 (bukan AGPL) |
| OCR | rapidocr + onnxruntime | Pasang lewat pip tanpa biner eksternal; OCR aksara Latin; lisensi Apache-2.0 dan MIT |
| Baca web | requests + beautifulsoup4 | Standar, parser bawaan html.parser |
| AI | Endpoint OpenAI-compatible via requests | Bisa diarahkan ke layanan mana pun (termasuk gateway lokal user) |
| Gambar | Pillow | Dependensi runtime: renderer memakainya untuk menghitung rasio logo; sekaligus dipakai fixture tes |
| Testing | pytest | Standar dan mudah dijalankan |

Catatan: baris Render PDF dan OCR adalah tambahan pada Revisi 2/3 karena
user meminta OCR ada di versi 1 (diverifikasi pada bagian 23). Pilihan
teknologi lain tidak berubah. Konfigurasi AI tidak lagi hanya lewat file;
lihat bagian 15 (halaman Pengaturan di GUI).

## 7. Data yang Disimpan (database lokal)

Disimpan di SQLite karena sering dipakai ulang:

- `dosen`: nama, gelar, identitas opsional.
- `mata_kuliah`: nama, kode opsional.
- `logo`: nama, path file gambar.
- `template`: nama, deskripsi, path file DOCX.
- `profil_mahasiswa`: nama, NIM, program studi. Menyediakan nilai untuk
  `{{NAMA}}`, `{{NIM}}`, dan `{{PRODI}}` agar tidak diketik ulang tiap
  laporan (menjawab putaran 2, temuan 5).

## 8. Data yang TIDAK Disimpan

- Sumber jurnal tidak dimasukkan ke database yang bisa dicari.
- Draf laporan disimpan **sementara** di `data/drafts/` selama pengerjaan,
  supaya pekerjaan tidak hilang bila aplikasi tertutup dan verifikasi bisa
  diulang. Teks sumber hanya ikut di dalam file draf, bukan di database
  sumber. Draf dihapus saat laporan diekspor atau user membuangnya.

## 9. Format Template

Template adalah file `.docx` dengan penanda tetap. Penanda wajib:

| Penanda | Diisi dengan |
|---------|--------------|
| `{{JUDUL}}` | Judul laporan |
| `{{NAMA}}` | Nama mahasiswa (profil_mahasiswa) |
| `{{NIM}}` | NIM mahasiswa (profil_mahasiswa) |
| `{{MATA_KULIAH}}` | Mata kuliah dari database |
| `{{DOSEN}}` | Nama dosen dari database |
| `{{LOGO}}` | Logo kampus 5x5 cm dari database |
| `{{TANGGAL}}` | Tanggal otomatis |
| `{{ISI_LAPORAN}}` | Isi bab hasil AI |
| `{{DAFTAR_PUSTAKA}}` | Daftar pustaka APA 7th |
| `{{DAFTAR_ISI}}` | Daftar isi otomatis (field TOC Word) |

Penanda opsional:

| Penanda | Sumber nilai | Perilaku bila tidak ada |
|---------|--------------|--------------------------|
| `{{TAHUN}}` | Tahun berjalan (otomatis) | Dibiarkan kosong |
| `{{PRODI}}` | `profil_mahasiswa.prodi` | Dibiarkan kosong |

Catatan (menjawab kontradiksi putaran 2): `{{DAFTAR_ISI}}` kini **wajib**
supaya tujuan nomor 5 (daftar isi) selalu terpenuhi. `{{PRODI}}` kini punya
sumber nilai (profil mahasiswa), tidak lagi mengambang.

### 9.1 Strategi Pencarian dan Penggantian Penanda (menjawab P0-4)

DOCX menyimpan teks dalam potongan bernama `run`. Penanda seperti
`{{JUDUL}}` sering terpecah menjadi beberapa run karena format, pemeriksa
ejaan, atau penyuntingan. Pencarian teks biasa akan gagal menemukannya.

Keputusan:

- Modul bersama `document/placeholders.py` menyediakan satu fungsi
  pencarian dan penggantian. Renderer dan validator wajib memakai fungsi
  yang sama ini, supaya hasil validasi dan pengisian selalu cocok.
- Untuk setiap paragraf, gabungkan teks seluruh run, cari penanda pada
  teks gabungan (termasuk penanda yang terpotong antar run), lalu lakukan
  penggantian. Teks **sebelum** penanda tetap di run pertama, teks
  **sesudah** penanda tetap di run terakhir; yang dikosongkan hanya run
  yang sepenuhnya berada di dalam penanda. Format run pertama
  dipertahankan. Ini mencegah teks setelah penanda ikut terhapus
  (menjawab putaran 2, temuan 3).
- Harus menangani beberapa penanda berbeda dalam satu paragraf.
- Pola yang sama dipakai untuk header, footer, dan sel tabel.

### 9.2 Lokasi Penanda yang Didukung

- Didukung: paragraf body, sel tabel, header, footer.
- Tidak didukung pada versi 1: text box dan shape. Ini ditulis eksplisit
  di README.
- Penanda tak dikenal (misalnya `{{FOO}}`): dibiarkan apa adanya, tetapi
  dicatat dan ditampilkan sebagai peringatan **sebelum ekspor**, supaya
  penanda mentah tidak ikut tercetak tanpa disadari.

### 9.3 Validasi Template

- `validate_template` mengembalikan daftar penanda wajib yang hilang dan
  penanda khusus yang tidak berdiri sendiri.
- Bila ada penanda wajib hilang **atau** penanda khusus tidak berdiri
  sendiri, aplikasi menampilkan dialog ramah yang menyebut penanda mana,
  dan menolak memproses, bukan crash (perilaku tunggal, menjawab putaran
  3, syarat C).
- Waktu penolakan: template tidak lengkap **tetap boleh disimpan** di tab
  Kelola Template (dengan peringatan dan status "tidak lengkap" yang
  dihitung ulang saat daftar ditampilkan, bukan kolom database). Yang
  ditolak adalah **memakainya untuk membuat laporan**: saat user memilih
  template itu di tab Buat Laporan, aplikasi menampilkan dialog ramah dan
  tidak melanjutkan sampai user memilih template lain (menjawab putaran 6,
  temuan kecil).
- Validasi memakai fungsi pencarian pada bagian 9.1.

### 9.4 Penanda Khusus (banyak paragraf dan gambar)

- `{{ISI_LAPORAN}}`, `{{DAFTAR_PUSTAKA}}`, `{{DAFTAR_ISI}}`, dan `{{LOGO}}`
  bukan penggantian teks biasa (banyak paragraf, field, atau gambar).
- Aturan: penanda khusus ini wajib **berdiri sendiri di satu paragraf**.
  Bila bercampur teks lain, validator **menolak** dengan dialog ramah yang
  menyebut penanda mana, sama seperti kasus penanda wajib yang hilang
  (menjawab putaran 2 temuan 3 dan putaran 3 syarat C).
- `{{LOGO}}` diganti gambar 5x5 cm; `{{DAFTAR_ISI}}` diganti field TOC;
  `{{ISI_LAPORAN}}` diganti blok paragraf; `{{DAFTAR_PUSTAKA}}` diganti
  daftar entri dengan hanging indent.

## 10. Alur Utama

1. Buka aplikasi GUI.
2. Bila konfigurasi AI belum diisi, aplikasi tetap terbuka dan menampilkan
   petunjuk menuju tab Pengaturan (bagian 15).
3. Pilih menu: Buat Laporan Baru, Kelola Data, Kelola Template, atau
   Pengaturan.
4. Buat Laporan Baru: pilih template sekali di awal, pilih profil
   mahasiswa, dosen, dan mata kuliah dari database, pilih logo dari
   database, isi judul laporan, isi outline bab.
5. Masukkan sumber (PDF atau link web). Kegagalan satu sumber tidak
   menghentikan sumber lain.
6. Bila PDF tanpa lapisan teks, jalankan OCR otomatis (bagian 12.1).
7. AI mengekstrak teks dan data bibliografi. Metadata dari sumber
   diprioritaskan dibanding tebakan AI; user dapat mengoreksi manual
   (bagian 12.4).
8. AI menghasilkan isi laporan. Sitasi dalam teks dibuat oleh kode dari id
   sumber, bukan diketik AI (bagian 11.4).
9. Sistem memverifikasi cuplikan sumber secara deterministik dan menandai
   tiap kalimat "terverifikasi", "tidak terverifikasi", atau "bukan klaim
   faktual"; kalimat yang belum selesai wajib ditandai selesai oleh user
   sebelum ekspor (bagian 11, 19).
10. User meninjau: parafrase atau edit manual (bagian 19), ulangi sampai
    setuju.
11. Setuju: generate DOCX dari template, masukkan logo ke cover (bagian 20).
12. Simpan file DOCX di `C:\Generator`.

Catatan responsivitas (menjawab putaran 6): operasi yang memakan waktu
(OCR, satu panggilan AI per batch, pengambilan link web, render) berjalan di
thread lain. Thread utama Tkinter hanya menyentuh widget lewat antrean dan
`after`, sehingga jendela tidak membeku atau tampak "Not Responding" di
Windows.

## 11. Strategi Anti-Delusi

Grounding, cuplikan, dan temperatur rendah tidak cukup: model bisa
mengarang cuplikan, atau menempelkan cuplikan asli pada klaim yang tidak
didukung. Karena itu bukti sumber diverifikasi secara deterministik oleh
kode, dan sitasi dalam teks dibuat oleh kode.

### 11.1 Bentuk Keluaran AI (JSON)

- Paragraf berupa daftar kalimat. Tiap kalimat punya `text` (teks
  kalimat), `quote` (cuplikan dari sumber), `source_ids` (id sumber), dan
  `is_factual` (penanda apakah kalimat itu klaim faktual atau bukan).
- Satu cuplikan untuk satu kalimat, bukan satu cuplikan untuk paragraf
  panjang.
- Satu kalimat = satu klaim. Kode menempatkan sitasi di **akhir kalimat**
  itu; AI tidak menulis sitasi sendiri.
- Karena AI mengembalikan satu objek per kalimat, kode tidak perlu
  memecah kalimat sendiri. Ini menghindari pemecahan yang salah pada
  singkatan seperti "dkk.", "Dr.", dan "et al." (menjawab syarat A).

### 11.2 Verifikasi Deterministik

- Setiap `quote` dicocokkan hanya terhadap teks **lengkap** sumber yang
  disebut di `source_ids` untuk klaim itu, bukan terhadap semua sumber,
  dan bukan hanya chunk tempat cuplikan ditemukan, supaya cuplikan yang
  melintasi batas chunk tetap bisa dicocokkan.
- Pencocokan dilakukan setelah normalisasi: spasi berlebih, besar-kecil
  huruf, dan tanda hubung di akhir baris (kata terpenggal akibat tata
  letak PDF, termasuk jurnal dua kolom).
- Cuplikan punya panjang minimum (misalnya 8 kata). Cuplikan terlalu
  pendek dianggap tidak valid karena hampir pasti cocok di mana saja.
- Status per kalimat ada tiga: `terverifikasi` (cuplikan ada di sumber
  yang dirujuk), `tidak terverifikasi` (cuplikan tidak ditemukan, atau
  cuplikan terlalu pendek, atau `source_ids` kosong), dan `bukan klaim
  faktual` (kalimat yang AI tandai `is_factual` salah, misalnya kalimat
  pengantar).
- Tidak ada kalimat yang lolos tanpa status. Kalimat yang tidak punya
  entri sama sekali dari AI dianggap `tidak terverifikasi`, bukan
  diabaikan.
- Kalimat hasil edit manual (`origin="manual"`) selalu `tidak
  terverifikasi` tanpa memeriksa cuplikan, karena verifikasi otomatis hanya
  berlaku untuk teks AI (menjawab putaran 6, bagian 19).

### 11.3 Arti Status (Kejujuran)

- `terverifikasi` berarti "cuplikan itu ada di sumber yang dirujuk", bukan
  "klaim itu benar". Memastikan klaim sesuai cuplikan tetap tugas user.
- Ada dua risiko: false negative (parafrase internal, perbedaan unicode,
  tanda hubung) dan false positive (cuplikan asli ditempel pada klaim yang
  salah). Pemetaan ke sumber yang dirujuk dan panjang minimum mengurangi
  false positive, tetapi tidak menghapusnya.
- Tinjauan user adalah penjaga terakhir.

### 11.4 Sitasi Terikat (menjawab putaran 2, temuan 2)

- Sitasi dalam teks dibuat oleh kode memakai `citation.py` dari
  `source_ids` tiap klaim, bukan diketik AI. Jadi sitasi selalu cocok
  dengan daftar pustaka.
- Beberapa sumber dalam satu kalimat digabung dalam satu tanda kurung,
  dipisah titik koma, urut alfabetis seperti daftar pustaka, misalnya
  `(Abadi, 2020; Zed, 2021)` (APA 7).
- Daftar pustaka hanya memuat sumber yang benar-benar dikutip (dirujuk
  `source_ids` oleh kalimat yang sitasinya benar-benar dipasang). Sumber yang
  dimasukkan user tetapi tidak dikutip ditampilkan sebagai peringatan di
  GUI. Kalimat yang sitasinya dimatikan user (`citation` salah) tidak
  dihitung sebagai mengutip, sehingga sumber yang hanya muncul di situ tidak
  masuk daftar pustaka (menjawab putaran 6).
- Bila user mengedit manual dan menghapus sitasi, klaim itu ditandai tanpa
  sitasi (`Sentence.citation` dimatikan) dan `tidak terverifikasi`.
  Aplikasi tidak menambahkan sitasi kembali secara paksa, tetapi menawarkan
  tombol "Pulihkan sitasi" yang menyalakan `citation` kembali dari
  `source_ids` yang tetap tersimpan.

### 11.5 Perilaku di GUI dan Blokir Ekspor

- Klaim/paragraf `tidak terverifikasi` ditandai jelas.
- Ekspor DOCX diblokir secara default bila masih ada kalimat `tidak
  terverifikasi` atau `bukan klaim faktual` yang belum ditandai selesai
  oleh user (lihat bagian 19). User boleh mengekspor setelah konfirmasi
  eksplisit, dan statusnya dicatat di log.

### 11.6 Prompt Injection

- Teks sumber diperlakukan sebagai **data**, bukan perintah. Prompt
  menginstruksikan model mengabaikan perintah apa pun yang ada di dalam
  teks sumber.

### 11.7 Temperatur AI

- Temperatur diatur rendah untuk mengurangi variasi keluaran.

## 12. Penanganan Error (Anti-Crash)

Prinsip: kegagalan satu sumber tidak menghentikan sumber lain; tidak ada
tumpukan error ke layar; log ke file tanpa API key.

### 12.1 PDF Hasil Scan (OCR ada di versi 1)

- Bila PDF tidak punya lapisan teks, deteksi dan jalankan OCR otomatis.
- Pipeline OCR: render halaman ke gambar dengan pypdfium2, lalu OCR dengan
  rapidocr (mesin onnxruntime). Semua dipasang lewat pip, tanpa biner
  eksternal.
- Hasil OCR dipakai sebagai teks sumber seperti sumber lain, dan tetap
  masuk verifikasi cuplikan (bagian 11.2).
- Bila OCR gagal, tampilkan pesan jelas per sumber dan sediakan opsi tempel
  teks manual untuk sumber itu.
- Catatan kualitas: hasil OCR bisa kurang akurat, sehingga verifikasi
  cuplikan bisa menandai lebih banyak klaim "tidak terverifikasi". Ini
  ditulis di README.
- Verifikasi: kualitas OCR aksara Indonesia diuji dengan contoh PDF scan
  berbahasa Indonesia sebelum dependensi ini dikunci di versi rilis.

### 12.2 Website Diblokir atau Butuh JavaScript

- Tampilkan pesan gagal per sumber.
- Sediakan opsi tempel teks manual sebagai cadangan untuk sumber itu.

### 12.3 PDF Sangat Panjang (Chunking)

- Teks sumber dipotong menjadi beberapa bagian (chunk) sebelum dikirim ke
  AI agar tidak melewati batas konteks model.
- Chunk dikelompokkan ke dalam batch di bawah batas karakter prompt; AI
  dipanggil sekali per batch, lalu hasil tiap batch digabung dan kalimat
  yang sama (setelah normalisasi) dibuang duplikatnya. Dengan begitu
  seluruh teks sumber terpakai, bukan hanya bagian awal.
- Chunk diberi id. Verifikasi cuplikan (bagian 11.2) tetap memakai teks
  lengkap sumber yang dirujuk, bukan hanya chunk, supaya cuplikan yang
  melintasi batas chunk tetap cocok.

### 12.4 Metadata Bibliografi Tidak Lengkap atau Salah

- Sediakan formulir tinjau dan koreksi manual sebelum sumber masuk daftar
  pustaka.
- Ekstraksi bibliografi mengirim hanya sebagian teks ke AI: `max_chars`
  karakter pertama (misalnya 6000) ditambah sedikit ekor (misalnya 500),
  bukan seluruh teks. Metadata (judul, penulis, tahun) biasanya ada di awal
  atau akhir dokumen, jadi kutipan terbatas sudah cukup dan PDF panjang
  tidak melewati batas konteks model. Isi laporan tetap memakai chunking
  12.3.
- Metadata yang tersedia dari PDF, DOI, atau halaman web diprioritaskan
  dibanding tebakan AI.
- Formulir memuat kolom **nama keluarga** per penulis yang bisa diedit
  user. Nama Indonesia seperti "Budi Santoso" tidak punya pemisah jelas,
  jadi kode tidak menebak; user menandai bagian mana yang jadi nama
  keluarga (atau mengosongkannya bila nama hanya satu kata). Menjawab
  putaran 3, syarat B.
- Penulis dimodelkan eksplisit: nama keluarga, nama depan, penanda
  organisasi, dan singkatan organisasi (bila ada). Kode tidak pernah
  menebak pemisahan dari satu string nama. AI boleh mengisi usulan awal,
  tetapi user dapat mengoreksinya di formulir.

### 12.5 Template Rusak atau Bukan DOCX

- Tolak dengan pesan ramah, bukan crash.

### 12.6 Logo Bukan Gambar atau Tidak Ditemukan

- Lewati logo dengan peringatan, tanpa menggagalkan render.

### 12.7 Respons AI Bukan JSON Valid

- Tangani dan minta ulang (retry sekali), lalu tampilkan pesan ramah.

### 12.8 Lokasi Tidak Bisa Ditulis

- Bila `C:\Generator` atau folder datanya tidak bisa ditulis, aplikasi
  memakai path relatif terhadap lokasi aplikasi, dan bila tetap gagal,
  meminta user memilih folder.

## 13. Struktur File

```
C:\Generator\
  README.md                     panduan pemakaian + format template
  requirements.txt              daftar pustaka Python
  run.bat                       peluncur bootstrap (lihat bagian 16)
  .gitignore
  src/generator/
    config.py                   muat/simpan konfigurasi
    paths.py                    lokasi folder data (dengan fallback)
    logging_setup.py            log ke data/app.log tanpa API key
    database.py                 akses SQLite (profil mahasiswa, dosen,
                                matkul, logo, template)
    sources/
      errors.py                 kelas SourceReadError tunggal
      pdf_reader.py             ekstrak teks dari PDF + deteksi scan
      ocr.py                    render halaman (pypdfium2) + OCR (rapidocr)
      web_reader.py             ambil konten dari URL
      chunking.py               pemotongan teks panjang
    ai/
      client.py                 klien OpenAI-compatible
      prompts.py                template prompt (teks sumber = data)
      bibliography.py           ekstrak data bibliografi
      citation.py               format sitasi APA 7th (murni, mudah ditest)
      content.py                tulis isi laporan berbasis sumber
    verification.py             verifikasi deterministik cuplikan sumber
    drafts.py                   simpan/muat draf sementara (termasuk tanda selesai)
    report.py                   gerbang ekspor, label sitasi, daftar pustaka terpakai
    document/
      placeholders.py           pencarian/penggantian penanda lintas run
      template.py               baca dan validasi template DOCX
      renderer.py               isi penanda, buat DOCX (logo, TOC)
    gui/
      app.py                    jendela utama dan menu
      worker.py                 jalankan operasi lama di thread, hasil lewat after
      tab_data.py               kelola profil mahasiswa, dosen, matkul, logo
      tab_template.py           kelola template
      tab_report.py             alur buat laporan
      tab_settings.py           pengaturan AI + tombol Tes koneksi
  tests/                        tes pytest
  data/                         diabaikan git (database, logo, template, config, log)
```

Catatan: `config.example.json` dihapus karena konfigurasi lewat GUI
(menjawab kontradiksi putaran 2). `bootstrap.bat` tidak dipakai; hanya
`run.bat`.

## 14. Yang Diserahkan ke Implementer

- Detail prompt AI dan bentuk JSON internal (dalam batas bagian 11.1).
- Tata letak persis tiap tab GUI.
- Pilihan pustaka kecil lain selama ramping, lisensi permissif, dan stabil.

## 15. Konfigurasi AI dan Halaman Pengaturan (menjawab P0-2)

- GUI memiliki tab **Pengaturan** berisi: URL endpoint, API key, nama
  model, dan temperatur.
- Tombol **Tes koneksi**: mengirim pesan uji singkat ke endpoint dan
  menampilkan hasil yang ramah ("Koneksi berhasil" atau "Gagal: alasan
  singkat").
- Penyimpanan API key: file `data/config.json`, diabaikan git, dan tidak
  pernah ditulis ke log. API key tersimpan **polos (belum terenkripsi)**;
  hal ini ditulis di README (menjawab catatan kecil putaran 2).
- Bila konfigurasi belum diisi, aplikasi tetap terbuka dan menampilkan
  petunjuk menuju tab Pengaturan, bukan crash.

## 16. Instalasi dan Peluncuran Pertama (menjawab P0-3)

Keputusan untuk versi 1: **opsi (a)**, `run.bat` yang melakukan bootstrap.

Alasan: tetap memakai Python 3.12 sesuai batasan, tanpa langkah build
tambahan; transparan dan mudah diperbarui; menghindari komplikasi
PyInstaller (ukuran besar, deteksi antivirus).

Perilaku `run.bat`:

1. Deteksi Python 3.12. Bila tidak ada, tampilkan pesan yang menuntun user
   memasang Python (dengan tautan) dan berhenti dengan rapi.
2. Buat virtual environment di folder aplikasi bila belum ada.
3. Pasang dependensi dari `requirements.txt` saat pertama kali.
4. Tampilkan pesan **progres** saat mengunduh dan memasang dependensi,
   khususnya OCR dan mesin ONNX yang berukuran besar, supaya user tidak
   mengira aplikasi macet (menjawab putaran 2, temuan 6).
5. Jalankan aplikasi.

Dampak bila kelak memilih `.exe` (opsi b): pengguna tidak perlu Python,
tetapi ukuran berkas membesar, stabilitas bergantung pada build PyInstaller,
dan pembaruan lebih rumit. Ini dicatat sebagai opsi masa depan.

## 17. Spesifikasi Modul Sitasi APA 7th (menjawab P1-2, diperluas putaran 2)

Aturan ini diverifikasi ke apastyle.apa.org (Author-Date Citation System),
Purdue OWL (Reference List: Author/Authors), dan panduan perpustakaan
universitas (UQ, JCU) pada 2026-10-18. Lihat bagian 23 untuk daftar sumber.

Catatan model data: penulis disimpan sebagai objek eksplisit (nama
keluarga, nama depan, penanda organisasi, singkatan), bukan string
tunggal, supaya kode tidak menebak pemisahan nama (bagian 12.4).

### 17.1 Sitasi Dalam Teks

- Satu penulis: `(Santoso, 2020)`.
- Dua penulis: `(Santoso & Wijaya, 2020)`.
- Tiga penulis atau lebih: `(Santoso et al., 2020)` mulai dari sitasi
  pertama.
- Parenthetical memakai `&`; narrative memakai kata "and".
- Tanpa tahun: `(Santoso, n.d.)`.
- Penulis organisasi dengan singkatan: nama penuh pada sitasi pertama
  disertai singkatan, lalu singkatan pada sitasi berikutnya, misalnya
  `(Kementerian Pertanian [Kementan], 2020)` lalu `(Kementan, 2020)`.
- Batasan versi ini: sitasi yang dihasilkan selalu memakai bentuk
  `Nama Penuh [Singkatan]`, belum beralih ke singkatan saja setelah sitasi
  pertama (dicatat di README).
- Penulis organisasi tanpa singkatan: pakai nama penuh, misalnya
  `(Stanford University, 2020)`.
- Penulis pertama sama tetapi penulis kedua berbeda: tambahkan nama sampai
  sitasi jelas berbeda, lalu baru `et al.`, misalnya `(Cooper, Lee, et al.,
  2015)` dan `(Cooper, Ross, et al., 2015)`. Jangan memakai `a`/`b` untuk
  kasus ini.
- Nama penulis satu kata (tanpa nama keluarga): kata itu diperlakukan
  sebagai nama keluarga, misalnya `(Sukarno, 2020)`.

### 17.2 Daftar Pustaka

- Sampai 20 penulis: cantumkan semua penulis, pisahkan dengan koma, dan
  `&` sebelum penulis terakhir. Jangan pakai "et al." di daftar pustaka.
- 21 penulis atau lebih: cantumkan 19 penulis pertama, elipsis (…), lalu
  penulis terakhir (tanpa `&`).
- Tanpa penulis: judul dipakai di posisi penulis.
- Penulis organisasi: tulis nama penuh.
- Nama penulis satu kata: ditulis apa adanya.
- DOI ditulis sebagai `https://doi.org/<doi>`.

### 17.3 Pengurutan

- Daftar pustaka diurutkan alfabetis menurut nama keluarga penulis
  pertama, lalu tahun.
- Penulis dan tahun sama: urutkan menurut judul, tambahkan huruf `a`, `b`,
  `c` setelah tahun di sitasi dalam teks dan daftar pustaka.
- Penulis pertama sama tetapi penulis kedua atau ketiga berbeda: urutkan
  alfabetis menurut nama keluarga penulis kedua (lalu ketiga bila perlu).

### 17.4 Daftar Kasus Uji Minimal untuk `citation.py`

- Satu penulis.
- Dua penulis.
- Tiga penulis dan lebih (et al.).
- Lebih dari 20 penulis (19 + elipsis + terakhir).
- Tanpa penulis.
- Tanpa tahun (n.d.).
- Sumber situs web.
- Penulis organisasi dengan singkatan.
- Penulis organisasi tanpa singkatan.
- Nama penulis satu kata.
- Urutan alfabetis.
- Penulis dan tahun sama (a, b, c).
- Penulis pertama sama, penulis kedua berbeda (disambiguasi nama).
- Indeks label cocok dengan indeks asli sumber, bukan posisi hasil urut.
- Beberapa sumber dalam satu kalimat digabung dipisah titik koma.

## 18. Struktur Isi Laporan dan Style DOCX (menjawab P1-3)

### 18.1 Pemetaan Isi ke Style

- AI mengembalikan isi terstruktur (JSON) berupa daftar bagian dengan
  tingkat judul (`level`) dan paragraf.
- Renderer memetakan: `level 1` ke style Heading 1, `level 2` ke Heading 2,
  paragraf ke style Normal milik template.
- Template user belum tentu memuat style Heading. Renderer wajib memeriksa
  dulu: bila style Heading yang diminta tidak ada, renderer membuat style
  itu (berbasis Normal, tebal) atau jatuh ke tebal pada style Normal, bukan
  melempar `KeyError` dan bukan membuat aplikasi crash (menjawab putaran 6,
  temuan 5, sejalan dengan anti-goal crash).

### 18.2 Penentu Struktur

- Struktur bab ditentukan oleh **outline laporan** yang diisi user di tab
  Buat Laporan (daftar judul bab). AI menulis isi untuk tiap bab.
- Bila user tidak mengisi outline, AI boleh mengusulkan outline, dan user
  menyetujuinya sebelum isi ditulis.

### 18.3 Daftar Isi (TOC)

- Memakai field Table of Contents otomatis milik Word, disisipkan pada
  penanda `{{DAFTAR_ISI}}` (wajib).
- Konsekuensi: field baru terisi setelah di-update di Word. README
  menjelaskan "klik kanan pada daftar isi, pilih Update Field". Perlu
  dicatat: pada sebagian versi Word, opsi update saat membuka memunculkan
  dialog konfirmasi; ini diuji dan dicatat di README (menjawab catatan
  kecil putaran 2).

### 18.4 Style Sitasi dan Daftar Pustaka

- Sitasi dalam teks ditulis sebagai teks biasa.
- Daftar pustaka memakai hanging indent.

### 18.5 Pengisian Nilai Penanda (menjawab putaran 6, temuan 4)

- Nilai penanda sederhana diisi kode dari profil dan tanggal sistem, bukan
  oleh AI: `{{NAMA}}`, `{{NIM}}`, `{{PRODI}}` dari profil mahasiswa;
  `{{MATA_KULIAH}}` dan `{{DOSEN}}` dari pilihan user; `{{JUDUL}}` dari
  kotak judul; `{{TANGGAL}}` dari tanggal sistem; `{{TAHUN}}` dari tahun
  tanggal sistem.
- Format `{{TANGGAL}}` memakai bahasa Indonesia, misalnya "18 Oktober 2026"
  (nama bulan Indonesia), supaya konsisten dengan dokumen berbahasa
  Indonesia. `{{TAHUN}}` diisi empat digit tahun.
- Penanda opsional (`{{TAHUN}}`, `{{PRODI}}`) yang tidak punya nilai
  diganti string kosong, bukan dibiarkan mentah, supaya `{{TAHUN}}` tidak
  pernah tercetak di dokumen. Hal yang sama berlaku untuk `{{LOGO}}` yang
  gagal dimuat: paragraf penandanya dikosongkan agar tidak ada penanda
  mentah yang tertinggal (menjawab putaran 6, temuan 5).

## 19. Alur Peninjauan dan Edit Manual (menjawab P1-4, diperjelas putaran 6)

- Asal teks ditandai **per kalimat** lewat `Sentence.origin` bernilai `"ai"`
  atau `"manual"`. Tiap kalimat juga punya `Sentence.citation` (benar bila
  sitasi otomatis dipasang). Tidak ada `manual_edits` terpisah; teks dan
  asal tersimpan langsung di dalam `sections` draf, jadi tidak ada dua
  sumber kebenaran yang bisa berselisih.
- Editing dilakukan **per kalimat**, bukan per paragraf: GUI menampilkan
  satu kotak teks untuk tiap kalimat. Menyimpan satu kotak menghasilkan
  kalimat baru dengan `origin="manual"` dan `uid` tetap (kalimat yang sama,
  teks baru). Tidak ada pemetaan balik dari satu area teks paragraf ke
  beberapa kalimat, karena itu bertentangan dengan model satu kalimat satu
  klaim (11.1). Kalimat manual selalu berstatus `tidak terverifikasi` walau
  teks kebetulan cocok dengan cuplikan, karena verifikasi otomatis (11.2)
  hanya berlaku untuk teks AI. Kalimat manual dan kalimat `bukan klaim
  faktual` dianggap belum selesai sampai user menekan **Tandai selesai**
  untuk bagian itu.
- **Parafrase lewat AI:** mengirim kalimat terpilih ke AI untuk ditulis
  ulang. Hasilnya kalimat baru berstatus `origin="ai"` yang tetap harus
  lulus verifikasi cuplikan; kalimat yang tidak lulus berstatus `tidak
  terverifikasi`. Parafrase terikat ke `source_ids` yang sama.
- **Menjalankan ulang AI** menimpa kalimat hasil AI dan mempertahankan
  kalimat manual (digabung oleh fungsi tersendiri, diuji), kecuali user
  memilih **"tulis ulang semua"** yang juga menimpa kalimat manual.
- Bila user menghapus sitasi saat mengedit, lihat bagian 11.4: kalimat itu
  tetap terhubung ke `source_ids` tetapi `citation` dimatikan, ditandai
  tanpa sitasi, dan ada tombol **Pulihkan sitasi** yang menyalakan
  `citation` kembali. Kalimat manual tetap `tidak terverifikasi` (bukan
  dianggap terverifikasi) sampai ditandai selesai.
- **Usul outline otomatis** (menjawab 18.2): bila user mengosongkan kotak
  outline, tombol Usulkan Outline meminta AI mengusulkan daftar judul bab
  dari topik dan ringkasan sumber; hasilnya mengisi kotak outline dan user
  menyetujui atau memperbaikinya sebelum isi ditulis.

## 20. Keputusan P2

- **Logo tidak persegi:** disesuaikan (fit) ke dalam kotak 5x5 cm dengan
  mempertahankan rasio aspek, tanpa dipotong, lalu dipusatkan. Format
  gambar yang didukung mengikuti dukungan python-docx (PNG, JPG, GIF, BMP).
- **Fallback lokasi:** pakai path relatif terhadap lokasi aplikasi bila
  folder utama tidak tersedia; bila tetap gagal, minta user memilih folder.
- **Privasi:** teks sumber dikirim ke layanan AI sesuai endpoint yang
  diatur user. Pemberitahuan ini ditulis di README dan di layar Pengaturan.
- **Penanda tambahan:** `{{TAHUN}}` dan `{{PRODI}}` adalah penanda opsional
  (bagian 9). Penanda tak dikenal dibiarkan apa adanya tetapi memicu
  peringatan sebelum ekspor, bukan crash.
- **Migrasi database:** tabel `schema_version` disimpan untuk menandai
  versi skema.
- **Draf laporan:** disimpan sementara di `data/drafts/` selama pengerjaan,
  dihapus saat ekspor atau dibuang user (bagian 8).
- **Log:** error ditulis ke `data/app.log`, tanpa menampilkan tumpukan
  error ke user dan tanpa mencatat API key.

## 21. Kriteria Penerimaan

1. Template tanpa salah satu penanda wajib menghasilkan dialog peringatan
   yang menyebut nama penanda yang hilang, tanpa crash.
2. Template dengan penanda terpecah run tetap terisi dengan benar, dan teks
   sebelum/sesudah penanda tidak hilang.
3. Cuplikan sumber yang dikarang AI (tidak ada di sumber yang dirujuk)
   ditandai "tidak terverifikasi".
4. Satu sumber gagal (PDF scan gagal OCR, link diblokir) tidak
   menghentikan pemrosesan sumber lain.
5. User baru dapat menjalankan aplikasi dan mengisi pengaturan AI tanpa
   mengetik perintah terminal selain yang sudah dibungkus `run.bat`.
6. Data profil mahasiswa, dosen, mata kuliah, dan logo cukup diisi sekali
   dan dapat dipilih ulang pada laporan berikutnya.
7. Logo di cover berukuran tepat 5x5 cm.
8. Semua modul murni (`citation.py`, validasi template, verifikasi
   cuplikan) memiliki tes pytest.
9. Sumber PDF hasil scan menghasilkan teks lewat OCR, dan bila OCR gagal
   muncul pesan ramah dan opsi tempel teks manual.
10. Ekspor DOCX diblokir saat masih ada kalimat tak terverifikasi atau
    bukan klaim faktual yang belum ditandai selesai, dan bisa dilanjutkan
    setelah konfirmasi eksplisit user.
11. Template dengan `{{DAFTAR_ISI}}` menghasilkan daftar isi (field TOC) di
    DOCX.
12. Jendela tetap responsif (tidak "Not Responding") saat OCR, panggilan AI
    per batch, atau pengambilan link web berjalan, karena operasi lama
    berjalan di thread lain dan UI diperbarui lewat `after`.
13. Template user tanpa style Heading tetap menghasilkan DOCX (renderer
    membuat atau jatuh ke style tebal) tanpa crash.
14. Penanda opsional tanpa nilai (`{{TAHUN}}`, `{{PRODI}}`) dan `{{LOGO}}`
    yang gagal dimuat tidak pernah tercetak sebagai penanda mentah di DOCX.
15. Kalimat hasil edit manual dan kalimat `bukan klaim faktual` tidak dapat
    lolos gerbang ekspor sebelum ditandai selesai lewat `uid` kalimat.

## 22. Keputusan Terbuka yang Sudah Diselesaikan (2026-10-18)

1. Instalasi versi 1: `run.bat` bootstrap. Dipilih agent karena user
   menyerahkan keputusan (jawaban: "yang bagus aja"). `.exe` tetap sebagai
   opsi masa depan.
2. Struktur bab laporan: diisi user sebagai outline di aplikasi.
3. OCR PDF hasil scan: ada di versi 1. Lihat bagian 12.1.
4. Fitur spec yang belum punya task (putaran 6): **parafrase lewat AI, usul
   outline otomatis, dan "tulis ulang semua" dipertahankan di versi 1**,
   masing-masing diberi task dan tes sendiri (8b, 17a, 17b), bukan dicoret.
5. Template tidak diberi kolom status di database (putaran 6): status
   "lengkap/tidak lengkap" dihitung ulang dengan `validate_template` saat
   daftar ditampilkan, supaya tidak ada status basi. Yang ditolak hanya
   pemakaian template tidak lengkap di tab Buat Laporan (9.3).

## 23. Catatan Revisi

### Putaran 1: diterima

- P0-1 sampai P0-4, P1-1 sampai P1-4, dan P2 semuanya diterima dan ditulis
  ulang di Revisi 2 (verifikasi deterministik, tab Pengaturan, run.bat
  bootstrap, penanganan penanda lintas run, keterbatasan sumber, spesifikasi
  APA 7th, struktur DOCX, alur peninjauan, keputusan P2).
- Tidak ada temuan yang ditolak pada putaran 1.

### Putaran 2: diterima

- **Celah 1 (verifikasi cuplikan):** diterima. Cuplikan dicocokkan hanya
  terhadap sumber yang dirujuk `source_ids`, ada panjang minimum, satu
  cuplikan per klaim, arti status diperjelas, verifikasi memakai teks
  lengkap (bukan chunk), dan normalisasi tanda hubung akhir baris
  (bagian 11.1 sampai 11.3, 12.3).
- **Celah 2 (sitasi terikat):** diterima. Sitasi dalam teks dibuat kode
  dari `source_ids`; daftar pustaka hanya memuat sumber yang dikutip;
  penghapusan sitasi saat edit manual ditangani (bagian 11.4, 19).
- **Celah 3 (penggantian penanda):** diterima. Teks sebelum/sesudah
  penanda dipertahankan; penanda khusus wajib berdiri sendiri; penanda
  tak dikenal memicu peringatan sebelum ekspor (bagian 9.1, 9.2, 9.4).
- **Celah 4 (kontradiksi antar bagian):** diterima dan diperbaiki.
  `{{DAFTAR_ISI}}` menjadi penanda wajib; `{{PRODI}}` punya sumber nilai;
  `config.example.json` dihapus; `bootstrap.bat` dihapus; kalimat "pilihan
  teknologi tidak berubah" diperbaiki (bagian 6, 9, 13, 16).
- **Celah 5 (profil mahasiswa):** diterima. Tabel `profil_mahasiswa`
  ditambahkan (bagian 7).
- **Celah 6 (dependensi OCR):** diterima dan diverifikasi. Hasil:
  `rapidocr-onnxruntime` 1.4.4 mendukung Python 3.12 tetapi sudah
  digantikan `rapidocr` 3.x (Apache-2.0, `requires_python <4,>=3.8`,
  mendukung 3.12/3.13); `onnxruntime` berlisensi MIT; **PyMuPDF berlisensi
  AGPL**, sehingga diganti `pypdfium2` 5.14.0 (BSD-3-Clause / Apache-2.0,
  `requires_python >=3.6`). Pesan progres ditambahkan ke run.bat. Kualitas
  OCR aksara Indonesia akan diuji sebelum dikunci (bagian 6, 12.1, 16).
- **Celah 7 (aturan APA):** diterima. Ditambah aturan penulis organisasi
  (dengan dan tanpa singkatan), nama penulis satu kata, dan penulis pertama
  sama dengan penulis kedua berbeda (bagian 17.1 sampai 17.4).
- **Catatan kecil:** diterima. Konsekuensi update field TOC dicatat
  (18.3); API key polos ditulis di README (15); prompt injection ditangani
  dengan memperlakukan teks sumber sebagai data (11.6); kriteria
  penerimaan ditambah butir 9, 10, 11 (bagian 21).

### Putaran 3: diterima

- Syarat A (penempatan sitasi): satu klaim = satu kalimat, kode menempatkan
  sitasi di akhir kalimat (bagian 11.1).
- Syarat B (nama penulis Indonesia): formulir koreksi metadata memuat kolom
  nama keluarga yang bisa diedit user, kode tidak menebak (bagian 12.4).
- Syarat C (penanda khusus tidak berdiri sendiri): disatukan menjadi
  penolakan dengan dialog ramah, sama seperti penanda wajib hilang (bagian
  9.3, 9.4).
- Pengecekan paket OCR langsung dari PyPI: `rapidocr` 3.10.0 (Apache-2.0,
  `requires_python <4,>=3.8`, mendukung 3.12) dan `onnxruntime` 1.31.0 (MIT,
  `requires_python >=3.11`, classifier 3.12 sampai 3.14). Klaim agent pada
  putaran 2 kini terverifikasi.
- Urutan implementasi: uji OCR dengan PDF scan berbahasa Indonesia menjadi
  langkah pertama sebelum requirements.txt dikunci (bagian 12.1).
- Draf laporan: disimpan sementara supaya pekerjaan tidak hilang, dan
  verifikasi bisa diulang (bagian 8, 20).
- URL sumber verifikasi dilengkapi (bagian ini, di bawah).

### Putaran 4 (Revisi 5): diterima

- Model penulis eksplisit: `Author(family, given, is_org, abbrev)`. Kode
  tidak menebak pemisahan nama; user mengoreksi di formulir (bagian 12.4,
  17). Ini menutup celah yang melemahkan syarat B.
- JSON per kalimat: paragraf berupa daftar kalimat, tiap kalimat punya
  `text`, `quote`, `source_ids`, `is_factual`. Kode tidak memecah kalimat
  sendiri, sehingga singkatan seperti "dkk." dan "Dr." tidak salah pecah
  (bagian 11.1).
- Status ketiga `bukan klaim faktual`, plus aturan bahwa kalimat tanpa
  entri dianggap `tidak terverifikasi`. Tidak ada kalimat yang lolos tanpa
  status. Gerbang ekspor memblokir sampai user menandai selesai (bagian
  11.2, 11.5, 19).
- Chunking: batch di bawah batas karakter, satu panggilan AI per batch,
  hasil digabung dan didedup, supaya seluruh teks sumber terpakai (bagian
  12.3).
- Perbaikan pelaksanaan: konfigurasi `pythonpath` pytest, fungsi tes koneksi
  bernama `check_connection` agar tidak terkumpul pytest sebagai tes, dan
  kontrak `fields` pada renderer (kunci penanda khusus diabaikan).

### Putaran 5 (Revisi 5, lanjutan): diterima

- Indeks sitasi: `LabeledSource` menyimpan `source_index` (indeks asli
  sumber), dan `order_and_label` hanya melabeli sumber yang benar-benar
  dikutip, sehingga label selalu cocok dengan `source_ids` dan sumber tak
  dikutip tidak memicu sufiks a/b/c (bagian 17.4).
- Beberapa sumber dalam satu kalimat digabung dalam satu tanda kurung,
  dipisah titik koma, urut alfabetis seperti daftar pustaka (APA 7),
  bukan beberapa tanda kurung berurutan (bagian 11.4, 17).
- Tanda selesai memakai `uid` kalimat yang stabil (bukan nomor posisi),
  disimpan di draf supaya tidak hilang saat aplikasi ditutup dan tidak
  berpindah saat kalimat disisip, dihapus, atau diurut ulang; ada tombol
  massal untuk kalimat bukan klaim faktual (bagian 17, 19).
- Batasan singkatan organisasi (nama penuh di semua kemunculan) dicatat di
  bagian 17.1 dan README.
- Id sumber yang tidak dikenal diperlakukan sebagai `tidak terverifikasi`
  dan tidak memasang label (bagian 11.2), dan tiap chunk diberi label
  `[sumber <id>]` saat dikirim ke AI (bagian 12.3).

### Putaran 6 (Revisi 5, sebelum GUI): diterima

Semua temuan putaran 6 dinilai sah dan diperbaiki.

- Fitur spec tanpa task: **parafrase lewat AI, usul outline, dan "tulis
  ulang semua" tetap ada di versi 1** dengan task dan tes sendiri (bagian
  18.2, 19; Task 8b, 17a, 17b). Tidak ada fitur spec yang menggantung tanpa
  task.
- Model "diedit manual" dijelaskan: asal ditandai per kalimat lewat
  `Sentence.origin` (`"ai"`/`"manual"`), ada kolom `Sentence.citation`, dan
  `DraftState.manual_edits` dihapus (teks dan asal tersimpan di `sections`).
  Kalimat manual selalu `tidak terverifikasi`; tombol Pulihkan sitasi
  menyalakan `citation` kembali (bagian 19; Task 8, 9, 17b).
- `report.pending` diperjelas: hanya kalimat yang statusnya bukan
  `terverifikasi` dan `uid`-nya belum ada di `done`, supaya kalimat
  terverifikasi tidak dihitung sebagai tertunda. Ada tes khusus (Task 17a).
- Pengisian nilai penanda ditugaskan ke kode (`report.build_fields`), termasuk
  format tanggal bahasa Indonesia; penanda opsional tanpa nilai dan
  `{{LOGO}}` yang gagal dimuat dikosongkan supaya tidak ada penanda mentah
  yang tercetak (bagian 18.5; Task 12, 17c).
- Style Heading yang tidak ada di template ditangani dengan membuat atau
  fallback, bukan `KeyError`; ada tes (bagian 18.1; Task 12).
- GUI tidak boleh membeku: operasi lama berjalan di thread lain dan UI
  diperbarui lewat `after` (bagian 10, 13; modul `gui/worker.py`; Task 13).
- Task GUI terbesar dipecah: 17a (generate dan tampilan status), 17b (edit,
  tandai selesai, pulihkan sitasi, parafrase), 17c (gerbang ekspor, isi
  fields, simpan DOCX).
- Temuan kecil: `AIClient` menangkap exception umum dan memeriksa
  `status_code` (Task 5); status template dihitung saat ditampilkan, dan
  penolakan terjadi saat template dipilih di tab Laporan (Task 15, 16);
  model rapidocr diunduh saat pertama jalan sehingga Task 1 butuh internet;
  header plan tidak lagi memanggil skill `superpowers:*` yang belum tentu
  ada di OpenCode, diganti instruksi eksekusi manual; ditambah **Task 0**
  (git init, venv, pip, letak dokumen); instruksi eksekusi ditulis eksplisit
  (satu task per giliran, jalankan pytest sebelum commit, berhenti bila tes
  gagal, jangan menebak API rapidocr, jangan menggabungkan task GUI).

### Putaran 6b (perbaikan lanjutan sebelum GUI): diterima

- **Perintah Python/venv:** header plan mewajibkan `.venv\Scripts\python -m
  pytest` dan `.venv\Scripts\python -m pip install`, karena aktivasi
  `activate` tidak bertahan antar panggilan shell agen.
- **Satu kelas `SourceReadError`:** didefinisikan di `sources/errors.py` dan
  diimpor `pdf_reader`/`web_reader`, supaya GUI menangkap keduanya (bagian
  13).
- **Edit manual per kalimat:** satu kotak teks per kalimat, menghindari
  pemetaan balik ambigu (bagian 19).
- **Ekstraksi bibliografi dibatasi:** hanya awal 6000 karakter plus ekor 500
  (bagian 12.4).
- **`cited_ids` mengikuti sitasi yang benar-benar dipasang** (bagian 11.4).
- **Pillow adalah dependensi runtime** (renderer memakainya untuk logo),
  bukan hanya tes (bagian 6/20).
- **Pembuat koneksi database tunggal** di `build_app` (Task 13).
- **Uji manual GUI** wajib setelah Task 13 sebelum menambah tab lain.
- **Konteks eksekusi:** semua perintah dijalankan dari root repo (tes
  memakai path relatif); `CHECKPOINT-2026-10-18.md` opsional di Task 0
  (jangan sampai agen berhenti hanya karena catatan sesi tidak ada).
- **Risiko OCR:** kegagalan pada fixture berfont Pillow tidak cukup untuk
  menyimpulkan rapidocr tidak cocok; uji juga PDF scan Indonesia asli
  (bagian 12.1).

### Ditolak

- Tidak ada temuan yang ditolak pada putaran 2 dan 3. Semua temuan dinilai
  sah.

### Sumber Verifikasi Fakta (2026-10-18)

- APA in-text author-date:
  https://apastyle.apa.org/style-grammar-guidelines/citations/basic-principles/author-date
- APA reference list author rules (Purdue OWL):
  https://owl.purdue.edu/owl/research_and_citation/apa_style/apa_formatting_and_style_guide/reference_list_author_authors.html
- Panduan perpustakaan University of Queensland (group authors):
  https://guides.library.uq.edu.au/referencing/apa7/author-info
- Panduan perpustakaan James Cook University (order of authors, et al.):
  https://libguides.jcu.edu.au/apa/authors
- PyPI metadata: `rapidocr` 3.10.0 (Apache-2.0, `requires_python <4,>=3.8`),
  `onnxruntime` 1.31.0 (MIT, `requires_python >=3.11`, classifier 3.12),
  `rapidocr-onnxruntime` 1.4.4 (`<3.13,>=3.6`), `pypdfium2` 5.14.0
  (BSD-3-Clause / Apache-2.0), `PyMuPDF` (AGPL)
