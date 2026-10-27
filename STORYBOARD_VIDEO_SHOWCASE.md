# Storyboard — Video Showcase "Generator Laporan" (3 Menit)

Spesifikasi siap-eksekusi untuk dibangun dengan **React + Remotion** oleh agent/LLM lain.
Semua teks layar sudah final (bahasa Indonesia), semua warna memakai token resmi
`design/DESIGN_SYSTEM.md` v2.1, semua label UI diambil dari kode asli aplikasi
(`frontend/src/components/TabReview.tsx`, `Sidebar.tsx`) — bukan karangan.

## 0. Parameter global (WAJIB)

| Parameter | Nilai |
|---|---|
| Durasi | 180 detik = 5400 frame |
| FPS | 30 |
| Resolusi | 1920×1080 (16:9) |
| Format keluaran | MP4 (H.264), tanpa audio (default) |
| Bahasa | Indonesia |
| Komposisi Remotion | id `Showcase`, `durationInFrames: 5400` |
| Gaya visual | Editorial akademik: kertas krem `#FFF8DE`, tinta navy `#101827`, aksen perwangan `#8CA9FF`, serif Georgia untuk identitas, Times New Roman untuk dokumen |
| Sumber data di layar | SEMUA dummy (lihat §7). Jangan pakai data asli aplikasi. |

## 1. Token warna & tipografi (salin mentah)

```
canvas #FFF8DE | paper #FFFFFF | sidebar-bg #101827 | sidebar-line #263957
sidebar-text #CBD7EE | sidebar-muted #8EA3C7 | surface-muted #FFF2C6
ink #101827 | ink-soft #2F405D | ink-muted #60708A
line #C6D4EC | line-strong #AAC4F5 | accent #8CA9FF | accent-dark #3D5DAF
accent-pale #DCE6FF | warning #6E5A24 | warning-pale #FFF2C6
danger #7A404A | danger-pale #F4DCE0 | danger-line #D7A8B3
hijau status (dari TabReview.tsx asli): bg #D8F3E3 · teks #0E5A34 · border #9BD8B4 · dot #18A05C
bar "perlu ditinjau" #D7C28D
```

Font: **Inter** (UI, via `@remotion/google-fonts/Inter`, weights 400/500/600/700/800),
**JetBrains Mono** (overline/mono, weights 500/800), **Georgia** + **Times New Roman**
(font sistem, tidak perlu diunduh). Kertas dokumen selalu Times New Roman, line-height 2.0, justify.

## 2. Prinsip motion (konsisten di semua scene)

- Ease gerak kursor & slide: `Easing.inOut(Easing.cubic)` antar waypoint.
- Panel masuk: `spring({damping: 200, stiffness: 80–120})`; pil status "pop": `spring({damping: 12–14, stiffness: 200})` mulai scale 0.6.
- Bayangan khas cetak: panel `5px 5px 0 rgba(23,23,23,.1)`, kertas `0 12px 30px rgba(32,37,31,.11)`.
- Radius kecil: kartu 8px, tombol 5px, kontrol 3px, pil 999px.
- Klik selalu: kursor panah hitam SVG (stroke putih) + ripple ring `#3D5DAF` (scale 0.3→3.3, fade 14 frame).
- Setiap scene diawali fade/rise 10–12 frame dan diakhiri transisi 10 frame ke scene berikut (kecuali disebut lain).
- Referensi implementasi hidup: klip 8 detik yang sudah terbukti render di mesin ini — komposisi `Klip` di `C:\Users\ACER\AppData\Local\Temp\gl-clip\src\Klip.tsx` (folder temp; salin bila masih ada. Semua pola di storyboard ini identik dengan yang ada di file itu).

## 3. Breakdown scene

