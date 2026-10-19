"""Tab Buat Laporan bagian 1: sumber, fallback OCR/manual, koreksi metadata (12, Task 16).

Semua operasi lama (baca PDF/OCR, ambil web, panggilan AI) berjalan lewat
`worker.run_in_thread` supaya jendela tidak membeku. Kode tidak pernah menebak
pemisahan nama penulis; nilai dari AI hanyalah usulan yang diedit user di
formulir koreksi.
"""

from __future__ import annotations

import logging
import re
import time
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import config, database, drafts, paths, report
from ..ai import bibliography, content
from ..ai.citation import Author, Source
from ..ai.client import AIClient
from ..document import renderer
from ..document.template import TemplateError, validate_template
from ..sources import pdf_reader, web_reader
from ..verification import (
    STATUS_NON_FACTUAL,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    verify_sections,
)
from .worker import run_in_thread

from .feedback import Toast, ToolTip

_LOG = logging.getLogger(__name__)

_DRAFT_ID = "aktif"

_AUTHOR_FIELDS = ("family", "given", "is_org", "abbrev")

_STATUS_LABELS = {
    STATUS_VERIFIED: "terverifikasi",
    STATUS_UNVERIFIED: "belum terverifikasi",
    STATUS_NON_FACTUAL: "bukan klaim faktual",
}
_STATUS_COLORS = {
    STATUS_VERIFIED: "#1a7f37",
    STATUS_UNVERIFIED: "#b42318",
    STATUS_NON_FACTUAL: "#667085",
}

# Tombol navigasi yang boleh jalan walau kursor di luar kalimat aktif.
_NAV_KEYS = {
    "Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
    "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R",
}


def normalize_metadata(doc: dict[str, str]) -> dict[str, str]:
    """Samakan kunci metadata dokumen dengan yang dibaca `merge_metadata`.

    Pembaca PDF dan web memancarkan `date` (sering berupa tanggal lengkap atau
    format internal PDF seperti D:20231019120000), sedangkan penggabungan
    mengharapkan `year`; ambil 4 digit yang masuk akal sebagai tahun bila ada,
    tanpa menghapus nilai asli.
    """
    result = dict(doc or {})
    date = result.get("date")
    if date and not result.get("year"):
        kandidat = re.findall(r"\d{4}", str(date))
        pilihan = next(
            (k for k in kandidat if 1900 <= int(k) <= 2100),
            kandidat[0] if kandidat else None,
        )
        result["year"] = pilihan if pilihan else str(date)
    return result


def source_to_record(source: Source, text: str, kind: str) -> dict:
    """Ubah hasil AI menjadi dict draf; penulis disalin apa adanya sebagai usulan."""
    return {
        "kind": kind,
        "title": source.title,
        "year": source.year,
        "container": source.container,
        "doi": source.doi,
        "url": source.url,
        "authors": [
            {
                "family": author.family,
                "given": author.given,
                "is_org": bool(author.is_org),
                "abbrev": author.abbrev,
            }
            for author in source.authors
        ],
        "text": text,
    }


def record_to_source(record: dict) -> Source:
    """Bangun ulang `Source` dari dict draf untuk pemakaian modul AI."""
    return Source(
        authors=[
            Author(
                author.get("family", ""),
                author.get("given", ""),
                bool(author.get("is_org", False)),
                author.get("abbrev", ""),
            )
            for author in record.get("authors", [])
        ],
        year=record.get("year", ""),
        title=record.get("title", ""),
        container=record.get("container", ""),
        doi=record.get("doi", ""),
        url=record.get("url", ""),
    )


