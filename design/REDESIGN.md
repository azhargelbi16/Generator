# Generator Laporan | Field Notes

Tanggal: 2026-10-24

Cara pakai: buka file desain di Figma lalu pilih **Plugins -> Development -> Generator Laporan - UI Redesign**.
Sumber plugin ada di `design/figma-plugin/manifest.json` dan `design/figma-plugin/code.js`.
Plugin idempoten, jadi frame hasil run sebelumnya akan dihapus sebelum papan baru dibuat.

## Arah visual

Redesain ini menggunakan Cult UI sebagai referensi ritme visual, bukan sebagai template yang disalin.
Yang diambil adalah kontras hitam dan kertas, komposisi yang tegas, micro-interaction yang terasa hidup,
serta komponen yang menunjukkan state dengan jelas. Identitas Generator tetap editorial dan akademik.

Bahasanya adalah **meja kerja editorial berkontras tinggi**:

- Canvas hangat seperti kertas kerja, dengan panel putih hanya untuk permukaan yang perlu dibaca.
- Ink navy sebagai dasar, `#FFF2C6` sebagai highlight hangat, `#FFF8DE` sebagai surface utama,
  `#AAC4F5` sebagai state pendukung, dan `#8CA9FF` sebagai aksen aktif.
- Garis tipis, label kecil, dan ruang kosong dipakai untuk membantu orientasi, bukan dekorasi.
- Radius kecil dan bayangan pendek menjaga permukaan tetap terasa seperti alat kerja, bukan kumpulan kartu SaaS.
- Hover, focus, active, loading, dan error diberi perubahan bentuk yang terbaca tanpa animasi dekoratif.
- Satu bidang gelap dengan sapuan `#FFF2C6` menjadi fokus saat memulai laporan; treatment ini tidak diulang di setiap panel.
- Semua contoh data ditulis sebagai placeholder seperti `[JUDUL LAPORAN]` atau `[SUMBER 01]`.
- State empty, loading, error, dan success ditampilkan sebagai bagian dari alur, bukan dipisahkan dari produk.

Reading: alat kerja akademik untuk mahasiswa, dengan bahasa visual editorial kontras tinggi, dial ENERGY 2 / RHYTHM 2 / MOTION 2.

## Frame yang dibuat

| Frame | Isi |
| --- | --- |
| `00 · Field Notes design sheet` | Arah visual, token warna, tipografi, dan aturan penggunaan aksen |
| `01 · Studio Laporan` | Sumber kosong, formulir laporan, dan aksi mulai menyusun |
| `02 · Menyusun laporan` | Tahap proses, pratinjau bagian aktif, dan aktivitas yang sedang berjalan |
| `03 · Canvas & Review` | Struktur bab, dokumen, inspektor kalimat, dan bukti sumber |
| `04 · Pemeriksaan Akhir` | Gerbang ekspor dengan temuan yang bisa ditindaklanjuti |
| `05 · Pengaturan AI` | Endpoint, API key, model, temperatur, dan status koneksi |
| `06 · UI States` | Empty, loading, error, dan success state untuk alur utama |

## Aturan implementasi

1. Jangan mengubah placeholder menjadi data realistis tanpa sumber nyata.
2. Jangan menambah angka statistik, nama pengguna, aktivitas, atau status koneksi yang belum berasal dari aplikasi.
3. Gunakan status hanya bila status itu membantu keputusan pengguna.
4. Setiap tombol dalam implementasi harus memiliki aksi nyata atau dihapus.
5. Pertahankan state kosong, proses berjalan, error, dan berhasil ketika desain dipindahkan ke React.
6. Pertahankan kontras warna dan fokus keyboard saat membuat versi produksi.

## Cara menjalankan ulang

1. Buka Figma.
2. Pilih **Plugins -> Development -> Import plugin from manifest** jika plugin belum terdaftar.
3. Pilih `design/figma-plugin/manifest.json`.
4. Jalankan **Generator Laporan - UI Redesign**.
5. Bila `code.js` berubah, jalankan plugin lagi. Frame lama akan dibersihkan otomatis.