### S1 · Hook masalah (frame 0–360 · 0:00–0:12)
- **Tujuan**: sakit kepala penonton: laporan butuh sitasi, klaim tanpa bukti, cek manual lambat.
- **Visual**: latar `canvas`. Tiga "kartu kalimat" Times New Roman muncul berurutan (stagger 20 frame), lalu stempel merah miring "KLAIM TANPA BUKTI?" menempel di salah satunya; sitasi `(?, ????)` berkedip abu.
- **Teks layar** (final):
  - Overline mono: `LAPORAN AKADEMIK, TANPA DRAMA`
  - Kartu 1: `"Konsumsi media daring meningkat 40% (?, ????)."`
  - Kartu 2: `"Metode kuliah luring lebih efektif (?, ????)."`
  - Kartu 3: `"Motivasi belajar menurun drastis (?, ????)."`
- **Transisi keluar**: kartu-kartu terdorong keluar ke kiri; masuk S2.

### S2 · Intro produk (360–750 · 0:12–0:25)
- **Visual**: sama dengan intro klip 8 detik (sudah terbukti): overline `MEJA KERJA AKADEMIK` diapit hairline `#AAC4F5`; judul Georgia 104px `Generator Laporan` (tracking −0.055em, warna `ink`); tagline Inter 28px `Setiap kalimat punya buktinya.`
- **Tambahan**: di bawah tagline, satu baris meta mono 12px muncul di frame ~560: `laporan akademik bersitasi · dari sumber PDF, web, dan DOI · ekspor DOCX`.

### S3 · Peta alur kerja (750–1110 · 0:25–0:37)
- **Visual**: sidebar gelap `#101827` (lebar 264) slide-in dari kiri; item nav menyala satu per satu (12 frame each) dengan nomor mono + inset bar krem:
  1. `01 Studio laporan — sumber dan kerangka`
  2. `02 Canvas & review — baca per kalimat`
  3. `03 Profil & institusi — identitas akademik`
  4. `04 Template Word — format dan penanda`
  5. `05 Pengaturan AI — endpoint dan model`
- Saat item menyala, di kanan muncul kartu pratinjau mini scene-nya (thumbnail 240×150, isi mengikuti scene S4–S8).
- **Teks**: judul kecil Georgia `Lima langkah, satu meja kerja.`

### S4 · Input sumber (1110–1740 · 0:37–0:58)
- **Visual**: mock tab Studio laporan. Empat kartu sumber masuk stagger, masing-masing dengan ikon garis + chip status:
  1. `PDF — jurnal_2020.pdf` · chip `128 halaman · teks terbaca`
  2. `DOI — 10.xxxx/xxxxx` · chip `CrossRef · metadata lengkap` (animasi: teks DOI → resolusi → kartu terisi tahun/jurnal otomatis)
  3. `Web — tautan artikel` · chip `teks diambil`
  4. `Teks manual — tempel kutipan` · chip `4.120 karakter`
- Kartu ke-5 (PDF pindaian) muncul lalu chip berubah `OCR berjalan…` → `selesai (kualitas rendah — periksa)`.
- **Teks**: overline `SUMBER DULU, BUKAN KEMUDIAN`; caption bawah: `Aplikasi tidak pernah menebak pemisahan nama penulis — metadata bisa dikoreksi manual.`

### S5 · Generate (1740–2280 · 0:58–1:16)
- **Visual**: panel "Studio laporan": pilih `Format laporan` — empat chip varian `A · B · C · D` (D aktif, `default`), tombol primer `Generate` ditekan (ripple).
- Progress streaming ala terminal kartu: baris teks muncul bertahap mono 12px:
  `menyusun kerangka D · BAB 2 tinjauan pustaka · BAB 3 pembahasan · verifikasi kutipan lokal…`
  Di sampingnya penghitung kata naik `0 → 1.676 kata`.
- **Teks**: caption `Ditulis per subbab, dicek ulang per kalimat — semuanya lokal di komputer Anda.`

