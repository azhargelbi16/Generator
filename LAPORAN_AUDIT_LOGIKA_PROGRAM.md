# Laporan Audit Logika Program — Generator Laporan

Tanggal: 25 Oktober 2026
Cakupan: `src/generator/` (content, prompts, format_spec, renderer, preflight, report, api_bridge) + bukti gejala pada DOCX di `output/`.

Ringkasan singkat: **mesin menulis prosa yang lancar, tetapi 4 keputusan arsitektur membuat dokumen yang dihasilkannya tidak layak dikumpulkan**: (1) setiap bab ditulis dari sumber yang sama tanpa dedup lintas bab, (2) kegagalan AI ditelan diam-diam dan bab kosong tetap diekspor, (3) sitasi ditambahkan buta di atas teks yang sudah bersetasi, (4) verifikasi justru memberi skor sempurna pada salinan verbatim.

---

## KRITIS

### BUG 1 — Kalimat sumber sama berulang lintas bab (Biochar: kalimat identik di 1.1, 3.1, 3.2.1, 4.1)

**Gejala:** Kalimat "Penelitian menunjukkan biochar mampu menaikkan pH tanah asam sebesar 0,5–1,2 satuan pada dosis 10 ton per hektar" muncul di paragraf [11], [25], [28], [34] dokumen Biochar — termasuk dua kali dalam BAB 3 yang sama (3.1 Hasil vs 3.2.1 Pembahasan).

**Akar masalah (tiga lapis yang saling memperkuat):**

1. `src/generator/ai/content.py:641-655` — jalur varian (A/B/C) membuat satu panggilan AI per BAB, tetapi setiap langkah bab menerima SELURUH chunk sumber yang sama:
   ```python
   ref_chunks = chunk_refs if len(chunk_refs) <= 30 else batches[0]   # baris 644
   ```
   Model dipaksa menulis 4 bab dari bahan identik → fakta inti yang sama ditulis ulang tiap bab.
2. `src/generator/ai/content.py:239-275` (`_merge_sections`) — dedup HANYA di dalam section berjudul sama (key = judul section, baris 246). Duplikat antar "3.1 Hasil" vs "3.2.1 Pembahasan" vs "4.1 Kesimpulan" tidak pernah dibandingkan. Set `emitted` global hanya memfilter pratinjau streaming, BUKAN hasil `_merge_sections` (baris 564-565) dari JSON utuh.
3. `src/generator/document/renderer.py:152-161` — satu-satunya dedup di render hanya membandingkan bab level-1 dengan subbab level-2 tepat di bawahnya, dan hanya bila daftar kalimatnya identik persis.

**Perbaikan yang disarankan:** dedup similarity global (bukan per-judul) di `_merge_sections`; atau kirim ringkasan kalimat yang sudah terpakai sebagai konteks "jangan tulis ulang" pada langkah bab berikutnya; atau alokasikan chunk sumber berbeda per bab.

### BUG 2 — Bab kosong gagal-diam-diam dan tetap diekspor (termasuk kerangka kosong 14:28)

**Gejala:** (a) BAB 2 Tinjauan Pustaka dokumen Biochar hanya judul tanpa satu kata. (b) `Analisis_Efektivitas_Sensor_Pertanian_Cerdas.docx` (14:28) berisi kerangka kosong: "Kalimat pengantar laporan." + dafpus kosong — tetap ditulis ke `output/`.

**Akar masalah (rantai fail-open):**

1. `content.py:372-374` — `_stream_batch` menelan `StreamError`; buffer tak terurai → `data = None`.
2. `content.py:366-369` — kalimat duplikat lintas bab dibuang dari `collected` (akibat Bug 1, bab berikut hampir semua duplikat) → `collected` kosong.
3. `content.py:567-574, 715-718` — `merged=False` hanya menaikkan counter `gagal` + WARNING log; tidak ada retry per bab.
4. `format_spec.py:344-440` (`normalize_sections`) — heading bab kosong tetap dimasukkan; subbab dinamis BAB 2 yang tak terisi dibuang senyap (baris 423-425).
5. **Gerbang ekspor tidak menahan:** `api_bridge.py:1208-1312` (`export_report`) TIDAK memanggil `preflight.find_issues`/`can_export` sama sekali — satu-satunya cek keras adalah leftover `{{...}}` (baris 1287-1299). `preflight.py` memang bisa mendeteksi bab kosong (`_empty_section_titles`, baris 111-136), tetapi hasilnya hanya jadi dialog konfirmasi di frontend; endpoint ekspor backend bisa dipanggil apa adanya oleh skrip uji → file kosong tetap lahir.

