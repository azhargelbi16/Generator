# Generator Laporan

Aplikasi desktop untuk menyusun laporan akademik berbahasa Indonesia dari sumber PDF dan web, lengkap dengan sitasi APA edisi ke-7 dan keluaran DOCX yang rapi. Ditujukan untuk pemula: semua langkah dilakukan lewat jendela aplikasi, tanpa terminal.

## Instalasi

1. Pastikan Python 3.11 atau 3.12 terpasang di komputer Anda.
2. Jalankan aplikasi:
   - **Windows**: Klik dua kali `run.bat`.
   Skrip otomatis membuat virtual environment `.venv` saat pertama kali dijalankan, memasang semua paket dari `requirements.txt`, lalu membuka jendela aplikasi desktop modern (antarmuka telah dikompilasi siap pakai di `frontend/dist/`).
3. Cara manual bila diperlukan:

```
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m generator.web.app
```

## Mengatur layanan AI (tab Pengaturan)

Buka tab **Pengaturan** lalu isi:

| Isian | Arti |
| --- | --- |
| Base URL | Endpoint API yang kompatibel OpenAI, mis. `http://localhost:1234/v1` |
| API Key | Kunci layanan AI Anda |
| Model | Nama model, mis. nama model lokal di LM Studio |
| Temperatur | Angka 0 sampai 2; boleh diketik dengan koma, mis. `0,3` |

Tekan **Tes Koneksi** untuk memastikan layanan merespons, lalu **Simpan**.

Catatan keamanan dan privasi:

- **Keamanan & Enkripsi Kunci API**: Kunci API dan konfigurasi sensitif disimpan terenkripsi secara otomatis menggunakan **Windows DPAPI (CryptProtectData)** pada Windows (dan isolasi kunci mesin berizin ketat `chmod 0o600` pada Linux/macOS). Berkas diabaikan dari git dan teks kunci API tidak pernah ditulis ke berkas log.
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
- Text box dan shape **tidak didukung**; letakkan penanda di paragraf biasa, termasuk di header atau footer. Penanda di dalam tautan (hyperlink) atau tabel bersarang ditemukan saat validasi tetapi tidak diganti, jadi letakkan juga di paragraf atau tabel biasa.
- Template tanpa style Heading tetap menghasilkan DOCX; judul bab memakai format tebal sebagai gantinya.
- `{{DAFTAR_ISI}}` menjadi field TOC Word. Setelah dokumen terbuka di Word, klik kanan di daftar isi lalu pilih **Update Field** untuk mengisi nomor halaman.

## Format baku isi laporan

Pemetaan penanda di atas mengikuti spesifikasi format laporan fakultas. Bagian yang digenerate AI hanya isi di dalam `{{ISI_LAPORAN}}` (Bab 1 sampai Bab 4); margin, font, sampul, dan daftar isi tetap diatur berkas `.docx`.

Baris identitas pada sampul selalu dicetak kapital dari profil: `PROGRAM STUDI AGROTEKNOLOGI`, `FAKULTAS PERTANIAN`, `UNIVERSITAS JEMBER`, lalu `2026`. Isinya diambil dari tab Data (program studi, fakultas, institusi) dan tahun ekspor, jadi ubah profil bila identitas kampus berbeda.

Saat ekspor, aplikasi menambahkan **nomor halaman bawah-tengah** secara otomatis bila footer template masih kosong. Halaman sampul tidak diberi nomor dan halaman isi pertama dihitung sebagai halaman 1 (`titlePg` + nomor mulai 0). Bila footer template sudah berisi teks atau field `PAGE`, footer itu dibiarkan apa adanya — jadi template yang mengatur penomoran sendiri tetap menang.

Pilih **Format laporan** di halaman Buat Laporan:

