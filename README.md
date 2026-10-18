# Generator Laporan

Aplikasi desktop untuk menyusun laporan akademik berbahasa Indonesia dari sumber PDF dan web, lengkap dengan sitasi APA edisi ke-7 dan keluaran DOCX yang rapi. Ditujukan untuk pemula: semua langkah dilakukan lewat jendela aplikasi, tanpa terminal.

## Instalasi

1. Pastikan Python 3.12 terpasang di Windows.
2. Klik dua kali `run.bat`. Skrip ini membuat virtual environment `.venv` saat pertama kali dijalankan, memasang semua paket dari `requirements.txt`, lalu membuka jendela aplikasi.
3. Cara manual bila diperlukan:

```
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m generator.gui.app
```

## Mengatur layanan AI (tab Pengaturan)

Buka tab **Pengaturan** lalu isi:

| Isian | Arti |
| --- | --- |
| Base URL | Endpoint API yang kompatibel OpenAI, mis. `http://localhost:1234/v1` |
| API Key | Kunci layanan AI Anda |
| Model | Nama model, mis. nama model lokal di LM Studio |
| Temperatur | Angka 0 sampai 1; boleh diketik dengan koma, mis. `0,3` |

Tekan **Tes Koneksi** untuk memastikan layanan merespons, lalu **Simpan**.

Catatan keamanan dan privasi:

- API key disimpan apa adanya di `data/config.json`. Berkas itu diabaikan git dan isinya tidak pernah ditulis ke berkas log.
- **Teks sumber yang Anda masukkan dikirim ke layanan AI** sebagai bahan penulisan dan verifikasi kutipan. Jangan memasukkan dokumen yang tidak boleh meninggalkan komputer kecuali layanan AI yang Anda pakai berjalan lokal.

## Panduan format template

Template adalah berkas `.docx` biasa yang berisi penanda `{{...}}`. Unggah lewat tab **Template**. Aplikasi memvalidasinya setiap kali dipilih.

Penanda wajib (harus ada semua):

| Penanda | Diisi dengan |
| --- | --- |
| `{{JUDUL}}` | Judul laporan |
| `{{NAMA}}` | Nama mahasiswa dari tab Data |
| `{{NIM}}` | NIM dari tab Data |
| `{{MATA_KULIAH}}` | Mata kuliah yang dipilih |
| `{{DOSEN}}` | Dosen yang dipilih |
| `{{TANGGAL}}` | Tanggal ekspor, mis. 19 Oktober 2026 |
| `{{ISI_LAPORAN}}` | Seluruh bab isi laporan (penanda khusus) |
| `{{DAFTAR_PUSTAKA}}` | Daftar pustaka APA 7 (penanda khusus) |
| `{{DAFTAR_ISI}}` | Field daftar isi Word (penanda khusus) |
| `{{LOGO}}` | Logo 5x5 cm yang dipilih (penanda khusus) |

Penanda opsional: `{{TAHUN}}` dan `{{PRODI}}`. Bila nilainya kosong, penandanya dikosongkan sehingga tidak pernah tercetak mentah.

Aturan penting:

- **Penanda khusus** (`{{ISI_LAPORAN}}`, `{{DAFTAR_PUSTAKA}}`, `{{DAFTAR_ISI}}`, `{{LOGO}}`) harus berdiri sendiri di satu paragraf. Bercampur dengan teks lain (mis. `Bab: {{ISI_LAPORAN}}`) ditolak.
- Penanda yang hilang atau tidak berdiri sendiri: template **boleh disimpan** tetapi **tidak bisa dipakai** sampai diperbaiki.
- Penanda tak dikenal (bukan daftar di atas) tetap dipakai tetapi Anda akan diminta konfirmasi saat menyimpan DOCX.
- Text box dan shape **tidak didukung**; letakkan penanda di paragraf biasa, termasuk di header atau footer.
- Template tanpa style Heading tetap menghasilkan DOCX; judul bab memakai format tebal sebagai gantinya.
- `{{DAFTAR_ISI}}` menjadi field TOC Word. Setelah dokumen terbuka di Word, klik kanan di daftar isi lalu pilih **Update Field** untuk mengisi nomor halaman.

## Alur pemakaian