**Perbaikan yang disarankan:** (a) retry per bab yang gagal; (b) `export_report` wajib menjalankan `find_issues` dan menolak keras `empty_sections`/`pending` (fail-closed), bukan hanya andal pada dialog frontend.

---

## MAYOR

### BUG 3 — Sitasi ganda: naratif + parenthetik menumpuk

**Gejala:** "...menurut studi yang dilakukan oleh Lestari, Wardhani, dan Arifin (2024) (Lestari et al., 2024)"; juga "Nurhaliza dan Wijaya (2022) mencatat ... (Nurhaliza & Wijaya, 2022)." Gaya campur "dkk." vs "et al.".

**Akar masalah:** `content.py:730-747` (`compose`) menambahkan sitasi parenthetik secara buta ke setiap kalimat faktual ber-`source_ids`, tanpa memeriksa apakah teks kalimat sudah memuat sitasi naratif. `prompts.py:57-65` juga tidak pernah melarang model menulis sitasi di dalam `text` → tabrakan tak terhindarkan.

**Perbaikan:** deteksi pola penulis-tahun di `sentence.text` (regex) sebelum menyisipkan parenthetik, atau strip sitasi AI lalu rangkai ulang; tambahkan larangan sitasi naratif di prompt.

### BUG 4 — Artefak "[TABEL: ...]" dan "Sumber: [0], [1]" bocor ke DOCX

**Gejala:** paragraf "[TABEL: Ringkasan hasil ...]" + "Sumber: [0], [1]"; dokumen punya 0 tabel sungguhan.

**Akar masalah:** by design separuhnya — `format_spec.py:147-149` MEMINTA model menulis penanda `[TABEL: ...]` dan baris "Sumber: ...", sementara `prompts.py:87-92` melabeli sumber `[sumber 0]`, `[sumber 1]` sehingga model meniru format indeks itu. Tidak ada satu pun pasca-proses yang mengonversi penanda menjadi tabel DOCX, memetakan `[0]` ke label penulis-tahun, atau memblokir ekspor dokumen yang masih memuat penanda belum-terisi (berbeda dengan `{{...}}` yang ditolak keras).

**Perbaikan:** gerbang ekspor memperlakukan `[TABEL:`/`[GAMBAR:`/`[FOTO:` yang belum terisi seperti leftover `{{...}}` (tolak); atau renderer membuat tabel kosong ber-caption dari penanda; parser "Sumber: [n]" → sitasi penulis-tahun.

### BUG 5 — Patchwriting terstruktur: ~32% shingle 8-kata identik dengan sumber

**Gejala:** 258/792 shingle (32,6%) body dokumen identik dengan teks sumber; BAB 3 dokumen AI hampir seluruhnya salinan abstrak sumber.

**Akar masalah:** `prompts.py:60-62` menuntut "Tulis HANYA berdasarkan teks sumber ... quote diambil harfiah" tanpa instruksi parafrase/sintesis; `verification.py` memberi salinan verbatim skor dukungan 1.0 → status "terverifikasi" — pipeline secara struktural MENGHARGAI salinan. Fitur parafrase hanya manual per paragraf, dan fallback-nya mengembalikan paragraf asal senyap (`content.py:789-790`).

**Perbaikan:** tambah cek overlap n-gram kalimat-vs-sumber di verifikasi; kalimat dengan overlap tinggi ditandai "perlu parafrase" (merah), bukan hijau.

### BUG 6 — Referensi tanpa penulis + sitasi dalam-teks memakai judul penuh

**Gejala:** "Biochar dan Kesehatan Tanah. (2023). Jurnal Tanah dan Sumberdaya Lahan." tanpa penulis; hampir semua kalimat disitasi "(Biochar dan Kesehatan Tanah, 2023)".

**Akar masalah:** `bibliography.py:51-73` menerima `authors=[]` tanpa validasi; `merge_metadata` (86-107) tidak pernah menambal penulis kosong dari metadata dokumen; `citation.py:110-112, 190-197` memakai judul sebagai kepala sitasi; `preflight.py:81-88` hanya menandai sumber yang tanpa penulis DAN tanpa judul — yang berjudul-tapi-tanpa-penulis lolos.

