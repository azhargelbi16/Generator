# Generator Laporan — Design System v2.1

Diperbarui dari revisi Figma pengguna (24 Oktober 2026): token sidebar/paper
diformalkan, kertas A4 794px Times 12pt, legenda status kalimat, JetBrains Mono.

Sistem desain resmi aplikasi **Generator Laporan Akademik**. Gaya visual: *editorial
akademik* — kertas krem hangat, tinta navy pekat, aksen biru perwatan, dan detail
serif Georgia untuk identitas "karya ilmiah". Semua token di bawah dipakai langsung
oleh `frontend/src/index.css` (`:root`) — satu sumber kebenaran.

> Papan desain resmi: `design/figma/Generator_Laporan_Design_Board_v2.1.svg` (revisi Figma).
> (impor: seret berkas SVG ini ke kanvas Figma Desktop; semua layer bernama).

## 1. Warna (Color Tokens)

| Token | Hex | Pemakaian |
|---|---|---|
| `--canvas` | `#FFF8DE` | Latar belakang utama (kertas kerja) |
| `--paper` | `#FFFFFF` | Lembar dokumen (kertas review, pratinjau A4, preview generasi) — **v2.1** |
| `--sidebar-bg` | `#101827` | Latar sidebar (sama dengan `--ink`) — **v2.1** |
| `--sidebar-line` | `#263957` | Garis pembatas sidebar — **v2.1** |
| `--sidebar-text` | `#CBD7EE` | Teks item sidebar — **v2.1** |
| `--sidebar-muted` | `#8EA3C7` | Teks meta sidebar — **v2.1** |
| `--sidebar-hover` | `#1B2B47` | Latar hover sidebar — **v2.1** |
| `--surface` | `#FFF8DE` | Permukaan kartu / panel |
| `--surface-muted` | `#FFF2C6` | Permukaan sekunder (input, chip) |
| `--ink` | `#101827` | Teks utama, garis kuat, sidebar gelap |
| `--ink-soft` | `#2F405D` | Teks isi |
| `--ink-muted` | `#60708A` | Teks tersier / keterangan |
| `--line` | `#C6D4EC` | Garis batas biasa |
| `--line-strong` | `#AAC4F5` | Garis batas tegas, thumb scrollbar |
| `--accent` | `#8CA9FF` | Aksi utama, item nav aktif |
| `--accent-dark` | `#3D5DAF` | Hover aksi utama, teks aksen |
| `--accent-pale` | `#DCE6FF` | Latar aksi AI, info surface |
| `--warning` | `#6E5A24` | Teks peringatan |
| `--warning-pale` | `#FFF2C6` | Latar peringatan |
| `--danger` | `#7A404A` | Teks error / destruktif |
| `--danger-pale` | `#F4DCE0` | Latar error |
| `--focus-ring` | `rgba(140,169,255,.44)` | Ring fokus input |
| `--danger-line` | `#D7A8B3` | Garis batas status error — **v2.1** |

Alias semantik (nilai sengaja sama, didokumentasikan — v2.1): `--warning-pale` = `--surface-muted`;
`--success-pale` ≈ `--accent-pale`. Bedakan nilainya hanya bila palet mau diperluas.

Status semantik: **sukses** `#E3EBFF` (latar) + `--accent-dark` (teks);
**peringatan** `--warning-pale` + `--warning`; **bahaya** `--danger-pale` + `--danger`;
**info** `--accent-pale` + `--accent-dark`.

## 2. Tipografi

| Peran | Font | Ukuran | Berat | Catatan |
|---|---|---|---|---|
| Display H1 (hero) | Georgia / Times New Roman | `clamp(2.1rem, 4vw, 4.2rem)` | 700 | Tracking `-0.055em` |
| Judul panel H2 | Georgia / Times | 20–24px | 700 | Tracking `-0.02em` |
| Judul kartu H3 | Inter | 14px | 750 | |
| Body | Inter | 13px | 400–500 | Line-height 1.6 |
| Kecil / meta | Inter | 11px | 500 | |
| Label form | Inter | 10–12px | 700–800 | Uppercase, tracking `.12–.16em` |
| Overline / mono | JetBrains Mono → Consolas | 10px | 800 | Uppercase, tracking `.12em` — skala minimum v2.1: 10px |
| Kertas dokumen | Times New Roman | 12pt (16px) | 400 | Line-height 2.0, justify, lebar A4 794px (v2.1) |

## 3. Spacing, Radius, Elevasi

- **Radius**: kartu `8px` (`rounded-2xl`), tombol/input `5px` (`rounded-xl`),
  kontrol kecil `3px` (`rounded-lg`), chip `999px` (pil). Aplikasi sengaja
  memakai radius kecil — nuansa "cetakan akademik", bukan bubble SaaS generik.
- **Spacing**: skala 4/8/12/16/24/34px; padding studio `clamp(16px, 4vw, 68px)`.
- **Bayangan**: panel `5px 5px 0 rgba(23,23,23,.1)` (offset tegas khas cetak),
  kertas `0 12px 30px rgba(32,37,31,.11)`, dialog `0 12px 24px rgba(23,23,23,.13)`.
