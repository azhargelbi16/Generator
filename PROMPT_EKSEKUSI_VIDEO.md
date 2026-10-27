# MISI: Bangun video showcase 3 menit "Generator Laporan" (Remotion) di mesin ini

Anda adalah agent coding yang bekerja langsung di komputer ini (Windows, Git Bash).
Tugas: bangun dan render video showcase program **Generator Laporan** — rekonstruksi
native dengan **React + Remotion** (bukan screen-recording), lalu serahkan file MP4.

## Langkah 1 — Baca berkas ini dulu (urutan wajib)
1. `C:\Generator\STORYBOARD_VIDEO_SHOWCASE.md` — **sumber kebenaran utama**: 9 scene
   dengan rentang frame, teks layar final bahasa Indonesia, token warna DESIGN_SYSTEM
   v2.1, aturan motion/spring/easing, komponen reusable, gerbang QC, data dummy.
2. `C:\Generator\design\DESIGN_SYSTEM.md` — sistem desain resmi (bila bentrok dengan
   storyboard, storyboard menang untuk urusan video).
3. `C:\Generator\frontend\src\components\TabReview.tsx` + `Sidebar.tsx` — label dan
   struktur UI asli untuk rekonstruksi yang setia.
4. Bila masih ada: `C:\Users\ACER\AppData\Local\Temp\gl-clip\src\Klip.tsx` — klip 8 detik
   yang SUDAH terbukti render di mesin ini (scene S6 storyboard = perluasannya).
   SALIN sebagai basis; jangan menulis dari nol selama file itu ada.

## Spek terkunci — jangan ditanya ulang, jangan diubah
- 5400 frame, 30 fps, 1920×1080, MP4 (H.264), **tanpa audio**, bahasa Indonesia.
- Komposisi Remotion: id `Showcase`, `durationInFrames: 5400`.
- Semua data yang tampil = dummy (daftar lengkap di storyboard §7).
- **LARANGAN KERAS**: jangan membaca/mengubah/menghapus apa pun di `C:\Generator\data\`.
- Jangan git commit; jangan mengubah berkas program di luar folder kerja video.

## Jebakan lingkungan mesin ini (WAJIB dipatuhi, ini penyebab kegagalan paling umum)
- `node` (v24) ada di `C:\Program Files\nodejs` tetapi **tidak terlihat oleh `cmd.exe`**
  → semua shim `.cmd` (`npx`, `npm run`, postinstall `install.js`) pasti gagal dengan
  error `'node' is not recognized`.
- Pasang dependensi: `npm install --ignore-scripts --no-audit --no-fund`
  (binary esbuild/compositor datang via optionalDependencies — aman tanpa postinstall).
- Render & still **wajib** dipanggil langsung:
  `node node_modules/@remotion/cli/remotion-cli.js render src/index.ts Showcase out/showcase.mp4`
  `node node_modules/@remotion/cli/remotion-cli.js still src/index.ts Showcase out/f.png --frame=1234`
- Chrome Headless Shell terunduh otomatis saat render pertama (perlu internet sekali).
- Folder kerja: buat baru di `C:\Generator\clip-showcase\` (scaffold minimal ada di
  storyboard §5: package.json, tsconfig, remotion.config.ts, src/index.ts, src/Root.tsx).

## Alur kerja bertahap (gerbang — jangan lompat)
1. Scaffold + install (lihat atas). Verifikasi `node_modules/@remotion/cli` ada.
2. **Uji pipeline**: render `--frames=0-89` → MP4 kecil harus keluar. Gagal = berhenti,
   perbaiki dulu; jangan lanjut sebelum lolos.
3. Bangun scene S1–S9 sesuai storyboard §3; maksimalkan komponen reusable §4
   (sidebar, kertas A4 + blok kalimat ber-tint/bar/ring, inspektur hijau/merah,
   pil status, kursor+ripple, kartu judul).
4. **QC per scene**: render still di frame tengah scene (daftar frame di storyboard §6),
   periksa: tidak ada teks terpotong/overlap, kursor tepat di target klik, pil terbaca,
   tidak ada elemen keluar frame. Untuk klaim "terpotong" di tepi: verifikasi dengan
   CROP PNG area itu (mis. via Pillow) sebelum percaya — inspeksi gambar penuh 1920×1080
   sering salah lapor. Perbaiki → still ulang → lanjut hanya setelah bersih.
5. Render penuh 5400 frame (±5–15 menit; jangan dianggap hang).
6. Verifikasi file: durasi box `mvhd` = 180.000 s, jumlah frame, ukuran wajar 15–30 MB.
7. Salin hasil ke `C:\Generator\showcase_generator_laporan_3menit.mp4`.

## Kriteria terima (semua harus terpenuhi)
- [ ] Durasi tepat 180,000 dtk @30fps, 1920×1080, tanpa trek audio.
- [ ] 9 scene lengkap sesuai rentang frame storyboard §3, khususnya sub-beat S6
      (klik → hijau → sunting → merah → legenda) berurutan benar.
- [ ] Tidak ada teks terpotong/overlap di semua still QC; data dummy saja.
- [ ] Folder `C:\Generator\data\` tidak tersentuh.

## Format laporan akhir (wajib)
- Jalur MP4 + ukuran + durasi terverifikasi (metode verifikasi disebut).
- Daftar still QC yang diperiksa + statusnya per scene.
- Semua klaim diberi label: **fakta / perkiraan / tidak tahu**.
- Jangan mengajukan pertanyaan yang jawabannya sudah ada di storyboard; bila benar-benar
  terblokir, tuliskan titik blokirnya + apa saja yang sudah dicoba, lalu berhenti.