**Perbaikan:** wajibkan penulis (atau `is_org`) sebelum sumber bisa dikutip; tambal dari metadata; perluas preflight.

### BUG 7 — Judul subbab placeholder mentah tercetak: "3.2.1 Pembahasan topik 1"

**Gejala:** heading "Pembahasan topik 1", "Pembahasan topik 2" — nama template, bukan judul nyata.

**Akar masalah:** `format_spec.py:239` (`chapter_sub_outlines`) menghapus kurung `{}` SEBELUM judul dikirim ke AI, sehingga model tidak tahu itu placeholder dan menyalinnya mentah; `normalize_sections` (baris 339) mempertahankan salinan itu sebagai judul final.

**Perbaikan:** pertahankan penanda `{}` saat dikirim ke AI (aturan penggantian sudah ada di _RULES), atau tolak judul yang cocok pola "topik N" saat normalisasi.

---

## MINOR

### BUG 8 — "BAB 3. HASIL DAN PEMBAHASAN" dipaksakan untuk laporan tinjauan literatur
`api_bridge.py:972, 984-989` default varian B + outline hardcoded; tidak ada mode "tinjauan pustaka/sintesis literatur". Untuk laporan yang murni sintesis 5 jurnal, label "Hasil" menyesatkan.

### BUG 9 — Spasi ganda dalam sitasi "(Nurhaliza & Wijaya,  2022)"
`bibliography.py:68` tidak `.strip()` bidang `year` (bandingkan `authors` yang di-strip) → " 2022" lolos ke `citation.py:147-148`.

### BUG 10 — Tanggal sampul bisa berbahasa Inggris ("25 October 2026")
`scratch/generate_agriculture_report.py:349` memakai `datetime.now().strftime("%d %B %Y")` (nama bulan mengikuti locale, Inggris di mesin ini), dan `export_report`/`build_fields` menerima `TANGGAL` string mentah apa adanya — `format_tanggal()` (Indonesia, `report.py:29-33`) hanya dipakai sebagai FALLBACK saat field kosong, bukan sebagai formatter wajib. Perbaikan: selalu normalisasi ulang tanggal melalui `format_tanggal` di jalur ekspor.

### BUG 11 — Harness uji sendiri menyesatkan
`scratch/generate_agriculture_report.py:311-312` memaksa SEMUA sumber masuk cited (`cited_ids = set(range(...))`) sehingga dafpus menggelembung; dan `json.loads` tanpa `repair_truncated_json` → uji tidak merepresentasikan jalur produksi. Hasil uji (file dummy) tidak bisa dipakai menilai mutu pipeline.

### BUG 12 — Nomor halaman tidak pernah ditambahkan
`renderer.py` tidak punya logika footer/nomor halaman sama sekali; seluruhnya bergantung pada template, dan `Template_Standar_Akademik.docx` ber-footer kosong → semua ekspor tanpa nomor halaman.

---

## Yang BUKAN bug (jangan salah tuduh)

- **"Klik kanan di sini lalu pilih Update Field..."** — ini field TOC Word asli (`renderer.py:22-30`) plus `w:updateFields` aktif (baris 112-126); teks itu hanya isi field sebelum Word memperbaruinya. Perilaku benar.
- **Judul bab level-1 tanpa paragraf sendiri** — by design; isi hidup di subbab (pengecualian di `_empty_section_titles`, preflight.py:114-117 mencegah peringatan palsu).

## Urutan prioritas perbaikan

1. **Fail-closed di ekspor backend** (BUG 2e): `export_report` wajib menjalankan `find_issues` dan menolak bab kosong/kalimat tertunda. Satu perbaikan, menghapus satu kelas file sampah.
2. **Dedup lintas bab + pembagian sumber per bab** (BUG 1): hilangkan pengulangan 4× sekaligus mengurangi patchwriting.
3. **Sitasi: strip/deteksi naratif sebelum sisip parenthetik** (BUG 3) + prompt melarang sitasi di `text`.
4. **Gerbang penanda `[TABEL:...]`/`Sumber: [n]`** (BUG 4) + parser indeks → penulis-tahun.
5. **Verifikasi overlap verbatim** (BUG 5): salinan verbatim tidak boleh berstatus hijau.
6. Sisanya (BUG 6-12) berurutan sesuai keparahan.