### S6 · HERO — Review per kalimat (2280–3420 · 1:16–1:54) ← inti video
Perpanjangan langsung dari klip 8 detik yang sudah jadi; sub-beat:
1. **2280–2400 (4s)** — Canvas Review Studio: sidebar, command bar (chip `● Tersimpan`, penghitung `3/5 kalimat terverifikasi`, zoom `75%|100%`), kertas A4 Times justify: heading `BAB 2. TINJAUAN PUSTAKA`, subbab `2.1 Pembelajaran Daring dalam Pendidikan Tinggi`, 3 kalimat dummy (§7).
2. **2400–2700 (10s)** — kursor klik kalimat 1 `(Santoso, 2020)`: sorot tint `rgba(140,169,255,.45)` + ring `#3D5DAF`; inspektur kanan slide-in; pil hijau pop `✓ Kutipan Cocok dengan Sumber`; kartu kutipan amber `warning-pale` border `#D7C28D` berisi kutipan asli sumber (italic Times); chip sumber `Santoso (2020) · Jurnal Teknologi Pendidikan, 12(2), 45–58` + baris mono hijau `✓ kutipan ditemukan verbatim · hlm. 61`; tombol `✓ Tandai Selesai` `✦ Parafrase AI` `↺ Pulihkan Sitasi Sumber`; penghitung naik `3/5 → 4/5`.
3. **2700–2940 (8s)** — sunting di tempat: label `SUNTING KALIMAT DI TEMPAT`, textarea amber menyala (kursor teks berkedip), tombol biru `Simpan Perubahan Kalimat` ditekan; kalimat di kertas berubah teksnya (crossfade), statusnya turun ke bar tipis biru + chip `Selesai`.
4. **2940–3240 (10s)** — klik kalimat 2 `(Rahmawati & Pratama, 2021)`: tint `danger-pale`, bar kiri `#7A404A`; inspektur crossfade ke pil merah `✕ Belum Terverifikasi`; kotak alasan `Alasan verifikasi: Kutipan tidak ditemukan di teks sumber.`; area bukti: kotak putus-putus `Tidak ada kutipan langsung yang cocok ditemukan di teks sumber.`
5. **3240–3420 (6s)** — legenda status (dari DESIGN_SYSTEM §4): tiga baris kalimat contoh dengan bar kiri — hijau `terverifikasi`, amber `perlu ditinjau`, merah `kutipan tidak cocok`, plus abu `bukan klaim faktual`; caption: `Warna hanya muncul saat kalimat diklik — dokumen tetap bersih seperti di Word.`

### S7 · Gerbang ekspor + hasil (3420–3960 · 1:54–2:12)
- **Visual A (tolak)**: dialog `Pemeriksaan Akhir` dengan daftar merah: `bab wajib masih kosong · daftar pustaka kosong padahal ada klaim faktual`; tombol `Simpan DOCX` bergetar + dim. Teks mono kecil: `penolakan keras backend — tidak bisa dilewati dari dialog`.
- **Visual B (lolos)**: daftar hijau centang; tombol ditekan; animasi berkas `laporan_tinjauan_pustaka.docx` jatuh ke folder `output\`; halaman Word mock terbuka: sampul kapital `PROGRAM STUDI AGROTEKNOLOGI … 2026`, daftar pustaka APA 7 dengan *nama jurnal dan volume miring* `Healthcare, 9(10), 1272`.
- **Teks**: caption `Yang terkumpul baru bisa diekspor kalau layak dikumpulkan.`

### S8 · Nilai / keunggulan (3960–4500 · 2:12–2:30)
- **Visual**: grid 2×2 kartu (radius 8, bayangan cetak), masuk stagger; tiap kartu: ikon garis sederhana + judul Inter 700 + 1 baris keterangan:
  1. `Verifikasi lokal` — `kutipan dicocokkan di komputer Anda, bukan di awan`
  2. `Kunci terenkripsi` — `API key tersimpan via Windows DPAPI`
  3. `Draf tidak hilang` — `autosave lengkap dengan judul, sumber, catatan review`
  4. `AI lokal bisa` — `jalan dengan LM Studio / endpoint OpenAI-compatible mana pun`

### S9 · Closing + CTA (4500–5400 · 2:30–3:00)
- **Visual**: kembali ke kartu judul S2 (judul + tagline). Tambah:
  - baris pil rekap: `✓ Kutipan Cocok` (hijau) · `✕ Tidak Cocok` (merah) — frame ~4700;
  - CTA tombol primer `accent` → hover `accent-dark`: `Coba Generator Laporan` — frame ~4860, klik ripple dekoratif di 4950;
  - caption mono bawah: `rekonstruksi antarmuka · data contoh`;
  - hold statis 5100–5400 (untuk loop/end-card).

## 4. Komponen yang bisa dipakai ulang dari klip 8 detik

Semua sudah ada di `Klip.tsx` (link §2): sidebar + nav aktif, command bar (Tersimpan/penghitung/zoom), kertas A4 + blok kalimat dengan tint/bar/ring, inspektur lengkap (2 stack hijau/merah), pil status, kursor + ripple, kartu judul intro/outro, caption mono. Scene S4–S5 dan S7–S8 adalah komponen baru tapi memakai pola & token yang sama.

## 5. Lingkungan render di mesin ini (PENTING — sering menggagalkan agent lain)

1. `node` v24 ada di `C:\Program Files\nodejs` tetapi **TIDAK terlihat oleh `cmd.exe`** → semua shim `.cmd` (`npx`, postinstall `install.js`) gagal dengan `'node' is not recognized`.
2. Karena itu:
   - install: `npm install --ignore-scripts --no-audit --no-fund` (binary esbuild/compositor datang via optionalDependencies, aman);
   - render **wajib** dipanggil langsung: `node node_modules/@remotion/cli/remotion-cli.js render src/index.ts Showcase out/showcase.mp4`
   - masih: `node node_modules/@remotion/cli/remotion-cli.js still src/index.ts Showcase out/f####.png --frame=####`
