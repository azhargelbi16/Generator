# DOKUMENTASI WORKFLOW & RDE
## Aplikasi Generator Laporan Akademik

Dokumen ini dibuat khusus untuk **pemula / non-teknis** agar dapat memahami alur kerja aplikasi dari awal sampai akhir, tanpa perlu baca kode program.

---

## 1. ALUR PENGGUNA SECARA UMUM (User Journey)

Berikut adalah langkah demi langkah apa yang dilakukan pengguna saat menggunakan aplikasi ini:

```
Mulai: Buka aplikasi via run.bat
        |
        v
Tab Pengaturan: Isi Base URL, API Key, Model, Temperatur
        |
        v
Tes Koneksi AI
        |
    +---+---+
    |       |
  Tidak   Ya
    |       |
    v       v
Kembali  Simpan Pengaturan AI
ke atas       |
              v
       Tab Data: Isi Nama, NIM, Prodi
              |
              v
       Unggah Logo
              |
              v
       Tambah Dosen & Mata Kuliah
              |
              v
       Tab Template: Unggah template .docx
              |
          +---+---+
          |       |
        Tidak   Ya
          |       |
          v       v
      Kembali  Tab Buat Laporan
      ke atas         |
                      v
        Masukkan sumber: PDF / DOI (CrossRef) / Web / Teks manual
                      |
                      v
        Koreksi metadata penulis jika perlu
                      |
                      v
        Tulis judul laporan
                      |
                  +---+---+
                  |       |
               A/B/C   Bebas
                  |       |
                  v       v
        Outline otomatis  Buat outline sendiri
        sesuai varian     / Usulkan outline
                  |       |
                  +---+---+
                      |
                      v
               Klik Generate
                      |
                      v
        AI menghasilkan bab-bab laporan
                      |
                      v
        Tab Review Hasil: Baca per kalimat
                      |
                  +---+---+
                  |       |
                 Ya     Tidak
                  |       |
                  v       v
   Muncul status + tombol  Klik di area kosong
   (Parafrase / Tandai     untuk menyimpan
    Selesai / Pulihkan    perubahan
    Sitasi)
                  |       |
                  v       v
        Edit kalimat langsung di tempat (jika perlu)
                  |
                  v
        Semua kalimat sudah ditandai selesai?
                  |
              +---+---+
              |       |
            Tidak    Ya
              |       |
              v       v
     Ekspor DIBLOKIR   Klik Simpan DOCX
              |       |
              v       v
        (tidak bisa   File tersimpan di folder output\
         menyimpan)       |
              |       v
              +---+---+
                  |
                  v
               Selesai
```

---

## 2. ARSITEKTUR SISTEM (Bagian Dalam Aplikasi)

Ini adalah gambaran bagian-bagian dalam aplikasi dan bagaimana mereka saling berinteraksi:

```
ANTARMUKA PENGGUNA (React 19 + TypeScript + Tailwind via pywebview)
--------------------------------
[Tab Data]   [Tab Template]   [Tab Buat Laporan]   [Tab Review Hasil]   [Tab Pengaturan]
       \          |                  |                    |                 /
        \         |                  |                    |                /
         \        |                  |                    |               /
          \       |                  |                    |              /
           \      |                  |                    |             /
            \     |                  |                    |            /
             \    |                  |                    |           /
              \   |                  |                    |          /
               \  |                  |                    |         /
                \ |                  |                    |        /
                 \|                  |                    |       /
                  v                  v                    v      v
           +-------------------------------------------------------------+
           |                    LOGIKA INTI (Core)                       |
           |  [Report Controller] [Draf Otomatis] [Validasi Template]   |
           |  [Format Spec A/B/C] [Verifikasi Sitasi]                    |
           +-------------------------------------------------------------+
                           |          |          |          |          |
                           v          v          v          v          v
                  [AI Client]  [AI Content]  [AI Citation] [AI Bibliography]
                  (Layanan AI - Eksternal, butuh internet)
                           |
                           v
                  [PDF Reader+OCR] [Web Reader] [Teks Manual]
                  (Sumber Data)
                           |
                           v
                  [Template .docx] [Renderer DOCX] [Penanda {{...}}]
                  (Dokumen DOCX)
                           |
                           v
           +-------------------------------------------------------------+
           |              DATABASE LOKAL SQLite                          |
           |  [Profil, Dosen, Mata Kuliah] [Draf Tersimpan]              |
           |  [Config JSON] [Log Aplikasi]                               |
           +-------------------------------------------------------------+
```

---

## 3. RDE - RANCANGAN DESAIN ELEMEN (Versi Sederhana)

RDE adalah dokumen yang menjelaskan **apa saja elemen dalam aplikasi** dan **apa fungsinya**, dalam bahasa mudah dipahami.

### 3.1 Elemen Halaman (Tab)