---

## STATUS PERBAIKAN (diimplementasikan 25 Okt 2026)

Batasan yang dipegang: **tanpa panggilan AI tambahan, tanpa batch tambahan, tanpa
verifikasi ulang saat ekspor**. Semua penambahan biaya O(1)/O(n) ringan.

| Bug | Status | Perubahan |
| --- | --- | --- |
| BUG 1 dedup lintas bab | **Selesai** | `content.py` `_merge_sections`: indeks hash global (teks → himpunan sumber) membuang kalimat identik lintas bab; dedup kemiripan tetap per-bab agar biaya kuadratik tidak membesar. Ditambah aturan prompt anti-pengulangan. |
| BUG 2 bab kosong & skeleton diekspor | **Selesai (gate) + mitigasi** | `preflight.export_blockers` + `export_report` menolak keras: laporan kosong, bab wajib kosong, penanda `[TABEL/GAMBAR/FOTO]` belum diisi, dafpus kosong padahal ada klaim faktual. Retry otomatis per bab **tidak** ditambahkan (menambah panggilan AI) — diganti dedup + gate. |
| BUG 3 sitasi ganda | **Selesai** | `content.compose`: bila teks sudah memuat sitasi (pola `(…tahun…)`), sitasi buatan kode tidak ditambahkan. Prompt juga melarang menulis sitasi sendiri. |
| BUG 4 `[TABEL:]`/`Sumber: [0]` | **Selesai sebagian** | Gerbang ekspor menolak penanda yang belum diganti; prompt melarang `Sumber: [0]` dan meminta `(Penulis, Tahun)`. Parser otomatis `[n]`→penulis-tahun belum dibuat. |
| BUG 5 patchwriting | **Selesai** | `verification.verbatim_ratio`: kalimat >= 12 kata yang >= 80% potongannya muncul harfiah di jendela sumber kini berstatus `perlu_ditinjau` dengan alasan "parafrase dulu", bukan hijau. Dicek dengan sampel 5 potongan 8 kata + `str.find` (bukan set shingle penuh) agar biayanya kecil. |
| BUG 6 referensi tanpa penulis | **Selesai (peringatan)** | `preflight._citation_problems` menandai sumber terkutip yang tidak punya penulis ("periksa apakah penulis terlewat") tanpa memblokir ekspor — sumber organisasi/anonim tetap sah. |
| BUG 7 judul "Pembahasan topik 1" | **Selesai** | `format_spec.chapter_sub_outlines` mengirim judul dinamis lengkap dengan `{...}` agar diganti AI (aturan _RULES), bukan dicetak mentah. |
| BUG 8 label HASIL DAN PEMBAHASAN | **Selesai** | `format_spec` menambah **varian D "Tinjauan pustaka"**: BAB 1 Pendahuluan, BAB 2 Tinjauan Pustaka, BAB 3 **PEMBAHASAN** (subbab dinamis `{Pembahasan topik 1..3}`), BAB 4 Kesimpulan dan Saran — tanpa bab "Hasil". Varian muncul di pilihan "Format laporan" lewat `variant_choices()`/`get_format_variants`; label UI di `TabLaporan.tsx` diperbarui dan `frontend/dist` dibangun ulang. Varian A/B/C tidak diubah. |
| BUG 9 spasi ganda tahun | **Selesai** | `bibliography._source_from_dict`: `year.strip()`. |
| BUG 10 tanggal Inggris | **Selesai** | `report.format_tanggal_teks` + normalisasi di `build_fields` dan `export_report`. |
| BUG 11 harness uji menyesatkan | **Selesai** | `scratch/generate_agriculture_report.py`: tanpa pemaksaan `cited_ids`, memakai pemulihan JSON produksi, tanggal via `format_tanggal`. |
| BUG 12 nomor halaman | **Selesai** | `renderer._ensure_page_numbers`: footer bawah-tengah + field PAGE, hanya bila footer template kosong; `titlePg` + nomor mulai 0 agar sampul tidak bernomor dan halaman isi pertama = 1. Footer yang sudah berisi teks/field PAGE tidak disentuh. |