3. Chrome Headless Shell terunduh otomatis saat render pertama (butuh internet sekali).
4. Scaffold minimal: `package.json` (remotion, @remotion/cli, @remotion/google-fonts, react, react-dom, typescript, @types/react), `tsconfig.json`, `remotion.config.ts` (`setVideoImageFormat('jpeg')`, `setOverwriteOutput(true)`, `setCodec('h264')`), `src/index.ts` → `registerRoot`, `src/Root.tsx` → Composition `Showcase`.

## 6. QC & gerbang terima (wajib sebelum render penuh)

1. **Uji pipeline dulu**: render 90 frame pertama (`--frames=0-89`) — harus menghasilkan MP4.
2. **Still per scene** di frame tengah tiap scene (mis. 180, 550, 930, 1400, 2000, 2500, 2800, 3100, 3300, 3700, 4200, 4900). Periksa: tidak ada teks terpotong/overlap, kursor tepat di target klik, pil terbaca, jendela app tidak keluar frame.
3. Teknik verifikasi tepi yang akurat: **crop PNG** area yang dicurigai (mis. via Pillow) lalu periksa crop-nya — inspeksi gambar penuh 1920×1080 sering salah melaporkan "terpotong" pada chip yang menempel tepi.
4. Verifikasi file akhir: durasi `5400/30 = 180.000 s` (parse box `mvhd`), frame count, ukuran wajar (~15–30 MB).

## 7. Data dummy (satu-satunya data yang boleh tampil)

- Kalimat kertas (S6): persis tiga kalimat pada klip 8 detik (Santoso 2020 hijau; Rahmawati & Pratama 2021 merah; kalimat ketiga abu tanpa sitasi).
- Kutipan bukti: `“Keleluasaan mengatur waktu belajar menjadi manfaat yang paling banyak disebut mahasiswa pada kelas daring jika dibandingkan dengan kelas tatap muka.”`
- Sumber: `Santoso (2020) · Jurnal Teknologi Pendidikan, 12(2), 45–58`; `Rahmawati & Pratama (2021)`.
- DOI/PDF di S4 fiktif. **Jangan membaca atau menampilkan isi folder `data/` aplikasi.**

## 8. Opsi pengembangan (nyatakan bila tidak dikerjakan)

- Narasi/voice-over Indonesia (skrip per scene = teks layar di atas, 1–2 kalimat) + subtitle SRT.
- Versi 9:16 (1080×1920, layout satu kolom: kertas di atas, inspektur jadi panel bawah — breakpoint ≤1020px di DESIGN_SYSTEM §5 sudah mendefinisikan perilaku ini) dan 1:1.
- Musik latar lembah (piano/lo-fi) dengan ducking saat inspektur merah muncul.