1. **Data**: isi profil (nama, NIM, program studi), unggah logo, tambah dosen dan mata kuliah. Semuanya tersimpan di basis data lokal.
2. **Template**: unggah template yang lolos validasi.
3. **Buat Laporan**:
   - Masukkan sumber: PDF (dibaca langsung, atau OCR bila hasil pindaian), tautan web, atau teks manual. Metadata boleh dikoreksi lewat formulir; aplikasi tidak pernah menebak pemisahan nama penulis.
   - Tulis judul, klik **Usulkan outline**, sunting bila perlu.
   - Klik **Generate**. Setiap kalimat hasil AI membawa kutipan dari sumber dan diperiksa ulang secara lokal.
   - Periksa tiap kalimat: sunting langsung di kotaknya, **Tandai selesai** kalimat yang sudah Anda setujui, atau **Parafrase**.
   - Klik **Simpan DOCX**. Hasil tersimpan di folder `output\` dengan nama dari judul laporan. Draf otomatis terhapus setelah ekspor sukses.

## Status kalimat dan gerbang ekspor

Setiap kalimat selalu punya salah satu dari tiga status:

| Status | Arti |
| --- | --- |
| Terverifikasi (hijau) | Kutipan kalimat ditemukan di teks sumber |
| Belum terverifikasi (oranye) | Kutipan tidak ditemukan, atau kalimat baru Anda sunting |
| Bukan klaim faktual (abu) | AI menandai kalimat sebagai opini atau kalimat pengantar |

Ekspor diblokir selama masih ada kalimat yang belum ditandai selesai. Bila Anda tetap ingin menyimpan, muncul konfirmasi eksplisit dan kejadian itu dicatat di berkas log.

Bila satu kalimat memakai beberapa sumber, sitasinya digabung dalam satu tanda kurung dipisah titik koma sesuai APA 7, mis. `(Zed, 2020; Abadi, 2021)`. Daftar pustaka hanya memuat sumber yang benar-benar dikutip.

## Catatan OCR

PDF hasil pindaian diproses OCR: halaman dirender dengan pypdfium2 lalu dikenali rapidocr. Kualitas OCR bisa kurang akurat sehingga lebih banyak kalimat ditandai tidak terverifikasi; selalu periksa hasilnya. Model OCR diunduh saat pertama kali menjalankan OCR sehingga butuh internet, dan cache model disimpan di folder `data\`.

## Catatan teknis

- Operasi lama (OCR, panggilan AI, ambil web, render DOCX) berjalan di latar sehingga jendela tetap responsif.
- Sumber panjang diproses per batch lalu digabung dan dideduplikasi; verifikasi kutipan tetap memakai teks lengkap. Pada PDF sangat panjang kualitas isi bisa menurun karena tiap batch menulis bab yang sama dari potongan berbeda.
- Aplikasi memutuskan `is_factual` berdasarkan jawaban AI, sehingga Anda tetap penjaga terakhir: kalimat faktual yang salah tercatat bukan-klaim bisa lolos bila Anda menandai selesai tanpa membacanya.
- Batasan sitasi organisasi: versi ini menampilkan `Nama Penuh [Singkatan]` di semua kemunculan, belum beralih ke singkatan saja setelah sitasi pertama.
- Draf tersimpan otomatis di `data\drafts\` sehingga pekerjaan tidak hilang saat aplikasi ditutup.

## Struktur folder

| Folder | Isi |
| --- | --- |
| `data\` | Basis data SQLite, `config.json`, logo, template, draf, cache OCR |
| `output\` | Dokumen DOCX hasil ekspor |
| `logs\` | Berkas log aplikasi |

## Troubleshooting

| Gejala | Penanganan |
| --- | --- |
| Tes Koneksi gagal | Pastikan layanan AI hidup dan Base URL benar sampai `/v1` |
| Generate menampilkan pesan layanan AI | Periksa nama model dan API key; bagian non-AI tetap bisa dipakai |
| Template ditolak saat dipilih | Buka pesan peringatan: lengkapi penanda wajib atau pisahkan penanda khusus dari teks lain |
| Daftar isi kosong di Word | Klik kanan daftar isi, pilih Update Field |
| Logo tidak muncul | Pilih logo di tab Data sebelum mengekspor; logo yang rusak dilewati dan dicatat di log |
| Kalimat banyak yang oranye setelah PDF pindaian | Kualitas OCR rendah; coba teks manual atau PDF dengan lapisan teks |
| Lupa menandai selesai | Kotak kalimat oranye menandai yang belum; gunakan tombol tandai massal untuk kalimat bukan-klaim |