Bukti gelombang pertama: `pytest tests/ -q` → **343 passed**. Benchmark `scratch/bench_fixes.py`:
dokumen 48–200 kalimat tidak menunjukkan kenaikan berarti (selisih ±0,4 ms, sering
lebih cepat karena duplikat dibuang sebelum perbandingan); stres 1000 kalimat
+0,8–1,4 ms (kisaran noise). Prompt bertambah ±0,7 KB per panggilan bab (<5%).

Bukti gelombang kedua (deteksi verbatim + nomor halaman):

- `pytest tests/` → **semua lulus** (343 → 349 tes; 6 tes baru).
- `scratch/bench_verify.py` (200 kalimat, sumber 28 KB): verifikasi dengan cek
  verbatim **22,3–22,6 ms** vs tanpa cek **19,6–20,1 ms** → **+2,6 ms (+13%)**
  untuk satu kali pemeriksaan dokumen. Versi pertama implementasi memakai set
  shingle penuh dan menambah +11,6 ms (+63%), lalu dioptimalkan menjadi sampel
  substring. Tidak ada panggilan AI tambahan dan tidak ada I/O tambahan.

---

## GELOMBANG 3 — evaluasi uji pakai (25 Okt 2026)

Masukan pengguna setelah menguji output nyata (dokumen
`output/Pengaruh_Media_Sosial_...docx`, varian B):

| Masukan | Temuan teknis | Perbaikan |
| --- | --- | --- |
| 1. Subbab tinjauan pustaka kebanyakan; lebih baik 3–5 subbab berkualitas | Varian B/A memakai 8 node dinamis untuk BAB 2, lalu `normalize_sections` menambah setiap blok AI sebagai subbab tambahan → dokumen uji mencapai **2.1–2.13** dengan topik berulang. | Varian D dirombak: BAB 2 = **5 node dinamis** (AI memilih 3–5), tanpa sub-subbab, aturan prompt "2–3 paragraf per topik, jangan ulangi topik". `normalize_sections` membatasi subbab BAB 2/3 varian D maksimum 5; kelebihan topik digabung ke subbab terakhir (isi tidak hilang). |
| 2. Masih menghasilkan "Hasil dan Pembahasan" | Dokumen uji memakai varian B (default lama) yang memang punya bab Hasil. | **Varian D menjadi default** (backend `start_generation` dan pemilih UI). Varian D tidak punya bab Hasil sama sekali; pengguna yang memang butuh bab Hasil tetap bisa memilih A/B/C. |
| 3. Alur pembahasan: Rumusan Masalah → Tujuan → Pembahasan | Jalur varian memanggil AI **per bab secara terpisah**, sehingga Bab 3 tidak tahu rumusan masalah/tujuan yang sudah ditulis di Bab 1. | `generate_sections` kini mengirim **konteks antarbab** (rumusan masalah, tujuan, daftar subbab yang sudah ada, ≤900 karakter) ke setiap bab berikutnya. Varian D: BAB 3 = 5 node dinamis `{Jawaban rumusan masalah 1..5}` dengan aturan "jumlah subbab = jumlah rumusan masalah, urutan sama". Bila AI tetap mengirim judul placeholder, judul diambil dari butir Rumusan Masalah yang sejajar (`_heading_from_rumusan`), sehingga jumlah subbab tetap sesuai. |
| 4. Sampul harus "PROGRAM STUDI AGROTEKNOLOGI / FAKULTAS PERTANIAN / UNIVERSITAS JEMBER / 2026" | Nilai berasal dari profil dan dicetak apa adanya; dokumen uji menampilkan "PROGRAM STUDI Teknologi Informasi", "FAKULTAS Teknik", "Universitas Jember". | `build_fields` dan jalur ekspor mencetak PRODI/FAKULTAS/INSTITUSI **kapital**; tahun dari tanggal ekspor. Dengan profil Agroteknologi/Pertanian/Universitas Jember hasilnya persis empat baris yang diminta. |
| Tambahan: judul `{Pembahasan topik 1}` bocor ke dokumen | Perubahan gelombang 1 (mengirim `{...}` ke AI) membuat model kadang menyalin kurawalnya; `_clean_title` tidak membuang `{` `}`. | `_display_title` membuang kurawal dan mengenali nama template; judul yang masih placeholder tidak dicetak — isinya digabung ke bagian sebelumnya, dan penomoran subbab dinamis dihitung ulang agar tetap berurutan (tidak ada lompatan 3.1 → 3.3). |