| Tab | Fungsi Utama | Untuk Apa? |
|-----|-------------|------------|
| **Pengaturan** | Mengatur koneksi ke layanan AI | Menghubungkan aplikasi dengan AI (LM Studio atau serupa) agar bisa menghasilkan teks laporan |
| **Data** | Mengisi profil mahasiswa, dosen, mata kuliah, dan logo | Data ini akan dicetak di sampul dan header laporan |
| **Template** | Mengunggah dan memvalidasi file template .docx | Template adalah "bentuk" laporan akhir dengan penanda `{{JUDUL}}`, `{{NAMA}}`, dst. |
| **Buat Laporan** | Memasukkan sumber, menulis judul, memilih format, generate laporan | Tempat utama pembuatan laporan terjadi di sini |
| **Review Hasil** | Membaca dan memperbaiki laporan per kalimat | Memastikan setiap kalimat memiliki kutipan yang benar dari sumber |

### 3.2 Alur Data (Dari Masuk sampai Keluar)

```
INPUT
-----
[File PDF] [Tautan Web] [Teks Manual]
      \        |           /
       \       |          /
        \      |         /
         \     |        /
          \    |       /
           \   |      /
            \  |     /
             \ |    /
              v   v   v
    [Membaca & Mengekstrak Teks]
             |
             v
    [Memecah teks menjadi bagian-bagian kecil]
             |
             v
    [Meminta AI untuk menulis laporan]
             |
             v
    [Memeriksa apakah kutipan cocok dengan sumber]
             |
             v
    [Pengguna membaca dan memperbaiki per kalimat]
             |
         +---+---+
         |       |
        Ya     (lanjut)
         |       |
         v       v
    [File DOCX hasil ekspor] <--+
             |                  |
             v                  |
    [Draf otomatis disimpan di  +
     data\drafts\]              +
                                +
                               (kembali ke review jika ada perbaikan)
```

### 3.3 Status Kalimat (Di Tab Review Hasil)

Setiap kalimat dalam laporan selalu punya salah satu dari tiga status ini:

| Status | Warna | Artinya | Apa yang Harus Dilakukan? |
|--------|-------|---------|---------------------------|
| **Terverifikasi** | Hijau | Kutipan kalimat ditemukan di teks sumber | Tidak perlu apa-apa, sudah benar |
| **Belum terverifikasi** | Merah | Kutipan tidak ditemukan, atau kalimat baru diedit | Perbaiki kalimat atau kembalikan sitasi, lalu tandai selesai |
| **Bukan klaim faktual** | Abu-abu | Kalimat berupa opini atau pengantar | Boleh dilewati / tandai selesai |

**Aturan penting:** Tidak bisa menyimpan DOCX (ekspor) selama masih ada kalimat berstatus merah (belum ditandai selesai).

---

## 4. ALUR TEKNIS BALIK BELAKANG (Backend Flow)

Ini adalah alur apa yang terjadi di dalam komputer saat pengguna menekkan **Generate**:

```
Pengguna klik Generate
        |
        v
Format Spec menentukan struktur bab A/B/C
        |
        v
Prompt dikirim ke layanan AI
        |
        v
AI menghasilkan isi laporan
        |
        v
Normalisasi nomor bab dan subbab
        |
        v
Verifikasi sitasi terhadap teks sumber
        |
        v
Tampilkan di Tab Review Hasil
        |
        v
Pengguna review per kalimat
        |
        v
Klik Simpan DOCX
        |
        v
Renderer mengisi template .docx
        |
        v
File DOCX disimpan di folder output\

---

## 5. FOLDER DAN FILE PENTING

| Folder/File | Isi | Keterangan |
|-------------|-----|------------|
| `data\` | Database SQLite, config.json, logo, template, draf, log | Semua data pengguna disimpan di sini |
| `data\config.json` | Pengaturan AI | Berisi API key (jangan dibagikan!) |
| `data\drafts\` | Draf otomatis | Disimpan otomatis dan dapat dikelola via tombol Kelola Draf & Proyek |
| `output\` | Hasil file DOCX | Hasil akhir laporan siap dicetak |
| `run.bat` | Skrip peluncur | Membuat virtual environment dan membuka aplikasi |
| `requirements.txt` | Daftar paket Python yang dibutuhkan | pywebview, python-docx, pypdfium2, rapidocr, dll. |

---

## 6. CATATAN PENTING PENGGUNA

1. **API Key** disimpan dalam bentuk teks biasa di `data\config.json`. Jangan membagikan file ini kepada orang lain.
2. **Teks sumber dikirim ke layanan AI**. Jika menggunakan AI online (bukan lokal), jangan masukkan dokumen rahasia.
3. **PDF hasil pindaian** butuh OCR, yang memerlukan internet saat pertama kali untuk mengunduh model OCR.
4. **Ekspor diblokir** kalau masih ada kalimat merah (belum diverifikasi). Harus ditandai selesai terlebih dahulu.
5. **Daftar isi di Word** perlu diklik kanan → **Update Field** setelah dibuka untuk menampilkan nomor halaman.

---

## 7. RINGKASAN UNTUK PEMULA

1. Buka `run.bat` → Tunggu aplikasi terbuka
2. Atur AI di tab **Pengaturan** → Tes Koneksi → Simpan
3. Isi data diri di tab **Data** → Unggah logo
4. Unggah template .docx di tab **Template**
5. Di tab **Buat Laporan**: masukkan sumber, tulis judul, pilih format, klik **Generate**
6. Di tab **Review Hasil**: baca per kalimat, perbaiki jika perlu, tandai selesai
7. Klik **Simpan DOCX** → Hasil ada di folder `output\`

Selesai! Laporan akademik Anda siap digunakan.