- **Border**: 1px `--line`; pemisah kuat 1px `--ink`.

## 4. Komponen Inti

- **Tombol** — Primer (`ui-action-primary`): latar `--accent`, teks `--ink`,
  hover `--accent-dark` + teks krem. Sekunder: `--surface-muted`/garis `--line`.
  Aksi AI (`ui-action-ai`): latar `--accent-pale`, hover `--accent`. Tinggi 36px
  (kontrol kecil 28px), lift `translateY(-1px)` saat hover, focus ring 2px.
- **Kolom form** — latar `--surface-muted`, border `--line`, radius 5px; fokus:
  border `--ink` + ring 3px `--focus-ring`. Label terikat `htmlFor`/`id`.
- **Pil status** — Autosave: `✓ Tersimpan` (hijau `--accent` dot) / `Menyimpan…`
  (amber, pulse) / `⚠ Gagal menyimpan — dicoba ulang` (rose `#EF4444`).
  Sitasi kalimat: **Cocok** (hijau), **Tidak cocok** (merah), **Bukan klaim** (abu).
- **Navigasi sidebar** — item grid `23px 26px 1fr auto`; aktif: latar `--accent`,
  teks `--ink`, inset 4px krem kiri + geser `translateX(3px)`.
- **Kertas review** — lebar **794px (A4 @96dpi)** × zoom (75–150%), margin dalam 64px,
  **Times New Roman 16px (12pt)** di atas `--paper` putih, sitasi "(Penulis, Tahun)"
  sebelum tanda baca akhir — v2.1.
- **Legenda status kalimat** (v2.1) — setiap kalimat membawa bar kiri 3px sesuai status:
  **terverifikasi** = bar `--line-strong` (tanpa tint; aktifkan tint `--success-pale`
  lewat satu baris CSS di index.css bila legenda penuh diinginkan);
  **perlu ditinjau** = bar `#D7C28D` + tint `--warning-pale`;
  **kutipan tidak cocok** = bar `--danger` + tint `--danger-pale`;
  **terpilih** = tint `--accent` 45% + ring `--accent-dark`;
  **bukan klaim faktual** = teks `--ink-muted`, tanpa tint;
  kalimat yang sudah ditandai selesai turun ke bar tipis biru.
- **Dialog** — `role="dialog"`, `max-height: calc(100dvh - 40px)`, scroll internal,
  ditutup dengan Escape (klik Batal/✕ otomatis), latar overlay `rgba(16,24,39,.5)`.
- **Toast** — pojok kanan bawah, `role="status" aria-live="polite"`, max 420px.

## 5. Perilaku Responsif (breakpoint CSS px)

Ukuran efektif = lebar jendela ÷ zoom browser (Ctrl +/− di webview).

| Lebar CSS | Perilaku |
|---|---|
| ≥ 1181px | Canvas Review 3 panel: rail bab 230px + kertas + inspektur `min(360px, 30vw)` |
| ≤ 1140px | Hero Studio menyusun vertikal; statistik lebar penuh (tidak terpotong) |
| ≤ 1180px | Rail "Struktur Bab" disembunyikan; inspektur menyempit `min(320px, 32vw)` |
| ≤ 1020px | Inspektur menjadi panel bawah tetap (max 48vh); kertas memakai lebar penuh |
| ≤ 900px | Sidebar 214px; header padat; pil autosave disembunyikan |
| ≤ 760px | Bilah perintah review bisa scroll; padding studio menyusut |
| ≤ 700px | Sidebar jadi drawer mobile + scrim |
| Tinggi ≤ 620px | Mode ringkas: bilah perintah padat, kertas padding 14px |

Prinsip: **kertas selalu terjangkau** — saat lebih lebar dari stage, kertas
dipusatkan lewat `margin: auto` (bukan `justify-content: center`) sehingga sisi
kirinya tetap dapat di-scroll.

## 6. Aksesibilitas

- Kontras teks isi ≥ 4.5:1 (ink di atas krem ≈ 14:1; muted ≈ 5.6:1).
- Semua kontrol interaktif punya `focus-visible` (outline 2px `--accent`).
- Target sentuh/klik ikon ≥ 44×44px (kartu sumber, tombol hapus).
- Label form terikat `htmlFor`/`id`; ikon-only memakai `aria-label`.
- `prefers-reduced-motion` mematikan semua animasi.
- Toast `aria-live`; dialog bisa ditutup Escape.

## 7. Suara & Bahasa (Voice)

Bahasa Indonesia formal-santai ("Anda", imperatif halus). Status selalu menjelaskan
*kenapa*: "⚠ Gagal menyimpan — mencoba ulang…", bukan sekadar "Error". Angka penting
diformat lokal (koma desimal, "12 Oktober 2026"). Istilah akademik konsisten:
kutipan/citasi, sumber, verifikasi, gerbang ekspor.