Bukti gelombang 3: **356 tes lulus**; simulasi `scratch/e2e_variant_d.py`
(fake AI yang sengaja mengembalikan 6 topik dan satu judul placeholder):

```
BAB 2: 5 subbab (dari 6 blok AI, kelebihan digabung)
BAB 3: 3 subbab = 3 rumusan masalah, judul 3.2 diambil dari RM yang sejajar
Judul berkurawal tersisa: tidak ada
Ekspor DOCX: sukses
Sampul: PROGRAM STUDI AGROTEKNOLOGI / FAKULTAS PERTANIAN /
        UNIVERSITAS JEMBER / 2026
```

Tambahan biaya: prompt bertambah ≤900 karakter (≈225 token) per bab setelah
bab pertama; **tidak ada panggilan AI baru** dan tidak ada batch baru.

---

## GELOMBANG 4 — enam item pipeline (25 Okt 2026)

| Item | Perubahan (file) | Bukti E2E nyata (varian B, 3 sumber) |
| --- | --- | --- |
| 1. Kedalaman isi | `prompts.content_prompt`: aturan kuantitatif (L2 3–5 kalimat, L3 2–3 kalimat, kecuali daftar bernomor) + "satu objek = satu kalimat" + larangan mengulang untuk kuota. Tes baru `tests/test_prompts.py`. | Semua subbab memenuhi minimum: L2 3–5 kalimat (3.1 Hasil 13, 2.1/2.2 3), L3 2–3+ (2.2.3 20, 3.2.2 7). Tidak ada subbab 1 kalimat. |
| 2. Duplikat parafrase BAB 4 | `content._merge_sections`: ambang dedup 0,55 khusus section kesimpulan/saran (tetap hanya bila sitasi sama). | 4.1/4.2 berisi `[1,2,3]` tanpa nomor ganda. |
| 3. Penanda `[TABEL]` | `format_spec._VARIANT_EXTRA_RULES`: varian B/D dilarang menulis penanda/deskripsi tabel; `normalize_sections` membuang kalimat deskriptor tabel via regex. | 0 penanda `[TABEL` dan 0 kalimat deskriptor pada DOCX final. |
| 4. Satu butir satu paragraf | `renderer._numbered_groups`: blok berbutir dipecah per butir (paragraf naratif tetap utuh); spasi antar-run referensi diperbaiki. | DOCX: 1.2, 1.3, 4.1, 4.2 masing-masing 3 paragraf butir terpisah. |
| 5. APA 7 lengkap | `Source` + `volume/issue/pages`; CrossRef → `intake.source_from_crossref_message`; round-trip `records`; `citation.reference_segments` + `_join_runs`; `report.reference_runs_for`; renderer menulis run italic. | Ketiga entri memuat volume(nomor), halaman, dan run italic: *Healthcare, 9*(10), 1272; *Education Sciences, 15*(3), 317; *Cyberpsychology, Behavior, and Social Networking, 14*(5), 275–280. |
| 6. Verifikasi lintas bahasa | `verification._cross_language` (rasio penanda bahasa ID vs EN) + `REASON_TRANSLATED`; kutipan asing panjang yang ditemukan persis berstatus hijau dengan alasan terjemahan; halusinasi sebahasa dan salinan verbatim tetap merah. | Sebelum: 22 hijau / 19 perlu_ditinjau / 12 merah (dari 53). Sesudah: **64 hijau / 2 perlu_ditinjau / 13 merah** (dari 79) — 81% hijau, 97% bukan perlu_ditinjau. |

Status akhir gelombang 4: **379 tes lulus** (356 → 379; 23 tes baru), E2E
`step4 → step5 → step6b → step7` sukses mengekspor DOCX final, dan evaluasi
`step9_final_eval.py` memenuhi seluruh ukuran keberhasilan:

```
Penanda [TABEL/GAMBAR/FOTO]: 0        Kalimat deskriptor tabel: 0
Butir 1.2/1.3/4.1/4.2: [1,2,3] tanpa nomor ganda
Subbab di bawah minimum: tidak ada
Daftar pustaka: 3 entri, semuanya volume(issue), halaman, italic
```

