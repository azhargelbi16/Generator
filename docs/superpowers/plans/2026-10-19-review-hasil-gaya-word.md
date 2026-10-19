# Rencana Implementasi: Review Hasil Gaya Word (dokumen bersih + sunting langsung)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ubah tab "Review Hasil" menjadi tampilan dokumen bersih ala Microsoft Word (tanpa warna status di badan dokumen), sitasi tertulis langsung di kalimat, dan suntingan diketik langsung di dalam dokumen pada kalimat yang diklik.

**Architecture:** Semua perubahan terjadi di `ReportController` (`src/generator/gui/tab_report.py`) bagian pembangunan halaman review dan render dokumen, plus satu fungsi murni baru `display_text` di `src/generator/report.py` untuk teks kalimat beserta label sitasi. Logika status, gerbang ekspor, draf, generate, dan renderer DOCX tidak berubah.

**Tech Stack:** Python + Tkinter (tk.Text, tag, window_create), fungsi sitasi existing `report.labels_for` + `content.compose`.

**Spec:** Desain disetujui di percakapan (brainstorming) 2026-10-19: dokumen bersih seperti Word (Times New Roman 12pt isi, judul dan bab lebih besar tebal, sitasi inline (Sugiyono et al., 2025)), warna status hanya saat kalimat diklik, baris aksi muncul di bawah kalimat aktif (Parafrase AI, Tandai selesai, Pulihkan sitasi), sunting langsung di dokumen, scroll biasa, penghitung progres kecil di atas, gerbang ekspor dan draf tidak berubah.

## Global Constraints

- Teks UI Bahasa Indonesia sederhana untuk pemula; tanpa karakter em dash di semua teks project.
- Tanpa dependensi baru; Tkinter murni.
- Font isi dokumen: Times New Roman 12; judul laporan dan judul bab lebih besar dan tebal (bukan 12pt semua).
- Sitasi inline memakai label APA yang sudah ada: `report.labels_for(sources, cited)` -> `dict[int, str]` berupa "(Keluarga, Tahun)" / "(Org, Tahun)" / "Keluarga dkk., Tahun".
- Tk Text tidak mendukung rata kiri-kanan (justify penuh); dipakai rata kiri sebagai keputusan teknis (keputusan builder, disepakati pengganti justify).
- Status kalimat, `_done`, gerbang ekspor (`report.can_export`), format draf `aktif.json`, dan `renderer.render_report` tidak berubah.
- Platform Windows; uji lewat `pytest` dengan `PYTHONPATH=src` dan smoke GUI nyata (`tests/gui_smoke.py` butuh sesi ber-monitor).

## Review Focus

1. Klik area kosong saat sedang mengetik perbaikan: perubahan yang sudah diketik harus tersimpan (tidak hilang) sebelum baris aksi lepas.
2. Hapus/backspace dengan seleksi yang melintasi batas kalimat: harus diblok agar struktur dokumen tidak rusak.
3. Pembacaan biasa (scroll, seleksi teks untuk disalin) tidak boleh bisa mengubah dokumen; perubahan hanya lewat kalimat aktif.
4. Setelah parafrase atau suntingan, dokumen dibangun ulang: baris aksi lama harus hilang total, tidak ada sisa window tersembunyi.
5. Draf dipulihkan saat aplikasi dibuka: dokumen harus tetap terkunci sampai ada kalimat yang diklik (state disabled/normal konsisten).

---

### Task 1: Fungsi murni `display_text` (teks kalimat + sitasi inline)

**Files:**
- Modify: `src/generator/report.py` (setelah `apply_manual_edit`)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `content.Sentence`, label sitasi `dict[int, str]` dari `report.labels_for`.
- Produces: `display_text(sentence: Sentence, labels: dict[int, str]) -> str`. Aturan: sama dengan `content.compose` per kalimat; hanya untuk kalimat faktual dengan `citation=True` dan `source_ids`; label yang diketahui saja yang dipasang, digabung "; " dalam kurung, ditempatkan sebelum tanda baca akhir.

- [ ] **Step 1: Write the failing test**