class ReportController:
    """Pengendali laporan: halaman "Laporan" (sumber+pengaturan) dan "Review Hasil".

    Bukan widget; semua state milik objek ini, widget dibangun ke dua halaman
    notebook yang diberikan. `self._widget` dipakai untuk `after` pekerja latar.
    """

    def __init__(self, setup_page, review_page, notebook, db: database.Database):
        self._widget = setup_page
        self._notebook = notebook
        self._review_page = review_page
        self._db = db
        self._sources: list[dict] = []
        self._sections = []
        self._statuses = []
        self._done: set[str] = set()
        self._templates = db.list_template()
        self._dosen_list = db.list_dosen()
        self._matkul_list = db.list_mata_kuliah()
        self._logo_list = db.list_logo()
        self._template = None
        self._unknown_markers: list[str] = []
        self._generate_tick = None

        # Halaman Laporan: dua kolom (sumber | pengaturan).
        atas = ttk.Frame(setup_page, padding=(8, 8, 8, 4))
        atas.pack(side="top", fill="both", expand=True)
        left = ttk.Frame(atas)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(atas)
        right.pack(side="left", fill="both", expand=True)

        self._build_source_area(left)
        self._build_setup_area(right)
        self._build_result_area(review_page)

        self._widget.bind_all("<Control-Return>", lambda _e: self._generate())

        self._restore_draft()

    # ------------------------------------------------------------------ UI

    def _build_source_area(self, parent) -> None:
        list_frame = ttk.LabelFrame(parent, text="Sumber")
        list_frame.pack(side="top", fill="both", expand=True)
        self._source_listbox = tk.Listbox(list_frame, height=14, exportselection=False)
        self._source_listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self._source_listbox.bind("<<ListboxSelect>>", lambda _event: self._on_source_select())
        scrollbar = ttk.Scrollbar(list_frame, command=self._source_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._source_listbox.config(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(parent)
        buttons.pack(side="bottom", fill="x")
        btn_pdf = ttk.Button(buttons, text="📄 Tambah PDF...", command=self._add_pdf)
        btn_pdf.pack(side="left", padx=4)
        btn_link = ttk.Button(buttons, text="🔗 Tambah Link...", command=self._add_link)
        btn_link.pack(side="left", padx=4)
        btn_teks = ttk.Button(buttons, text="✍️ Tempel Teks Manual...", command=self._paste_manual)
        btn_teks.pack(side="left", padx=4)
        self._tombol_hapus = ttk.Button(
            buttons, text="🗑 Hapus", command=self._hapus_source, style="Danger.TButton"
        )
        self._tombol_hapus.pack(side="left", padx=4)
        ToolTip(btn_pdf, "Pilih berkas PDF sumber; teksnya dibaca lalu dianalisis metadata-nya.")
        ToolTip(btn_link, "Tempel URL artikel/web; teks halaman diambil lalu dianalisis metadata-nya.")
        ToolTip(btn_teks, "Ketik atau tempel teks sumber langsung tanpa berkas.")
        ToolTip(self._tombol_hapus, "Hapus sumber terpilih beserta sitasi yang merujuknya.")
        self._status = ttk.Label(buttons, text="")
        self._status.pack(side="left", padx=12)

        form = ttk.LabelFrame(parent, text="Koreksi metadata sumber terpilih")
        form.pack(side="bottom", fill="x", pady=(8, 0))
        self._meta_vars = {
            key: tk.StringVar() for key in ("year", "title", "container", "doi", "url")
        }
        labels = {
            "year": "Tahun",
            "title": "Judul",
            "container": "Publikasi",
            "doi": "DOI",
            "url": "URL",
        }
        for row, key in enumerate(self._meta_vars):
            ttk.Label(form, text=labels[key]).grid(row=row, column=0, sticky="w", padx=6, pady=2)
            ttk.Entry(form, textvariable=self._meta_vars[key], width=46).grid(
                row=row, column=1, columnspan=3, sticky="we", pady=2
            )
        self._authors_frame = ttk.Frame(form)
        self._authors_frame.grid(row=len(self._meta_vars), column=0, columnspan=4, sticky="we")
        btn_terapkan = ttk.Button(form, text="✔ Terapkan Koreksi", command=self._apply_corrections)
        btn_terapkan.grid(row=len(self._meta_vars) + 1, column=0, columnspan=4, sticky="w", padx=6, pady=6)
        ToolTip(btn_terapkan, "Simpan perbaikan judul, tahun, penulis, dan tautan ke draf.")

    def _build_setup_area(self, parent) -> None:
        frame = ttk.LabelFrame(parent, text="Pengaturan laporan")
        frame.pack(side="top", fill="both", expand=True)

        profil = self._db.get_profil()
        profil_text = (
            f"Profil: {profil.nama} ({profil.nim}), {profil.prodi}"
            if profil
            else "Profil belum diisi di tab Data."
        )
        ttk.Label(frame, text=profil_text).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        self._template_var = tk.StringVar()
        ttk.Label(frame, text="Template").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self._template_combo = ttk.Combobox(
            frame, textvariable=self._template_var, values=[t.nama for t in self._templates],
            state="readonly", width=36,
        )
        self._template_combo.grid(row=1, column=1, sticky="w", pady=4)
        self._template_combo.bind("<<ComboboxSelected>>", self._on_template_selected)

        self._picker_vars: dict[str, tk.StringVar] = {}
        rows = [
            ("dosen", "Dosen pembimbing", [d.nama for d in self._dosen_list]),
            ("matkul", "Mata kuliah", [m.nama for m in self._matkul_list]),
            ("logo", "Logo", [l.nama for l in self._logo_list]),
        ]
        for row, (key, label, values) in enumerate(rows, start=2):
            var = tk.StringVar()
            self._picker_vars[key] = var
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            combo = ttk.Combobox(frame, textvariable=var, values=values, state="readonly", width=36)
            combo.grid(row=row, column=1, sticky="w", pady=4)
            combo.bind("<<ComboboxSelected>>", lambda _event: self._save_draft())

        ttk.Label(frame, text="Judul laporan").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        self._judul_var = tk.StringVar()
        judul_entry = ttk.Entry(frame, textvariable=self._judul_var, width=40)
        judul_entry.grid(row=5, column=1, sticky="we", pady=4)
        judul_entry.bind("<KeyRelease>", lambda _event: self._save_draft())

        ttk.Label(frame, text="Outline bab (satu baris satu bab)").grid(
            row=6, column=0, sticky="w", padx=6, pady=4
        )
        self._outline_text = tk.Text(frame, width=44, height=12, wrap="word")
        self._outline_text.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=6, pady=4)
        self._outline_text.bind("<KeyRelease>", lambda _event: self._on_outline_edited())

        self._suggest_button = ttk.Button(
            frame, text="💡 Usulkan Outline", command=self._suggest_outline
        )
        self._suggest_button.grid(row=8, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        self._generate_button = ttk.Button(
            frame,
            text="🚀 Generate isi laporan",
            command=self._generate,
            style="Accent.TButton",
        )
        self._generate_button.grid(row=9, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 8))
        ToolTip(self._generate_button, "Menyusun isi laporan dari sumber dan outline Anda (Ctrl+Enter).")
        self._progres = ttk.Progressbar(frame, mode="indeterminate", length=280)
        self._progres.grid(row=10, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 8))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)
        self._update_outline_button()

    def _build_result_area(self, parent) -> None:
        result = ttk.LabelFrame(parent, text="Hasil generate (dokumen baca)")
        result.pack(side="top", fill="both", expand=True, pady=(8, 0))

        legend = ttk.Label(
            result,
            text="Klik kalimat untuk melihat statusnya dan memperbaikinya langsung di dokumen. "
            "Warna hanya muncul pada kalimat yang diklik.",
            foreground="#666666",
        )
        legend.pack(side="top", anchor="w", padx=6)

        self._chip_status = ttk.Label(result, text="Belum ada isi.", foreground="#666666")
        self._chip_status.pack(side="top", anchor="w", padx=6)

        # Baris tombol dipasang lebih dulu agar tidak pernah terdorong keluar
        # layar saat ruang vertikal sempit (ditemukan saat uji manual user).
        actions = ttk.Frame(result)
        actions.pack(side="bottom", fill="x")
        ttk.Button(
            actions, text="✔ Tandai paragraf selesai", command=self._mark_paragraph_done
        ).pack(side="left", padx=4)
        ttk.Button(
            actions, text="✔ Tandai kalimat selesai", command=self._mark_done
        ).pack(side="left", padx=4)
        ttk.Button(
            actions, text="☑ Tandai semua bukan klaim selesai", command=self._mark_all_nonfactual_done
        ).pack(side="left", padx=4)
        btn_simpan = ttk.Button(
            actions, text="💾 Simpan DOCX", command=self._save_docx, style="Accent.TButton"
        )
        btn_simpan.pack(side="left", padx=4)
        ToolTip(btn_simpan, "Ekspor laporan ke DOCX; tersedia setelah semua kalimat ditandai.")

        self._info = ttk.Label(
            result,
            text="Klik kalimat untuk memilihnya; ketik langsung pada kalimat yang diklik untuk "
            "memperbaikinya, lalu klik di luar kalimat untuk menyimpan.",
            foreground="#666666",
            wraplength=560,
            justify="left",
        )
        self._info.pack(side="bottom", fill="x")

        container = ttk.Frame(result)
        container.pack(side="top", fill="both", expand=True, padx=4, pady=(2, 4))
        container.columnconfigure(0, weight=1)
        # Kolom baca sempit dan di tengah agar baris tidak terlalu panjang
        # sehingga mata mudah berpindah baris (baris panjang melelahkan).
        kolom = ttk.Frame(container)
        kolom.grid(row=0, column=0, sticky="ns")
        kolom.rowconfigure(0, weight=1)
        self._doc = tk.Text(
            kolom,
            wrap="word",
            width=92,
            state="normal",
            font=("Times New Roman", 12),
            spacing1=2,
            padx=32,
            pady=24,
            relief="flat",
            background="#ffffff",
        )
        scrollbar = ttk.Scrollbar(kolom, orient="vertical", command=self._doc.yview)
        self._doc.configure(yscrollcommand=scrollbar.set)
        self._doc.grid(row=0, column=0, sticky="ns")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._doc.tag_config(
            "judul_laporan",
            font=("Times New Roman", 16, "bold"),
            justify="center",
            spacing3=10,
        )
        self._doc.tag_config(
            "judul_bab",
            font=("Times New Roman", 14, "bold"),
            justify="center",
            spacing1=18,
            spacing3=6,
        )
        self._doc.tag_config("terpilih", background="#fff3bf")
        self._doc.bind("<Button-1>", self._on_doc_click)
        self._doc.bind("<KeyPress>", self._on_doc_key)

        self._selected_uid: str | None = None
        self._selected_para_uids: list[str] = []
        self._sentence_ranges: dict[str, tuple[str, str]] = {}
        self._paragraph_ranges: list[tuple[str, str, list[str]]] = []
        self._aksi_frame = None
        self._aksi_index: str | None = None
        self._render_statuses()

    def _render_statuses(self) -> None:
        """Bangun ulang dokumen baca; pemetaan rentang teks ke kalimat satu banding satu."""
        posisi = self._doc.yview()
        self._selected_uid = None
        self._selected_para_uids = []
        self._aksi_frame = None
        self._aksi_index = None
        self._active_edit: tuple[str, str, str, str] | None = None
        self._doc.delete("1.0", "end")
        self._sentence_ranges = {}
        self._paragraph_ranges = []
        labels = report.labels_for(
            [record_to_source(r) for r in self._sources],
            report.cited_ids(self._statuses),
        )
        judul = self._judul_var.get().strip()
        if judul:
            self._doc.insert("end", judul + "\n\n", ("judul_laporan",))
        for section in self._sections:
            self._doc.insert("end", f"{section.title}\n", ("judul_bab",))
            for paragraph in section.paragraphs:
                awal_para = akhir_para = None
                uids_para: list[str] = []
                for sentence in paragraph.sentences:
                    awal = self._doc.index("end-1c")
                    self._doc.insert(
                        "end", report.display_text(sentence, labels), (f"uid:{sentence.uid}",)
                    )
                    akhir = self._doc.index("end-1c")
                    self._sentence_ranges[sentence.uid] = (awal, akhir)
                    if awal_para is None:
                        awal_para = awal
                    akhir_para = akhir
                    uids_para.append(sentence.uid)
                    self._doc.insert("end", " ")
                if awal_para is not None:
                    self._paragraph_ranges.append((awal_para, akhir_para, uids_para))
                self._doc.insert("end", "\n\n")
            # Pemisah antarbab hanya satu baris kosong; judul bab sudah
            # diberi jarak atas lewat gaya judul_bab.
        if not self._sentence_ranges:
            self._doc.insert(
                "end",
                "Belum ada isi. Isi outline, tambahkan sumber, lalu klik Generate isi laporan.",
                ("judul_bab",),
            )
        self._perbarui_chip()
        self._doc.yview_moveto(posisi[0])

    def _perbarui_chip(self) -> None:
        """Ringkas jumlah status kalimat AI dan yang sudah ditandai selesai."""
        dari_ai = [item for item in self._statuses if item.sentence.origin == "ai"]
        if not dari_ai:
            self._chip_status.config(text="Belum ada isi.")
            return
        hijau = sum(1 for item in dari_ai if item.status == STATUS_VERIFIED)
        merah = sum(1 for item in dari_ai if item.status == STATUS_UNVERIFIED)
        abu = sum(1 for item in dari_ai if item.status == STATUS_NON_FACTUAL)
        selesai = len(self._done & set(self._sentence_ranges))
        self._chip_status.config(
            text=(
                f"Sudah selesai diverifikasi {selesai} dari {len(dari_ai)} kalimat. "
                f"Terverifikasi {hijau}, belum terverifikasi {merah}, bukan klaim {abu}."
            )
        )

    def _status_by_uid(self) -> dict[str, str]:
        return {item.sentence.uid: item.status for item in self._statuses}

    def _uid_status(self, uid: str) -> str:
        return self._status_by_uid().get(uid, STATUS_UNVERIFIED)

    def _sentence_by_uid(self, uid: str):
        for sentence in self._iter_sentences():
            if sentence.uid == uid:
                return sentence
        return None

    def _section_title_of(self, uid: str) -> str:
        for section in self._sections:
            if any(s.uid == uid for p in section.paragraphs for s in p.sentences):
                return section.title
        return ""

    def _uid_at(self, index: str) -> str | None:
        for name in self._doc.tag_names(index):
            if name.startswith("uid:"):
                return name[4:]
        return None

    def _on_doc_click(self, event) -> None:
        uid = self._uid_at(self._doc.index(f"@{event.x},{event.y}"))
        if uid:
            self._select_sentence(uid)
        else:
            self._deselect()

    def _on_doc_key(self, event) -> str | None:
        """Blok ketikan di luar kalimat aktif; dokumen hanya berubah lewat kalimat terpilih."""
        keysym = getattr(event, "keysym", "")
        if getattr(event, "state", 0) & 0x4 and keysym.lower() in ("c", "a"):
            return None  # salin / pilih semua tetap boleh saat membaca
        if self._active_edit is None:
            return "break"
        _uid, awal, akhir, _teks_asli = self._active_edit
        try:
            if self._doc.tag_ranges("sel"):
                if self._doc.compare("sel.first", "<", awal) or self._doc.compare(
                    "sel.last", ">", akhir
                ):
                    return "break"
        except tk.TclError:
            pass
        if keysym in _NAV_KEYS:
            return None
        try:
            insert = self._doc.index("insert")
        except tk.TclError:
            return "break"
        if self._doc.compare(insert, "<", awal) or self._doc.compare(insert, ">", akhir):
            return "break"
        return None

    def _pasang_baris_aksi(self, uid: str) -> None:
        """Baris kecil di bawah kalimat aktif: status berwarna + aksi kalimat."""
        if self._aksi_frame is not None:
            self._lepas_baris_aksi()
        status = self._uid_status(uid)
        baris = ttk.Frame(self._doc)
        label_status = _STATUS_LABELS[status]
        if uid in self._done:
            label_status += " · sudah ditandai selesai"
        ttk.Label(baris, text="● " + label_status, foreground=_STATUS_COLORS[status]).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(baris, text="✒ Parafrase", command=self._paraphrase).pack(side="left", padx=2)
        ttk.Button(baris, text="✔ Tandai selesai", command=self._mark_done).pack(side="left", padx=2)
        ttk.Button(baris, text="↩ Pulihkan sitasi", command=self._restore_citation_action).pack(
            side="left", padx=2
        )
        self._aksi_frame = baris
        self._aksi_index = self._doc.index(f"{self._sentence_ranges[uid][1]} lineend")
        self._doc.window_create(self._aksi_index, window=baris)

    def _lepas_baris_aksi(self) -> None:
        if self._aksi_frame is not None:
            try:
                self._doc.delete(self._aksi_index)
            except tk.TclError:
                pass
            self._aksi_frame = None
            self._aksi_index = None
        self._doc.tag_remove("terpilih", "1.0", "end")

    def _deselect(self) -> None:
        self._commit_inline_edit()
        self._lepas_baris_aksi()
        self._selected_uid = None
        self._selected_para_uids = []

    def _select_sentence(self, uid: str) -> None:
        if self._active_edit is not None and self._active_edit[0] != uid:
            self._commit_inline_edit()
        self._lepas_baris_aksi()
        self._selected_uid = uid
        for awal, akhir, uids in self._paragraph_ranges:
            if uid in uids:
                self._selected_para_uids = uids
                break
        self._doc.tag_add("terpilih", *self._sentence_ranges[uid])
        rentang = self._sentence_ranges[uid]
        self._active_edit = (uid, rentang[0], rentang[1], self._doc.get(*rentang))
        self._pasang_baris_aksi(uid)
        status = self._uid_status(uid)
        selesai = "sudah ditandai selesai" if uid in self._done else "belum ditandai selesai"
        sudah = sum(1 for u in self._selected_para_uids if u in self._done)
        self._info.config(
            text=f"[{self._section_title_of(uid)}] paragraf ini {sudah}/{len(self._selected_para_uids)} "
            f"kalimat selesai; kalimat yang diklik {status} ({selesai})."
        )

    def _commit_inline_edit(self) -> None:
        """Simpan ketikan di rentang kalimat aktif sebagai suntingan manual; kosong diabaikan."""
        if self._active_edit is None:
            return
        uid, awal, akhir, teks_asli = self._active_edit
        self._active_edit = None
        sentence = self._sentence_by_uid(uid)
        if sentence is None:
            return
        teks_baru = " ".join(self._doc.get(awal, akhir).split())
        if teks_baru and teks_baru != teks_asli:
            self._swap_sentence(uid, [report.apply_manual_edit(sentence, teks_baru)])
            self._after_structure_change(
                "Kalimat disunting langsung di dokumen; berstatus belum terverifikasi "
                "sampai ditandai selesai."
            )
        else:
            self._render_statuses()

    def _paragraph_range_of(self, uids: list[str]):
        for awal, akhir, daftar in self._paragraph_ranges:
            if daftar == uids:
                return (awal, akhir)
        return None

    def _mark_paragraph_done(self) -> None:
        if not self._selected_para_uids:
            self._info.config(text="Klik dulu salah satu kalimat pada paragraf yang ingin ditandai.")
            return
        self._done.update(self._selected_para_uids)
        rentang = self._paragraph_range_of(self._selected_para_uids)
        if rentang:
            self._doc.tag_add("selesai", rentang[0], rentang[1])
        self._save_draft()
        self._info.config(
            text=f"Paragraf ditandai selesai ({len(self._selected_para_uids)} kalimat)."
        )

    def _iter_sentences(self):
        for section in self._sections:
            for paragraph in section.paragraphs:
                yield from paragraph.sentences

    def _swap_sentence(self, uid: str, replacements: list) -> bool:
        """Ganti satu kalimat ber-uid dengan daftar kalimat baru di paragraf asalnya."""
        for section in self._sections:
            for paragraph in section.paragraphs:
                for index, sentence in enumerate(paragraph.sentences):
                    if sentence.uid == uid:
                        paragraph.sentences[index : index + 1] = replacements
                        return True
        return False

    def _after_structure_change(self, message: str) -> None:
        self._reverify()
        self._render_statuses()
        self._save_draft()
        self._status.config(text=message)

    def _mark_done(self) -> None:
        if self._selected_uid is None:
            self._info.config(text="Klik dulu kalimat yang ingin ditandai selesai.")
            return
        uid = self._selected_uid
        self._done.add(uid)
        awal, akhir = self._sentence_ranges[uid]
        self._doc.tag_add("selesai", awal, akhir)
        self._save_draft()
        self._info.config(text="Kalimat ditandai selesai.")

    def _mark_all_nonfactual_done(self) -> None:
        uids = report.non_factual_uids(self._statuses)
        self._done.update(uids)
        for uid in uids:
            rentang = self._sentence_ranges.get(uid)
            if rentang:
                self._doc.tag_add("selesai", rentang[0], rentang[1])
        self._save_draft()
        self._status.config(text=f"{len(uids)} kalimat bukan klaim faktual ditandai selesai.")

    def _restore_citation_action(self) -> None:
        if self._selected_uid is None:
            self._info.config(text="Klik dulu kalimat yang sitasinya ingin dipulihkan.")
            return
        sentence = self._sentence_by_uid(self._selected_uid)
        if sentence is None:
            self._info.config(text="Kalimat tidak ditemukan lagi.")
            return
        if sentence.citation:
            self._info.config(text="Sitasi kalimat ini sudah aktif.")
            return
        new_sentence = report.restore_citation(sentence)
        self._swap_sentence(sentence.uid, [new_sentence])
        self._after_structure_change("Sitasi kalimat dipulihkan.")

    def _paraphrase(self) -> None:
        if self._selected_uid is None:
            self._info.config(text="Klik dulu kalimat yang ingin diparafrase.")
            return
        sentence = self._sentence_by_uid(self._selected_uid)
        if sentence is None:
            self._info.config(text="Kalimat tidak ditemukan lagi.")
            return
        client = self._ai_client()
        sources = [record_to_source(record) for record in self._sources]
        texts = [record.get("text", "") for record in self._sources]
        self._status.config(text="Memparafrase kalimat terpilih...")

        def work():
            return content.paraphrase(content.Paragraph([sentence]), sources, texts, client)

        def on_success(paragraph) -> None:
            new_sentences = list(paragraph.sentences)
            if not new_sentences:
                messagebox.showwarning(
                    "Parafrase gagal", "AI tidak mengembalikan kalimat baru; kalimat tidak diubah."
                )
                self._status.config(text="Parafrase tidak mengubah apa pun.")
                return
            self._swap_sentence(sentence.uid, new_sentences)
            self._after_structure_change(
                "Parafrase selesai; kalimat baru dihitung ulang statusnya."
            )

        def on_error(error) -> None:
            messagebox.showerror("Parafrase gagal", str(error))
            self._status.config(text="Parafrase gagal.")

        run_in_thread(self._widget, work, on_success=on_success, on_error=on_error)

    # -------------------------------------------------------------- sumber

    def _refresh_source_list(self) -> None:
        self._source_listbox.delete(0, "end")
        for index, record in enumerate(self._sources, start=1):
            year = f" ({record['year']})" if record.get("year") else ""
            self._source_listbox.insert("end", f"{index}. {record.get('title') or 'tanpa judul'}{year}")

    def _selected_index(self) -> int | None:
        selection = self._source_listbox.curselection()
        return selection[0] if selection else None

    def _hapus_source(self) -> None:
        """Buang sumber terpilih; sitasi yang merujuknya dilepas, indeks lain digeser."""
        index = self._selected_index()
        if index is None:
            self._status.config(text="Pilih dulu sumbernya di daftar.")
            return
        judul = self._sources[index].get("title") or "tanpa judul"
        if not messagebox.askyesno(
            "Hapus sumber",
            f"Hapus sumber \"{judul}\"?\n\nSitasi yang merujuk sumber ini akan dilepas.",
        ):
            return
        del self._sources[index]
        for sentence in self._iter_sentences():
            sentence.source_ids = [
                i - 1 if i > index else i for i in sentence.source_ids if i != index
            ]
            if not sentence.source_ids:
                sentence.citation = False
        self._refresh_source_list()
        self._after_structure_change("Sumber dihapus; sitasi yang merujuknya dilepas.")

    def _on_source_select(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        record = self._sources[index]
        for key in self._meta_vars:
            self._meta_vars[key].set(record.get(key, ""))
        for child in self._authors_frame.winfo_children():
            child.destroy()
        self._author_vars: list[dict] = []
        for number, author in enumerate(record.get("authors", []), start=1):
            ttk.Label(
                self._authors_frame, text=f"Penulis {number}"
            ).grid(row=number - 1, column=0, sticky="w", padx=2, pady=2)
            family = tk.StringVar(value=author.get("family", ""))
            given = tk.StringVar(value=author.get("given", ""))
            abbrev = tk.StringVar(value=author.get("abbrev", ""))
            is_org = tk.BooleanVar(value=bool(author.get("is_org", False)))
            ttk.Label(self._authors_frame, text="keluarga").grid(
                row=number - 1, column=1, sticky="e")
            ttk.Entry(self._authors_frame, textvariable=family, width=16).grid(
                row=number - 1, column=2, padx=2)
            ttk.Label(self._authors_frame, text="depan").grid(
                row=number - 1, column=3, sticky="e")
            ttk.Entry(self._authors_frame, textvariable=given, width=16).grid(
                row=number - 1, column=4, padx=2)
            ttk.Checkbutton(self._authors_frame, text="organisasi", variable=is_org).grid(
                row=number - 1, column=5, padx=2)
            ttk.Label(self._authors_frame, text="singkatan").grid(
                row=number - 1, column=7, sticky="e")
            ttk.Entry(self._authors_frame, textvariable=abbrev, width=10).grid(
                row=number - 1, column=8, padx=2)
            self._author_vars.append(
                {"family": family, "given": given, "is_org": is_org, "abbrev": abbrev}
            )
        if not self._author_vars:
            ttk.Label(
                self._authors_frame, text="Sumber ini belum punya penulis; tambahkan lewat koreksi."
            ).grid(row=0, column=0, sticky="w")
            self._author_vars = [
                {
                    "family": tk.StringVar(),
                    "given": tk.StringVar(),
                    "is_org": tk.BooleanVar(value=False),
                    "abbrev": tk.StringVar(),
                }
            ]

    def _apply_corrections(self) -> None:
        index = self._selected_index()
        if index is None:
            self._status.config(text="Pilih sumber di daftar lebih dulu.")
            return
        record = self._sources[index]
        for key in self._meta_vars:
            record[key] = self._meta_vars[key].get().strip()
        record["authors"] = [
            {
                "family": var["family"].get().strip(),
                "given": var["given"].get().strip(),
                "is_org": bool(var["is_org"].get()),
                "abbrev": var["abbrev"].get().strip(),
            }
            for var in self._author_vars
        ]
        record["authors"] = [
            author for author in record["authors"] if author["family"] or author["given"]
        ]
        self._refresh_source_list()
        self._save_draft()
        self._status.config(text="Koreksi metadata diterapkan.")
        Toast(self._widget, "Koreksi diterapkan")

    def _ai_client(self) -> AIClient:
        return AIClient(config.load_config(paths.CONFIG_PATH))

    def _append_source(self, record: dict) -> None:
        self._sources.append(record)
        self._refresh_source_list()
        self._source_listbox.selection_clear(0, "end")
        self._source_listbox.selection_set(len(self._sources) - 1)
        self._on_source_select()
        self._save_draft()
        self._status.config(text=f"Sumber {record['kind']} ditambahkan ({len(self._sources)} total).")
        Toast(self._widget, f"Sumber {record['kind']} ditambahkan")

    def _source_failed(self, error: Exception) -> None:
        if isinstance(error, pdf_reader.SourceReadError):
            messagebox.showerror(
                "Sumber gagal dibaca",
                f"{error}\nGunakan tombol 'Tempel Teks Manual...' untuk sumber ini; "
                "sumber lain tetap bisa diproses.",
            )
        else:
            messagebox.showerror("Gagal memproses sumber", str(error))
        self._status.config(text="Penambahan sumber gagal.")

    def _add_pdf(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Pilih berkas PDF",
            filetypes=[("PDF", "*.pdf"), ("Semua berkas", "*.*")],
        )
        if chosen:
            self._add_pdf_core(Path(chosen))

    def _add_pdf_core(self, path: Path) -> None:
        self._status.config(text="Membaca PDF (bisa lama bila scan)...")
        client = self._ai_client()
        catatan = {"meta_ai_gagal": False}

        def work():
            text = pdf_reader.extract_text_or_ocr(path)
            meta = normalize_metadata(pdf_reader.extract_metadata(path))
            try:
                source = bibliography.extract_source(text, client)
            except Exception:
                catatan["meta_ai_gagal"] = True
                source = Source([], "", "")
            return source_to_record(bibliography.merge_metadata(source, meta), text, "pdf")

        def selesai(record: dict) -> None:
            self._append_source(record)
            if catatan["meta_ai_gagal"]:
                self._status.config(
                    text=self._status.cget("text")
                    + " Metadata otomatis kosong; lengkapi lewat Koreksi."
                )

        run_in_thread(self._widget, work, on_success=selesai, on_error=self._source_failed)

    def _add_link(self) -> None:
        url = simpledialog.askstring(
            "Tambah Sumber Link", "URL sumber:", parent=self._widget
        )
        if not url or not url.strip():
            return
        self._add_link_core(url.strip())

    def _add_link_core(self, url: str) -> None:
        self._status.config(text="Mengambil halaman web...")
        client = self._ai_client()
        catatan = {"meta_ai_gagal": False}

        def work():
            text, meta = web_reader.fetch(url)
            meta = normalize_metadata(meta)
            try:
                source = bibliography.extract_source(text, client)
            except Exception:
                catatan["meta_ai_gagal"] = True
                source = Source([], "", "")
            return source_to_record(bibliography.merge_metadata(source, meta), text, "web")

        def selesai(record: dict) -> None:
            self._append_source(record)
            if catatan["meta_ai_gagal"]:
                self._status.config(
                    text=self._status.cget("text")
                    + " Metadata otomatis kosong; lengkapi lewat Koreksi."
                )

        run_in_thread(self._widget, work, on_success=selesai, on_error=self._source_failed)

    def _paste_manual(self) -> None:
        dialog = tk.Toplevel(self._widget)
        dialog.title("Tempel Teks Manual")
        dialog.transient(self._widget.winfo_toplevel())
        dialog.grab_set()
        ttk.Label(
            dialog, text="Tempel teks sumber di bawah, lalu klik OK."
        ).pack(anchor="w", padx=8, pady=4)
        text_widget = tk.Text(dialog, width=64, height=14, wrap="word")
        text_widget.pack(fill="both", expand=True, padx=8, pady=4)

        def confirm() -> None:
            content_text = text_widget.get("1.0", "end").strip()
            dialog.destroy()
            if content_text:
                self._add_manual_text(content_text)

        ttk.Button(dialog, text="OK", command=confirm).pack(pady=6)
        text_widget.focus_set()

    def _add_manual_text(self, text: str) -> None:
        self._status.config(text="Mengekstrak metadata teks manual...")
        client = self._ai_client()

        def work():
            source = bibliography.extract_source(text, client)
            return source_to_record(bibliography.merge_metadata(source, {}), text, "manual")

        run_in_thread(self._widget, work, on_success=self._append_source, on_error=self._source_failed)

    # ----------------------------------------------------------- pengaturan

    def _on_template_selected(self, _event=None) -> None:
        name = self._template_var.get()
        item = next((t for t in self._templates if t.nama == name), None)
        if item is None:
            self._template = None
            return
        try:
            result = validate_template(Path(item.path))
        except TemplateError as error:
            messagebox.showerror("Template tidak valid", str(error))
            self._template = None
            self._unknown_markers = []
            self._template_var.set("")
            return
        if result.missing or result.not_standalone:
            lines = []
            if result.missing:
                lines.append("Penanda wajib yang kurang: " + ", ".join(result.missing))
            if result.not_standalone:
                lines.append(
                    "Penanda khusus yang tidak berdiri sendiri: "
                    + ", ".join(result.not_standalone)
                )
            lines.append("Pilih template lain untuk melanjutkan.")
            messagebox.showwarning("Template tidak lengkap", "\n".join(lines))
            self._template = None
            self._unknown_markers = []
            self._template_var.set("")
            return
        self._template = item
        self._unknown_markers = list(result.unknown)
        if result.unknown:
            self._status.config(
                text="Catatan: penanda tak dikenal di template: " + ", ".join(result.unknown)
            )
        self._save_draft()

    def _outline_content(self) -> list[str]:
        raw = self._outline_text.get("1.0", "end")
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _update_outline_button(self) -> None:
        if self._outline_content():
            self._suggest_button.grid_remove()
        else:
            self._suggest_button.grid()

    def _on_outline_edited(self) -> None:
        self._update_outline_button()
        self._save_draft()

    def _suggest_outline(self) -> None:
        topic = self._judul_var.get().strip()
        if not topic:
            messagebox.showinfo(
                "Judul kosong", "Isi judul laporan lebih dulu sebagai topik outline."
            )
            return
        self._status.config(text="Menyusun usulan outline...")
        client = self._ai_client()
        sources = [record_to_source(record) for record in self._sources]
        texts = [record.get("text", "") for record in self._sources]

        def work():
            return content.suggest_outline(topic, sources, texts, client)

        def on_success(items) -> None:
            if not items:
                messagebox.showwarning(
                    "Outline kosong",
                    "AI tidak mengembalikan outline. Tulis outline manual atau coba lagi.",
                )
            else:
                self._outline_text.delete("1.0", "end")
                self._outline_text.insert("1.0", "\n".join(items))
                self._save_draft()
            self._update_outline_button()
            self._status.config(text="Usulan outline siap." if items else "Outline tidak tersedia.")

        def on_error(error) -> None:
            messagebox.showerror("Gagal menyusun outline", str(error))
            self._status.config(text="Penambahan outline gagal.")

        run_in_thread(self._widget, work, on_success=on_success, on_error=on_error)

    # ---------------------------------------------------------------- draf

    def _save_docx(self) -> None:
        """Gerbang ekspor, susun fields, render DOCX di latar, hapus draf saat sukses (11.5, 18)."""
        if not self._statuses:
            messagebox.showinfo(
                "Belum ada isi", "Generate isi laporan lebih dulu sebelum menyimpan DOCX."
            )
            return
        if self._template is None:
            messagebox.showinfo(
                "Template belum siap",
                "Pilih template yang lengkap di panel Pengaturan Laporan sebelum menyimpan.",
            )
            return
        cited = report.cited_ids(self._statuses)
        sources = [record_to_source(record) for record in self._sources]
        labels = report.labels_for(sources, cited)
        references = report.references_for(sources, cited)
        uncited = report.uncited_ids(sources, cited)

        ok, gate_message = report.can_export(self._statuses, frozenset(self._done))
        if not ok:
            proceed = messagebox.askyesno(
                "Ekspor terblokir", f"{gate_message}\n\nTetap simpan DOCX sekarang?"
            )
            if not proceed:
                self._status.config(text="Simpan dibatalkan; selesaikan kalimat yang tertunda.")
                return
            _LOG.warning("Ekspor dipaksa meski gerbang memblokir: %s", gate_message)
        if uncited:
            _LOG.info("Sumber dimasukkan tapi tidak dikutip: %s", uncited)
            self._status.config(
                text=f"Catatan: {len(uncited)} sumber tidak dikutip; tetap dicatat di log."
            )
        if self._unknown_markers:
            proceed = messagebox.askyesno(
                "Penanda tak dikenal",
                "Template memuat penanda tak dikenal: "
                + ", ".join(self._unknown_markers)
                + "\n\nTetap simpan DOCX?",
            )
            if not proceed:
                self._status.config(text="Simpan dibatalkan.")
                return

        profil = self._db.get_profil()
        profile = {"nama": profil.nama, "nim": profil.nim, "prodi": profil.prodi} if profil else {}
        judul = self._judul_var.get().strip()
        fields = report.build_fields(
            judul,
            profile,
            self._picker_vars["dosen"].get(),
            self._picker_vars["matkul"].get(),
            date.today(),
        )
        logo_path = None
        logo_name = self._picker_vars["logo"].get()
        if logo_name:
            item = next((l for l in self._logo_list if l.nama == logo_name), None)
            if item is not None and item.path:
                logo_path = Path(item.path)
        safe_judul = re.sub(r"[^\w\- ]", "", judul).strip().replace(" ", "_") or "laporan"
        out_path = paths.OUTPUT_DIR / f"{safe_judul}.docx"
        if out_path.exists():
            if not messagebox.askyesno(
                "Berkas sudah ada",
                f"'{out_path.name}' sudah ada di folder output.\nTimpa berkas lama?",
            ):
                self._status.config(text="Simpan dibatalkan.")
                return
        template_path = Path(self._template.path)
        # Salinan data, bukan referensi hidup: suntingan kalimat saat render
        # tidak boleh mengubah isi dokumen yang sedang disusun.
        sections = report.sections_from_dicts(report.sections_to_dicts(self._sections))
        self._status.config(text="Menyusun dokumen DOCX...")

        def work():
            return renderer.render_report(
                template_path, fields, sections, references, logo_path, out_path, labels=labels
            )

        def on_success(result) -> None:
            drafts.delete_draft(_DRAFT_ID)
            self._status.config(text=f"DOCX tersimpan: {result}")
            messagebox.showinfo("Dokumen tersimpan", f"Berkas laporan tersimpan di:\n{result}")

        def on_error(error) -> None:
            messagebox.showerror("Gagal menyimpan DOCX", str(error))
            self._status.config(text="Penyimpanan DOCX gagal.")

        run_in_thread(self._widget, work, on_success=on_success, on_error=on_error)

    def _generate(self) -> None:
        if self._generate_button.cget("state") == "disabled":
            return
        outline = self._outline_content()
        if not outline:
            messagebox.showinfo(
                "Outline kosong", "Isi outline manual atau klik Usulkan Outline lebih dulu."
            )
            return
        if not self._sources:
            messagebox.showinfo(
                "Tanpa sumber", "Tambahkan minimal satu sumber sebelum generate."
            )
            return
        topic = self._judul_var.get().strip() or "Laporan"
        self._generate_button.config(state="disabled")
        self._progres.start(12)
        self._generate_started = time.monotonic()
        self._generate_tick = None
        self._tick_generate()
        client = self._ai_client()
        sources = [record_to_source(record) for record in self._sources]
        texts = [record.get("text", "") for record in self._sources]

        def work():
            return content.generate_sections(topic, outline, sources, texts, client)

        def on_success(sections) -> None:
            if self._sections:
                overwrite_all = messagebox.askyesno(
                    "Tulis ulang isi laporan",
                    "Ada isi laporan yang sudah ada.\n\n"
                    "Ya = tulis ulang semua; catatan manual Anda dibuang.\n"
                    "Tidak = catatan manual dipertahankan di belakang hasil baru.",
                )
                self._sections = report.merge_for_regenerate(
                    self._sections, sections, overwrite_all=overwrite_all
                )
            else:
                self._sections = sections
            self._reverify()
            self._render_statuses()
            self._save_draft()
            pesan = f"Generate selesai: {len(self._sections)} bab."
            diminta = len(self._outline_content())
            if len(self._sections) < diminta:
                pesan += (
                    f" Kurang dari {diminta} bab yang diminta;"
                    " jawaban AI sebagian tidak terbaca, coba klik Generate lagi."
                )
            self._finish_generate(pesan)
            self._notebook.select(self._review_page)

        def on_error(error) -> None:
            messagebox.showerror("Generate gagal", str(error))
            self._finish_generate("Generate gagal.")

        run_in_thread(self._widget, work, on_success=on_success, on_error=on_error)

    def _tick_generate(self) -> None:
        """Perbarui status dengan detik berjalan selama generate berlangsung."""
        detik = int(time.monotonic() - self._generate_started)
        self._status.config(text=f"Menyusun isi laporan... ({detik} detik)")
        self._generate_tick = self._widget.after(1000, self._tick_generate)

    def _finish_generate(self, message: str) -> None:
        """Hentikan penghitung, aktifkan kembali tombol, laporkan hasil."""
        if self._generate_tick is not None:
            self._widget.after_cancel(self._generate_tick)
            self._generate_tick = None
        self._progres.stop()
        self._generate_button.config(state="normal")
        self._status.config(text=message)

    def _source_texts_by_id(self) -> dict[int, str]:
        return {index: record.get("text", "") for index, record in enumerate(self._sources)}

    def _reverify(self) -> None:
        self._statuses = verify_sections(self._sections, self._source_texts_by_id())

    def _collect_fields(self) -> dict:
        return {
            "judul": self._judul_var.get(),
            "outline": self._outline_text.get("1.0", "end").rstrip("\n"),
            "template": self._template_var.get(),
            "dosen": self._picker_vars["dosen"].get(),
            "matkul": self._picker_vars["matkul"].get(),
            "logo": self._picker_vars["logo"].get(),
        }

    def _save_draft(self) -> None:
        state = drafts.DraftState(
            draft_id=_DRAFT_ID,
            fields=self._collect_fields(),
            sources=self._sources,
            sections=report.sections_to_dicts(self._sections),
            done=sorted(self._done),
        )
        drafts.save_draft(state)

    def _restore_draft(self) -> None:
        state = drafts.load_draft(_DRAFT_ID)
        if state is None:
            return
        fields = state.fields
        self._judul_var.set(fields.get("judul", ""))
        if fields.get("outline"):
            self._outline_text.insert("1.0", fields["outline"])
        for key in ("dosen", "matkul", "logo"):
            if fields.get(key):
                self._picker_vars[key].set(fields[key])
        self._sources = list(state.sources)
        self._refresh_source_list()
        self._sections = report.sections_from_dicts(state.sections)
        self._done = set(state.done)
        if self._sections:
            self._reverify()
            self._render_statuses()
        if fields.get("template"):
            self._template_var.set(fields["template"])
            self._on_template_selected()
        self._update_outline_button()