Catatan kompatibilitas: sumber lama tanpa `volume/issue/pages` tetap diekspor
dengan bentuk referensi sebelumnya; field baru hanya menambah, tidak mengubah
kontrak frontend. Draf aktif pengguna dicadangkan ke
`scratch/student_run/backup/aktif-backup.json` sebelum E2E.

---

## GELOMBANG 5 — struktur paragraf & isi (25 Okt 2026)

| Item | Perubahan utama | Bukti |
| --- | --- | --- |
| 1. Latar belakang tidak boleh satu paragraf raksasa | `content._sections_from_dict`: kalimat pipih Gemini dikelompokkan menurut field `paragraph`/`par`; tanpa penanda dipecah tiap 4 kalimat; kalimat pipih di level section juga diterima; butir bernomor tetap satu per paragraf. Prompt meminta field `paragraph` dan 2–3 paragraf per subbab naratif. `format_spec._clean_paragraphs` memecah paragraf wrapper > 5 kalimat. | DOCX hasil E2E: **1.1 Latar Belakang = 2 paragraf terpisah** (5 dan 4 kalimat), bukan satu blok. Unit test: 8 kalimat pipih → ≥ 2 Paragraph; `paragraph` 1,1,2 → 2 Paragraph; 5 butir bernomor → 5 Paragraph. |
| 2. Kedalaman pembahasan | Prompt diganti berbasis paragraf (BAB 2/3: ≥3 paragraf, tiap paragraf 3–5 kalimat; L3 2–3 paragraf) + panduan isi per paragraf (temuan → perbandingan → mekanisme/implikasi) + larangan mengulang/memparafrase. Anggaran token langkah naik ke 16384 dan **streaming tidak lagi hardcoded 8192**. Bab dipecah menjadi panggilan ≤ 2 subbab (model membatasi ±18 KB keluaran), dengan retry sekali bila struktur salah. `_cap_paragraphs`/`_enforce_paragraph_shape` menjamin ≤ 6 paragraf dan target paragraf BAB 2/3. | DOCX E2E: 3.1 Hasil 3 paragraf; 3.2 Pembahasan 6 paragraf; total badan 1.900–2.800 kata (bervariasi per run). Unit test: rencana generasi memecah bab tanpa judul bab; paragraf wrapper 12 kalimat → 3 paragraf; retry struktur teruji. |
| 3. BAB 4 hanya Kesimpulan & Saran | Aturan prompt varian B/D: bab terakhir tanpa prosa pengantar/penutup. `format_spec._route_last_chapter_body`: paragraf prosa level BAB dibuang; butir bernomor dipindahkan ke 4.1 (atau 4.2 bila bernada saran). Varian A/C (PENUTUP) tidak diubah. | DOCX E2E: heading **BAB 4. KESIMPULAN DAN SARAN langsung diikuti 4.1 Kesimpulan** tanpa paragraf di antaranya; 4.1/4.2 masing-masing butir terpisah. Unit test: BAB 4 level-1 = 0 paragraf; varian C tetap mempertahankan prosa. |

Status: **399 tes lulus**. Biaya baru: satu laporan ± 9 panggilan AI (bukan 4)
karena pemecahan bab, durasi E2E ± 60–90 detik.

**Catatan historis:** sisa masalah struktur BAB 2 pada gelombang 5 (model
menaruh isi di level BAB, proporsi hijau 77–97%) diselesaikan pada gelombang 6
lewat penyebaran deterministik + pelengkap subbab + sanitasi judul; lihat bagian
GELOMBANG 6 di bawah untuk bukti dua run-nyata yang hijau penuh.

---

## GELOMBANG 6 — 4 cacat struktur + Penjaga Regresi (26 Okt 2026)

### Penjaga Regresi (Fase 0)

- `tests/test_e2e_invariants.py`: klien AI palsu dengan 6 variasi jawaban
  (schema bersarang, pipih+`paragraph`, judul kalimat panjang, isi level BAB,
  butir duplikat kesimpulan, JSON terpotong) → pipeline generate → normalize →
  render DOCX, lalu assert invariant S1–S7, K1–K4, V1–V2, E1. **Hijau.**