```python
from generator.ai.content import Sentence
from generator.report import display_text

def test_display_text_menambah_sitasi_sebelum_tanda_baca():
    s = Sentence("Hal ini membahayakan alam.", "q", [0, 1])
    assert display_text(s, {0: "(Sugiyono, 2025)", 1: "(Wijaya, 2021)"}) == (
        "Hal ini membahayakan alam (Sugiyono, 2025; Wijaya, 2021)."
    )

def test_display_text_tanpa_sumber_dikenal_tanpa_sitasi():
    s = Sentence("Kalimat polos.", "q", [99])
    assert display_text(s, {}) == "Kalimat polos."

def test_display_text_menghormati_flag_citation_dan_nonfactual():
    assert display_text(Sentence("A.", citation=False), {0: "(X, 2020)"}) == "A."
    assert display_text(Sentence("B.", is_factual=False), {0: "(X, 2020)"}) == "B."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'display_text'`

- [ ] **Step 3: Implement `display_text` in `src/generator/report.py`**

Satu kalimat tentang pendekatan: pindahkan logika penyisipan sitasi `_insert_before_final_punctuation` dari `content.compose` ke fungsi murni di `report.py` (compose memangginya juga, atau menduplikasi polanya per kalimat); `display_text` mengambil label untuk `source_ids` yang ada di `labels`, membungkus "(...)" bila belum berkurung, menggabung dengan "; ".

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_report.py src/generator/report.py
git commit -m "feat: display_text menempelkan sitasi inline pada teks kalimat"
```

---

### Task 2: Render dokumen bersih ala Word (font, judul, sitasi, tanpa warna)

**Files:**
- Modify: `src/generator/gui/tab_report.py` (`_build_result_area` tag config dan teks legend/chip, `_render_statuses`, `_perbarui_chip`)
- Test: `tests/gui_smoke.py` (bagian 5)

**Interfaces:**
- Consumes: `display_text` (Task 1), `report.labels_for`, `report.cited_ids`, `record_to_source`.
- Produces: tag dokumen "judul_laporan" (Times New Roman bold 16 center), "judul_bab" (Times New Roman bold 14 center), tag status TIDAK lagi dipasang di badan dokumen; `_doc` font "Times New Roman" 12, background "#ffffff", padx 32 pady 24; teks chip progres baru.

- [ ] **Step 1: Update smoke test yang ada (RED)**

Di `tests/gui_smoke.py` bagian "Kenyamanan baca" ganti menjadi:

```python
# Tampilan dokumen bersih ala Word: TNR 12, tanpa warna status, sitasi inline
isi_dok = report_tab._doc.get("1.0", "end-1c")
assert "\n\n" in isi_dok, "Paragraf tidak dipisah baris kosong"
assert report_tab._doc.cget("font") == "Times New Roman 12", report_tab._doc.cget("font")
merah_cfg = str(report_tab._doc.tag_cget("belum_terverifikasi", "foreground")) if "belum_terverifikasi" in report_tab._doc.tag_names() else ""
semua_tag = set()
for uid in report_tab._sentence_ranges:
    semua_tag.update(report_tab._doc.tag_names(report_tab._sentence_ranges[uid][0]))