| Varian | Dipakai untuk | Bab 2 | Bab 3 | Bab 4 | Rumusan Masalah |
| --- | --- | --- | --- | --- | --- |
| A | Responsi/tinjauan, beberapa objek bahasan | Tinjauan Pustaka | HASIL DAN PEMBAHASAN | PENUTUP | Ada |
| B | Laporan ringkas, satu objek bahasan | Tinjauan Pustaka | HASIL DAN PEMBAHASAN | KESIMPULAN DAN SARAN | Ada |
| C | Laporan praktikum | Metodologi | HASIL DAN PEMBAHASAN | PENUTUP | Tidak ada |
| D | **Tinjauan pustaka / sintesis literatur** (tanpa penelitian lapangan, **default**) | Tinjauan Pustaka (3–5 subbab) | **PEMBAHASAN** (mengikuti rumusan masalah) | KESIMPULAN DAN SARAN | Ada |
| Bebas | Outline manual seperti versi lama | Bebas | Bebas | Bebas | Bebas |

Varian D tidak punya bab "Hasil": seluruh temuan dari sumber dibahas sebagai sintesis pada `BAB 3. PEMBAHASAN`. Aturannya:

- **BAB 2 TINJAUAN PUSTAKA: 3–5 subbab saja** (bisa 3, 4, atau 5 sesuai kebutuhan), setiap subbab satu topik utuh dengan 2–3 paragraf dan tanpa sub-subbab. Kelebihan topik yang dihasilkan AI digabungkan ke subbab terakhir, bukan menjadi judul baru.
- **BAB 3 PEMBAHASAN mengikuti alur Rumusan Masalah → Tujuan → Pembahasan**: jumlah subbab sama dengan jumlah butir Rumusan Masalah, urutannya sama, dan setiap subbab menjawab satu rumusan masalah sekaligus menunjukkan tercapainya satu tujuan. Aplikasi mengirimkan rumusan masalah dan tujuan Bab 1 sebagai konteks ke bab berikutnya agar alurnya nyambung.
- Judul subbab yang masih berupa nama template (`{Topik 1}`, `{Jawaban rumusan masalah 2}`, dan sejenisnya) tidak pernah dicetak mentah: judulnya diganti judul nyata dari isi, atau untuk Bab Pembahasan diambil dari butir Rumusan Masalah yang sejajar.

Saat varian dipilih, aplikasi melakukan tiga hal:

1. Struktur varian dan aturan penulisan baku dikirim ke prompt sebagai instruksi wajib (bukan saran).
2. Judul dinamis `{Subjek}`, `{Objek}`, `{Aspek}` diisi AI, sedangkan nomor dan judul tetap (`BAB 1. PENDAHULUAN`, `1.1 Latar Belakang`, dan seterusnya) ditetapkan aplikasi.
3. Keluaran AI dinormalisasi sebelum ditampilkan: urutan bab dikembalikan sesuai varian, penomoran `BAB n.`/`n.n`/`n.n.n` dihitung ulang, bagian tetap yang kosong tetap muncul sebagai judul untuk diisi, dan bagian opsional tanpa isi dihapus. Isi tambahan dari AI tidak dibuang; ia menjadi subbab tambahan bernomor di akhir babnya.

Aturan tambahan: setiap subbab **naratif** ditulis dalam 2–3 paragraf; tiap paragraf 3–5 kalimat, satu paragraf tidak pernah memuat lebih dari 5 kalimat (kelebihan dipecah otomatis) dan satu subbab tidak lebih dari 6 paragraf. Subbab daftar bernomor (rumusan masalah, tujuan, kesimpulan, saran, alat/bahan, langkah kerja) tetap satu butir satu kalimat dan dirender **satu butir satu paragraf**. Untuk varian B/D, **BAB terakhir (Kesimpulan dan Saran) hanya berisi butir bernomor di 4.1 dan 4.2** — paragraf prosa di bawah heading BAB dibuang, dan butir yang menempel di level BAB dipindahkan ke subbab yang sesuai. Varian B dan D (makalah/tinjauan tanpa data lapangan) **tidak meminta tabel**: temuannya ditulis sebagai narasi, dan kalimat yang hanya mendeskripsikan keberadaan tabel dibuang otomatis. Varian A/C masih boleh memakai penanda `[TABEL: ...]`, `[GAMBAR: ...]`, atau `[FOTO: ...]` untuk Anda isi **sebelum ekspor** (ekspor ditolak selama penanda itu masih ada). Kesimpulan harus sejajar dengan tujuan, dan setiap klaim faktual tetap harus bersitasi dari sumber.