- `scripts/e2e_check.py`: jalankan pipeline lewat ApiBridge dengan AI sungguhan
  (3 sumber tersimpan, varian b), ekspor DOCX, cetak PASS/FAIL 15 invariant +
  metrik kata/kalimat/% hijau. Basis data, draf, dan output diarahkan ke
  `scratch/e2e_runs/`; `data/` milik pengguna hanya dibaca untuk config AI.

### Per fase: akar masalah (terverifikasi) → perbaikan → hasil guard

| Fase | Akar masalah terverifikasi | Perbaikan (diff minimal) | Guard |
| --- | --- | --- | --- |
| 1. BAB 2 tanpa subbab | Model kerap membalas tanpa judul subbab yang diminta; `_with_chapter_heading` membuat section "BAB n" dan merge menumpuk seluruh isi di level-1. | Prompt: aturan keras "setiap judul outline wajib jadi section persis; DILARANG isi di section BAB". Merge/normalize: `_fallback_distribute_chapter_body` menyebar isi level-BAB ke subbab (butir→daftar, prosa→naratif, level-2 diprioritaskan), `_rebalance_chapter` mengisi subbab kosong dari isi longgar, `_ensure_level2_subbab` memulihkan 2.1/2.2 yang hilang dengan memindahkan isi (bukan menduplikasi). | S1 hijau di fake (semua style) dan di 2 run-nyata. |
| 2. Sanitasi judul | Tidak ada sanitizer; model mengganti `{...}` dengan kalimat panjang/terpotong. | `_sanitize_title` (≤10 kata, buang nomor AI, deteksi kalimat) + fallback judul baku varian; judul pelengkap tanpa nomor dipetakan ke nomor subbab yang diminta; judul turunan yang masih berupa kalimat diganti label baku (`Objek Kajian`, dst.). | S3 hijau; fixture judul kalimat → judul pendek/baku. |
| 3. Penomoran ulang | Nomor dari AI ("1.5", "3.2.7") dipertahankan; setelah subbab dipindah/dilipat ada lompatan (2.1 [1,3]). | Nomor final selalu dihitung aplikasi: level 2 dinomori rapat per bab, level 3 dihitung ulang per induk (`_renumber_level3`) setelah pelipatan/penghapusan section kosong (`_drop_empty_generated_sections`). | S2 hijau di fake dan run-nyata. |
| 4. Over-generasi & duplikasi parafrase | Tiap langkah menerima sumber+konteks sama; model menulis ulang kerangka dengan redaksi berbeda (0,55–0,7) yang lolos ambang 0,85. | Prompt: "tulis HANYA subbab langkah ini; jangan menulis ulang pengantar/kerangka; tiap paragraf informasi baru". `_chapter_context` memuat ringkasan 1 kalimat per subbab yang sudah ditulis. Dedup naratif diturunkan ke 0,55 (daftar bernomor memakai dedup nomor + 0,85); merge pelengkap juga memakai dedup 0,55. | K4 hijau; tidak ada subbab > 6 paragraf; kata 2.064–2.825 (K5 tetap hijau). |

Pelengkap deterministik tambahan (muncul dari run-nyata berulang): subbab
tipis/kosong diminta ulang (maks 3 percobaan), sub-subbab 1 paragraf dilipat ke
induknya, dan Kesimpulan/Saran yang tetap kosong diisi 3 butir ringkasan/
rekomendasi umum (non-faktual) agar ekspor tidak diblokir bagian wajib kosong.

### Bukti definisi selesai

- `pytest tests/ -q` → **400 lulus** (399 + tes guard baru).
- `tests/test_e2e_invariants.py` → **SEMUA invariant hijau** untuk 6 variasi model.
- `scripts/e2e_check.py` dijalankan **dua kali berurutan**, keduanya hijau penuh:
  - Run K1: **2.429 kata**, 118 kalimat, **90% hijau**, S1–S7/K1–K4/V1–V3/E1 PASS.
  - Run K2: **2.064 kata**, 97 kalimat, **95% hijau**, semua invariant PASS.
- S1–S3 hijau → struktur dokumen kembali lengkap (ekspektasi skor struktur
  dosen naik dari 82).

Catatan jujur: isi Kesimpulan/Saran cadangan bersifat umum (bukan hasil sintesis
model) dan hanya dipakai bila AI berulang kali gagal menulis bagian itu; isinya
ditandai bukan klaim faktual sehingga tidak menuntut sitasi.