assert not ({"terverifikasi", "belum_terverifikasi", "bukan_klaim_faktual"} & semua_tag), semua_tag
assert "Santoso" in isi_dok and "2020" in isi_dok, "Sitasi inline tidak tercetak di dokumen"
assert not hasattr(report_tab, "_tombol_tema"), "Fitur mode gelap harus dihapus"
```

(Adjust nama konstanta status sesuai impor di smoke: `STATUS_VERIFIED` dsb. dari `generator.verification`.)

- [ ] **Step 2: Run smoke to verify it fails**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: FAIL (font masih Cambria, status masih berwarna, belum ada sitasi inline)

- [ ] **Step 3: Implement di `tab_report.py`**

1. `_doc` config: `font=("Times New Roman", 12)`, `background="#ffffff"`, `padx=32`, `pady=24`.
2. Tag "judul_laporan": `font=("Times New Roman", 16, "bold")`, `justify="center"`, `spacing3=10`; tag "judul_bab": `font=("Times New Roman", 14, "bold")`, `justify="center"`, `spacing1=18`, `spacing3=6`.
3. Hapus `tag_config` warna untuk ketiga status dan background "selesai" di dokumen (konstanta warna tetap dipakai di baris aksi, bukan di dokumen).
4. `_render_statuses`: di awal, bila `self._judul_var.get().strip()` terisi, sisipkan judul dengan tag "judul_laporan" lalu "\n\n"; tiap kalimat disisipkan sebagai `display_text(sentence, labels)` dengan tag hanya `uid:<uid>`; bangun `labels` sekali di awal fungsi lewat `report.labels_for([record_to_source(r) for r in self._sources], report.cited_ids(self._statuses))`; jangan pasang tag status maupun "selesai".
5. Legend diganti: "Klik kalimat untuk melihat statusnya dan memperbaikinya langsung di dokumen. Warna hanya muncul pada kalimat yang diklik."
6. `_perbarui_chip` teks utama menjadi: `f"Sudah selesai diverifikasi {selesai} dari {len(dari_ai)} kalimat."` (diikuti ringkasan warna seperti sekarang).

- [ ] **Step 4: Run smoke to verify it passes**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui/tab_report.py tests/gui_smoke.py
git commit -m "feat: dokumen review bersih ala Word dengan sitasi inline"
```

---

### Task 3: Klik kalimat -> sorotan + baris aksi melayang di bawah kalimat

**Files:**
- Modify: `src/generator/gui/tab_report.py` (`_select_sentence`, `_on_doc_click`, method baru `_pasang_baris_aksi`, `_lepas_baris_aksi`, `_deselect`)
- Test: `tests/gui_smoke.py`

**Interfaces:**
- Consumes: `_sentence_ranges`, `_uid_status`, `_STATUS_COLORS`, `_STATUS_LABELS`.
- Produces: `self._aksi_frame: ttk.Frame | None` (window tertanam di dokumen), `self._aksi_tag = "aksi_baris"`, `_deselect()` dipanggil saat klik area kosong, `_lepas_baris_aksi()` menghapus window dan tag "terpilih".

- [ ] **Step 1: Write the failing smoke additions**

```python
# Klik kalimat: baris aksi melayang muncul di dokumen dengan status + tombol
report_tab._select_sentence(belum_uid)
root3.update()
assert report_tab._aksi_frame is not None and report_tab._aksi_frame.winfo_exists(), "Baris aksi tidak muncul"
tombol = [w.cget("text") for w in report_tab._aksi_frame.winfo_children() if isinstance(w, ttk.Button)]
assert "✒ Parafrase" in tombol and "✔ Tandai selesai" in tombol, tombol

# Klik area kosong: baris aksi hilang, sorotan lepas
report_tab._deselect()
root3.update()
assert report_tab._aksi_frame is None, "Baris aksi harus hilang saat lepas"
```

- [ ] **Step 2: Run smoke to verify it fails**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: FAIL (`AttributeError: _aksi_frame`)

- [ ] **Step 3: Implement**

1. `_pasang_baris_aksi(uid)`: bila `self._aksi_frame` sudah ada panggil `_lepas_baris_aksi()`; buat `ttk.Frame` berisi label status berwarna (`_STATUS_COLORS[_uid_status(uid)]`, teks `_STATUS_LABELS[...]` plus "sudah ditandai selesai" bila uid di `_done`), tombol "✒ Parafrase" -> `self._paraphrase`, "✔ Tandai selesai" -> `self._mark_done`, "↩ Pulihkan sitasi" -> `self._restore_citation_action`; tanam dengan `self._doc.window_create(f"{akhir} lineend", window=baris)` dan catat indeks sisipan di `self._aksi_index`.
2. `_lepas_baris_aksi()`: bila ada, `self._doc.delete(self._aksi_index)` (menghapus window tertanam), `self._aksi_frame = None`, `tag_remove("terpilih", "1.0", "end")`.
3. `_select_sentence`: sorotan "terpilih" hanya pada rentang kalimat (bukan seluruh paragraf); panggil `_pasang_baris_aksi(uid)`; isi `self._info` seperti sekarang.
4. `_on_doc_click`: bila uid ditemukan -> `_select_sentence(uid)`; bila tidak -> `_deselect()`.
5. `_deselect()`: `_lepas_baris_aksi()`, `self._selected_uid = None`, `self._selected_para_uids = []`.
6. `_render_statuses` dan `_after_structure_change` memanggil `_lepas_baris_aksi()` di awal (dokumen dibangun ulang; window lama ikut terhapus karena rentang teks dihapus, tapi referensi harus di-None-kan).
7. Bottom bar tetap memuat: "✔ Tandai paragraf selesai", "☑ Tandai semua bukan klaim selesai", "💾 Simpan DOCX"; tombol "✔ Tandai kalimat selesai", "✒ Parafrase", "↩ Pulihkan sitasi" pindah ke baris aksi (hapus dari bottom bar); baris `_edit_entry`/`_edit_var`/`_apply_edit_button` dihapus dari bottom bar (Inline editing menggantikannya di Task 4; hapus referensinya di `_select_sentence`).