## Alur pemakaian

1. **Data**: isi profil (nama, NIM, program studi), unggah logo, tambah dosen dan mata kuliah. Semuanya tersimpan di basis data lokal.
2. **Template**: unggah template yang lolos validasi.
3. **Buat Laporan**:
   - Masukkan sumber: PDF naskah lengkap (dibaca langsung, atau OCR bila hasil pindaian, dilengkapi deteksi DOI otomatis untuk metadata APA 7) atau teks naskah manual. Metadata boleh dikoreksi lewat formulir; aplikasi tidak pernah menebak pemisahan nama penulis.
   - Kelola banyak laporan secara simultan lewat tombol **Kelola Draf & Proyek**: simpan snapshot proyek, buka kembali laporan lama, atau mulai draf baru.
   - Tulis judul, lalu pilih **Format laporan** (A, B, C, atau Bebas). Format baku mengisi outline dengan struktur varian dan mengunci editornya; pilih **Bebas** bila ingin menyusun outline sendiri, lalu klik **Usulkan outline** dan sunting bila perlu.
   - Klik **Generate**. Setiap kalimat hasil AI membawa kutipan dari sumber dan diperiksa ulang secara lokal.
   - Di tab **Review Hasil** dokumen tampil di **Canvas Review Studio** bersih seperti di Microsoft Word: dilengkapi kontrol Zoom (75%–150%), Fit-Width, Mode Baca bebas gangguan, serta sidebar navigasi Struktur Bab untuk melompat langsung antar bab. Huruf Times New Roman 12 poin, judul laporan dan judul bab lebih besar dan tebal, sitasi tertulis langsung di kalimatnya, mis. (Santoso, 2020).
   - Klik satu kalimat: kalimat itu disorot lembut dan panel inspektur sisi kanan menampilkan kutipan bukti asli dari teks sumber serta tombol **Parafrase AI**, **Tandai selesai**, dan **Pulihkan sitasi**.
   - Untuk memperbaiki kalimat, klik kalimatnya lalu ketik langsung di tempatnya; bagian lain dokumen terkunci. Pindah klik ke kalimat lain atau ke area kosong untuk menyimpan perbaikan secara otomatis.
   - Penghitung di atas dokumen menunjukkan berapa kalimat yang sudah selesai diverifikasi.
   - Klik **Simpan DOCX**. Hasil tersimpan di folder `output\` dengan nama dari judul laporan dan otomatis dibuka di Microsoft Word. Draf pekerjaan Anda tetap tersimpan dengan aman sehingga dapat dibuka dan direvisi kembali kapan saja.

## Status kalimat dan gerbang ekspor

Setiap kalimat selalu punya salah satu dari tiga status. Warna status hanya muncul pada kalimat yang sedang Anda klik, di baris kecil di bawahnya; badan dokumen tetap bersih tanpa warna.

| Status | Arti |
| --- | --- |
| Kutipan cocok (hijau) | Kutipan kalimat ditemukan di teks sumber. Ini bukan jaminan klaim benar — tetap baca sumbernya. |
| Kutipan tidak cocok (merah) | Kutipan tidak ditemukan, atau kalimat baru Anda sunting |
| Bukan klaim faktual (abu) | AI menandai kalimat sebagai opini atau kalimat pengantar |

Kutipan yang persis ditemukan pada sumber **berbahasa asing** (mis. jurnal berbahasa Inggris) tetap berstatus hijau walau kalimat laporannya berbahasa Indonesia: aplikasi mendeteksi perbedaan bahasa dan menandai alasan "terjemahan bebas — periksa artinya". Kutipan yang tidak ada di sumber tetap merah, dan salinan verbatim tetap ditandai perlu parafrase.

Gerbang ekspor (jendela Pemeriksaan Akhir) juga menandai: kalimat faktual yang tidak membawa sitasi sama sekali, daftar pustaka yang akan kosong, dan bagian bab yang masih kosong ("Kosong" di sidebar Struktur Bab). Kalimat yang belum ditandai selesai tetap tidak memblokir ekspor: gerbang menampilkan peringatan, dan bila Anda tetap ingin menyimpan, muncul konfirmasi eksplisit yang kejadiannya dicatat di berkas log.

Namun ada **penolakan keras di backend** (tidak bisa dilewati dari dialog) untuk dokumen yang belum layak dikumpulkan, dengan pesan yang menyebutkan alasannya:

- laporan tanpa isi sama sekali;
- bab wajib yang masih kosong;
- paragraf yang masih memuat penanda `[TABEL: ...]`, `[GAMBAR: ...]`, atau `[FOTO: ...]` yang belum diganti isi nyata;
- daftar pustaka kosong padahal ada klaim faktual.

Perbaiki dokumen (isi bagian kosong, ganti/buang penanda, lengkapi sitasi) lalu ekspor lagi. Dokumen dengan penanda `{{...}}` yang tersisa juga tetap ditolak otomatis.

Draf aktif tersimpan otomatis lengkap dengan judul, sumber, dan catatan review Anda, sehingga aman menutup lalu membuka aplikasi kembali. "Mulai Lembar Kerja Kosong Baru" mengarsipkan draf lama yang masih berisi (berawalan `arsip_`) alih-alih memusnahkannya.

Bila satu kalimat memakai beberapa sumber, sitasinya digabung dalam satu tanda kurung dipisah titik koma dan diurutkan alfabetis sesuai APA 7, mis. `(Abadi, 2021; Zed, 2020)`. Daftar pustaka hanya memuat sumber yang benar-benar dikutip, memakai format APA 7 lengkap: nama jurnal dan volume dimiringkan, nomor dan halaman mengikuti, mis. *Healthcare, 9*(10), 1272. Data volume/nomor/halaman diambil otomatis dari CrossRef saat DOI diselesaikan; sumber lama tanpa data itu tetap diekspor dengan bentuk sebelumnya.

## Catatan OCR

PDF hasil pindaian diproses OCR: halaman dirender dengan pypdfium2 lalu dikenali rapidocr. Kualitas OCR bisa kurang akurat sehingga lebih banyak kalimat ditandai tidak terverifikasi; selalu periksa hasilnya. Model OCR diunduh saat pertama kali menjalankan OCR sehingga butuh internet. Unduhannya dicache di dalam `.venv` (folder `site-packages`), bukan di folder `data\`, sehingga menghapus folder `data\` tidak mengulang unduhan model.

## Desain & responsivitas

- Sistem desain resmi: `design/DESIGN_SYSTEM.md` (token warna, tipografi, komponen, breakpoint). Papan desain siap-impor Figma: seret `design/figma/Generator_Laporan_Design_Board.svg` ke kanvas Figma Desktop.
- Antarmuka diuji pada 100%–200% zoom dan ukuran jendela minimum (960×640). Saat jendela sempit: rail Struktur Bab disembunyikan (≤1180px), inspektur kalimat turun menjadi panel bawah (≤1020px), dan dialog selalu punya scroll internal.
- Semua dialog dapat ditutup dengan tombol Escape; label form terikat kolom isinya untuk pembaca layar.

## Catatan teknis

- Antarmuka ditulis dengan Desktop Webview modern (React 19 + TypeScript + Tailwind CSS via pywebview). GUI Tkinter dan Qt lama resmi dipensiunkan; aplikasi berjalan mulus dan responsif di atas Microsoft Edge WebView2 bawaan Windows.

- Operasi lama (OCR, panggilan AI, ambil web, render DOCX) berjalan di latar sehingga jendela tetap responsif.
- Penulisan isi berjalan **per kelompok maksimal 2 subbab** (bukan satu panggilan per bab): jawaban satu bab yang padat bisa melebihi batas panjang keluaran penyedia AI sehingga JSON terpotong. Bila jawaban tetap tidak memuat subbab (mis. isi ditaruh di section "BAB") atau JSON tidak terbaca, langkah itu **diulang sekali** dengan instruksi struktur eksplisit; bila masih gagal, isi level bab disebar otomatis ke subbab. Setelah semua bab selesai, aplikasi menjalankan **pelengkap deterministik**: subbab tipis/kosong diminta sekali lagi ke AI (maksimal 3 percobaan), subbab level-2 penting yang hilang dipulihkan dengan memindahkan isi, sub-subbab 1 paragraf dilipat ke induknya, dan Kesimpulan/Saran yang tetap kosong diisi ringkasan/rekomendasi umum. Judul section selalu dihitung ulang aplikasi (≤10 kata, bukan kalimat).
- Sumber panjang diproses per batch lalu digabung dan dideduplikasi; verifikasi kutipan tetap memakai teks lengkap. Pada PDF sangat panjang kualitas isi bisa menurun karena tiap batch menulis bab yang sama dari potongan berbeda.
- Aplikasi memutuskan `is_factual` berdasarkan jawaban AI, sehingga Anda tetap penjaga terakhir: kalimat faktual yang salah tercatat bukan-klaim bisa lolos bila Anda menandai selesai tanpa membacanya.
- Batasan sitasi organisasi: bentuk panjang `Nama Penuh [Singkatan]` dipakai pada kemunculan pertama, lalu bentuk singkat pada kemunculan berikutnya di DOCX. Halaman Review tetap menampilkan bentuk panjang agar mudah diperiksa.
- Draf tersimpan otomatis di `data\drafts\` sehingga pekerjaan tidak hilang saat aplikasi ditutup. Berkas draf memuat teks sumber utuh dalam JSON polos (tidak dienkripsi) dan baru dihapus setelah ekspor sukses; hapus manual bila laporan batal diekspor.
- Teks dari web dan PDF diperlakukan sebagai data, bukan instruksi. Aplikasi hanya meminta kutipan dan metadata, tetapi prompt injection dari halaman/sumber tetap mungkin; periksa hasil sebelum diekspor.

## Struktur folder

| Folder | Isi |
| --- | --- |
| `data\` | Basis data SQLite, `config.json`, logo, template, draf, dan berkas log `app.log` |
| `output\` | Dokumen DOCX hasil ekspor |

## Troubleshooting

| Gejala | Penanganan |
| --- | --- |
| Tes Koneksi gagal | Pastikan layanan AI hidup dan Base URL benar sampai `/v1` |
| Generate menampilkan pesan layanan AI | Periksa nama model dan API key; bagian non-AI tetap bisa dipakai |
| Template ditolak saat dipilih | Buka pesan peringatan: lengkapi penanda wajib atau pisahkan penanda khusus dari teks lain |
| Daftar isi kosong di Word | Klik kanan daftar isi, pilih Update Field |
| Logo tidak muncul | Pilih logo di tab Data sebelum mengekspor; logo yang rusak dilewati dan dicatat di log |
| Kalimat banyak yang merah setelah PDF pindaian | Kualitas OCR rendah; coba teks manual atau PDF dengan lapisan teks |
| Lupa menandai selesai | Kotak kalimat merah menandai yang belum; gunakan tombol tandai massal untuk kalimat bukan-klaim |