- [ ] **Step 4: Run smoke to verify it passes**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: PASS (uji parafrase dan tandai selesai yang ada menyesuaikan: mereka memanggil `_select_sentence` dulu, tombol sekarang di baris aksi tapi method sama)

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui/tab_report.py tests/gui_smoke.py
git commit -m "feat: baris aksi melayang muncul hanya pada kalimat yang diklik"
```

---

### Task 4: Sunting langsung di dokumen (klik kalimat, ketik di tempatnya)

**Files:**
- Modify: `src/generator/gui/tab_report.py` (state dokumen, binding tombol, commit)
- Test: `tests/gui_smoke.py`

**Interfaces:**
- Consumes: `_sentence_ranges[uid]`, `report.apply_manual_edit`, `_swap_sentence`, `_after_structure_change`, `_deselect` (Task 3).
- Produces: `self._active_edit: tuple[str, str, str] | None` = (uid, awal, akhir); `_on_doc_key(event) -> str | None` ("break" bila diluar); `_commit_inline_edit()` membaca teks rentang aktif, menormalkan whitespace (ganti "\n" jadi spasi), bila berubah terapkan `apply_manual_edit`; dokumen `state="normal"` permanen, perubahan dikendalikan binding.

- [ ] **Step 1: Update smoke uji sunting lama menjadi inline (RED)**

Ganti blok "Sunting manual lewat kotak sunting..." menjadi:

```python
# Sunting langsung di dokumen: ketik di rentang kalimat, commit saat lepas
report_tab._select_sentence(belum_uid)
awal, akhir = report_tab._sentence_ranges[belum_uid]
report_tab._doc.delete(awal, akhir)
report_tab._doc.insert(awal, "Kalimat diedit langsung di dokumen.")
report_tab._commit_inline_edit()
edited = report_tab._sentence_by_uid(belum_uid)
assert edited.origin == "manual", "Suntingan langsung harus menandai kalimat manual"
assert edited.text == "Kalimat diedit langsung di dokumen.", edited.text
report_tab._select_sentence(belum_uid)
report_tab._mark_done()
```

Tambahkan uji kunci terkunci:

```python
# Ketikan di luar kalimat aktif ditolak; di dalam diterima
report_tab._select_sentence(para_uid)
awal, akhir = report_tab._sentence_ranges[para_uid]
kelass = tk.Event(); kelass.keysym = "a"; kelass.state = 0
report_tab._doc.mark_set("insert", f"{awal} linestart")
assert report_tab._on_doc_key(kelas) == "break", "Ketikan di luar kalimat aktif harus diblok"
report_tab._doc.mark_set("insert", awal)
assert report_tab._on_doc_key(kelas) is None, "Ketikan di dalam kalimat aktif harus boleh"
report_tab._deselect()
```

- [ ] **Step 2: Run smoke to verify it fails**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: FAIL (`AttributeError: _commit_inline_edit`)

- [ ] **Step 3: Implement**

1. `_doc.config(state="normal")` permanen; hapus semua `state="disabled"`/`state="normal"` sekitar render (render tetap aman karena perubahan dikendalikan binding, bukan state).
2. Binding di `_build_result_area`: `self._doc.bind("<KeyPress>", self._on_doc_key)`; `self._doc.bind("<Button-1>", self._on_doc_click)` tetap.
3. `_on_doc_key(event)`: bila `self._active_edit` None -> return "break"; bila ada seleksi yang melintasi batas rentang aktif -> "break"; bila "insert" di luar rentang -> "break"; selain itu None (boleh). (Keysym Escape atau tombol navigasi boleh dilewati lewat whitelist: Return/BackSpace/Delete/Left/Right/Up/Down/Home/End tidak diblok bila di dalam rentang.)
4. `_select_sentence(uid)`: set `self._active_edit = (uid, awal, akhir)` dari `_sentence_ranges`.
5. `_commit_inline_edit()`: bila `self._active_edit` None return; baca teks rentang; normalkan `" ".join(text.split())`; bila kosong -> kembalikan teks asli kalimat (jangan hapus kalimat lewat suntingan kosong); bila berubah -> `apply_manual_edit` + `_swap_sentence` + `_after_structure_change("Kalimat disunting langsung di dokumen.")`; `self._active_edit = None`. Perhatian: `_after_structure_change` membangun ulang dokumen sehingga `_select_sentence` berikutnya memakai rentang baru.
6. `_deselect()`: panggil `_commit_inline_edit()` DULUAN (simpan ketikan terakhir), baru `_lepas_baris_aksi()` dan reset pilihan.
7. `_on_doc_click` urutannya: bila klik kalimat lain sementara `active_edit` ada -> commit dulu (otomatis lewat `_select_sentence`? pastikan `_select_sentence` memanggil `_commit_inline_edit()` bila ada active_edit sebelum pindah), lalu pilih kalimat baru. Bila klik kosong -> `_deselect()` (yang commit lalu lepas).

- [ ] **Step 4: Run smoke to verify it passes**

Run: `pytest tests/test_gui_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generator/gui/tab_report.py tests/gui_smoke.py
git commit -m "feat: sunting kalimat langsung di dokumen review"
```

---

### Task 5: Dokumentasi + verifikasi akhir

**Files:**
- Modify: `README.md` (bagian cara review), `.superpowers/sdd/2026-10-18-generator-laporan.md/progress.md`

**Interfaces:**
- Consumes: semua task sebelumnya.

- [ ] **Step 1: Update README**

Ganti penjelasan tab Review Hasil: dokumen bersih ala Word (Times New Roman 12, judul/bab lebih besar), sitasi inline, klik kalimat untuk melihat status dan memperbaiki langsung di dokumen, tombol di baris kecil di bawah kalimat aktif, penghitung progres di atas, gerbang ekspor tetap.

- [ ] **Step 2: Catat ruling di progress.md**

Satu paragraf: tanggal, permintaan user (tampilan Word + sitasi inline + sunting langsung + parafrase di tempat), keputusan warna hanya saat diklik, font Times New Roman 12 (heading lebih besar), keterbatasan justify Tk.

- [ ] **Step 3: Full suite**

Run: `pytest -q`
Expected: semua passed (132+)

- [ ] **Step 4: Commit**

```bash
git add README.md .superpowers/sdd/2026-10-18-generator-laporan.md/progress.md
git commit -m "docs: panduan review hasil gaya Word"
```

---

## Self-Review Notes

- Spec coverage: tampilan Word (Task 2), sitasi inline (Task 1+2), warna hanya saat klik (Task 2+3), baris aksi di bawah kalimat (Task 3), sunting langsung + parafrase di tempat (Task 3+4), scroll biasa (tak ada perubahan; dokumen Text sudah scroll), penghitung progres (Task 2 chip), gerbang ekspor + draf tak berubah (tak ada task; smoke bagian 6-7 memverifikasi tetap hijau).
- Konsistensi: `display_text` dipakai Task 2; `_aksi_frame`/`_deselect`/`_commit_inline_edit` dipakai lintas Task 3-4; konstanta status dari `generator.verification`.
- Uji parafrase existing di smoke tetap memanggil `report_tab._paraphrase()` setelah `_select_sentence`, method tidak berubah (hanya lokasi tombol), jadi tak perlu ubah uji parafrase selain pemilihan kalimat sebelumnya.
