"""Tab Buat Laporan bagian 1: sumber, fallback OCR/manual, koreksi metadata (12, Task 16).

Semua operasi lama (baca PDF/OCR, ambil web, panggilan AI) berjalan lewat
`worker.run_in_thread` supaya jendela tidak membeku. Kode tidak pernah menebak
pemisahan nama penulis; nilai dari AI hanyalah usulan yang diedit user di
formulir koreksi.
"""

from __future__ import annotations

import logging
import re
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

_LOG = logging.getLogger(__name__)

_DRAFT_ID = "aktif"

_AUTHOR_FIELDS = ("family", "given", "is_org", "abbrev")

_STATUS_MARKS = {
    STATUS_VERIFIED: "OK",
    STATUS_UNVERIFIED: "BELUM",
    STATUS_NON_FACTUAL: "BUKAN-KLAIM",
}
_STATUS_COLORS = {
    STATUS_VERIFIED: "#1a7f37",
    STATUS_UNVERIFIED: "#b42318",
    STATUS_NON_FACTUAL: "#666666",
}


def normalize_metadata(doc: dict[str, str]) -> dict[str, str]:
    """Samakan kunci metadata dokumen dengan yang dibaca `merge_metadata`.

    Pembaca PDF dan web memancarkan `date`, sedangkan penggabungan mengharapkan
    `year`; salin tanpa menghapus nilai asli.
    """
    result = dict(doc or {})
    if result.get("date") and not result.get("year"):
        result["year"] = result["date"]
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


class ReportTab(ttk.Frame):
    """Pengaturan laporan, masukan sumber, dan koreksi metadata."""

    def __init__(self, parent, db: database.Database):
        super().__init__(parent, padding=12)
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

        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)

        self._build_source_area(left)
        self._build_setup_area(right)

        self._restore_draft()

    # ------------------------------------------------------------------ UI

    def _build_source_area(self, parent) -> None:
        list_frame = ttk.LabelFrame(parent, text="Sumber")
        list_frame.pack(side="top", fill="both", expand=True)
        self._source_listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        self._source_listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self._source_listbox.bind("<<ListboxSelect>>", lambda _event: self._on_source_select())
        scrollbar = ttk.Scrollbar(list_frame, command=self._source_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._source_listbox.config(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(parent)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="Tambah PDF...", command=self._add_pdf).pack(
            side="left", padx=4
        )
        ttk.Button(buttons, text="Tambah Link...", command=self._add_link).pack(
            side="left", padx=4
        )
        ttk.Button(buttons, text="Tempel Teks Manual...", command=self._paste_manual).pack(
            side="left", padx=4
        )
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
        ttk.Button(form, text="Terapkan Koreksi", command=self._apply_corrections).grid(
            row=len(self._meta_vars) + 1, column=0, columnspan=4, sticky="w", padx=6, pady=6
        )

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
        self._outline_text = tk.Text(frame, width=44, height=9, wrap="word")
        self._outline_text.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=6, pady=4)
        self._outline_text.bind("<KeyRelease>", lambda _event: self._on_outline_edited())

        self._suggest_button = ttk.Button(
            frame, text="Usulkan Outline", command=self._suggest_outline
        )
        self._suggest_button.grid(row=8, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Button(frame, text="Generate isi laporan", command=self._generate).grid(
            row=9, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 8)
        )
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)
        self._update_outline_button()
        self._build_result_area(parent)

    def _build_result_area(self, parent) -> None:
        result = ttk.LabelFrame(parent, text="Hasil generate (satu kotak per kalimat)")
        result.pack(side="top", fill="both", expand=True, pady=(8, 0))

        container = ttk.Frame(result)
        container.pack(side="top", fill="both", expand=True, padx=4, pady=4)
        self._canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._rows_frame = ttk.Frame(self._canvas, padding=2)
        self._rows_window = self._canvas.create_window((0, 0), window=self._rows_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._rows_frame.bind("<Configure>", lambda _event: self._on_rows_configure())
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        actions = ttk.Frame(result)
        actions.pack(side="bottom", fill="x")
        ttk.Button(actions, text="Tandai selesai", command=self._mark_done).pack(side="left", padx=4)
        ttk.Button(
            actions, text="Tandai semua bukan klaim selesai", command=self._mark_all_nonfactual_done
        ).pack(side="left", padx=4)
        ttk.Button(actions, text="Pulihkan sitasi", command=self._restore_citation_action).pack(
            side="left", padx=4
        )
        ttk.Button(actions, text="Parafrase", command=self._paraphrase).pack(side="left", padx=4)
        ttk.Button(actions, text="Simpan DOCX", command=self._save_docx).pack(side="left", padx=4)

        self._result_hint = ttk.Label(
            result,
            text="Klik kotak kalimat untuk memilih; mengubah isinya menandai kalimat manual "
            "(berstatus belum terverifikasi sampai ditandai selesai).",
            foreground="#666666",
            wraplength=560,
            justify="left",
        )
        self._result_hint.pack(side="bottom", fill="x")

        self._rows = []
        self._selected_row = None
        self._render_statuses()

    def _on_rows_configure(self) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfigure(self._rows_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self._canvas.yview_scroll(-int(event.delta / 120), "units")

    def _render_statuses(self) -> None:
        """Bangun ulang baris kalimat; pemetaan teks ke kalimat satu banding satu."""
        for child in self._rows_frame.winfo_children():
            child.destroy()
        self._rows = []
        self._selected_row = None
        status_by_uid = {item.sentence.uid: item.status for item in self._statuses}
        total = 0
        for section in self._sections:
            ttk.Label(
                self._rows_frame, text=f"## {section.title}", font=("", 10, "bold")
            ).pack(fill="x", pady=(8, 2))
            for paragraph in section.paragraphs:
                for sentence in paragraph.sentences:
                    total += 1
                    row = ttk.Frame(self._rows_frame)
                    row.pack(fill="x", pady=2)
                    status = status_by_uid.get(sentence.uid, STATUS_UNVERIFIED)
                    label = ttk.Label(
                        row,
                        text=_STATUS_MARKS.get(status, _STATUS_MARKS[STATUS_UNVERIFIED]),
                        width=13,
                        anchor="w",
                        foreground=_STATUS_COLORS.get(status, _STATUS_COLORS[STATUS_UNVERIFIED]),
                    )
                    label.pack(side="left")
                    var = tk.StringVar(value=sentence.text)
                    entry = ttk.Entry(row, textvariable=var)
                    entry.pack(side="left", fill="x", expand=True)
                    rec = {
                        "uid": sentence.uid,
                        "sentence": sentence,
                        "var": var,
                        "label": label,
                        "entry": entry,
                    }
                    entry.bind("<Button-1>", lambda _event, rec=rec: self._select_row(rec))
                    entry.bind("<FocusIn>", lambda _event, rec=rec: self._select_row(rec))
                    entry.bind("<FocusOut>", lambda _event, rec=rec: self._commit_edit(rec))
                    entry.bind("<Return>", lambda _event, rec=rec: self._commit_edit(rec))
                    self._rows.append(rec)
        if total == 0:
            ttk.Label(
                self._rows_frame,
                text="Belum ada isi. Isi outline, tambahkan sumber, lalu klik Generate isi laporan.",
            ).pack(anchor="w", pady=8)
        self._rows_frame.update_idletasks()
        self._on_rows_configure()

    def _select_row(self, rec: dict) -> None:
        self._selected_row = rec
        self._result_hint.config(text=f"Kalimat terpilih: {rec['sentence'].text[:70]}")

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

    def _commit_edit(self, rec: dict) -> None:
        new_text = rec["var"].get().strip()
        if not new_text or new_text == rec["sentence"].text:
            return
        new_sentence = report.apply_manual_edit(rec["sentence"], new_text)
        self._swap_sentence(rec["sentence"].uid, [new_sentence])
        rec["sentence"] = new_sentence
        self._after_structure_change(
            "Kalimat disunting manual; berstatus belum terverifikasi sampai ditandai selesai."
        )

    def _after_structure_change(self, message: str) -> None:
        self._reverify()
        self._refresh_row_marks()
        self._save_draft()
        self._status.config(text=message)

    def _refresh_row_marks(self) -> None:
        """Perbarui penanda status tiap baris tanpa membangun ulang kotak teks."""
        status_by_uid = {item.sentence.uid: item.status for item in self._statuses}
        fresh = {sentence.uid: sentence for sentence in self._iter_sentences()}
        for rec in self._rows:
            sentence = fresh.get(rec["uid"])
            if sentence is not None:
                rec["sentence"] = sentence
            status = status_by_uid.get(rec["uid"], STATUS_UNVERIFIED)
            rec["label"].config(
                text=_STATUS_MARKS.get(status, _STATUS_MARKS[STATUS_UNVERIFIED]),
                foreground=_STATUS_COLORS.get(status, _STATUS_COLORS[STATUS_UNVERIFIED]),
            )

    def _mark_done(self) -> None:
        if self._selected_row is None:
            self._status.config(text="Klik dulu kotak kalimat yang ingin ditandai selesai.")
            return
        self._done.add(self._selected_row["uid"])
        self._refresh_row_marks()
        self._save_draft()
        self._status.config(text="Kalimat ditandai selesai.")

    def _mark_all_nonfactual_done(self) -> None:
        uids = report.non_factual_uids(self._statuses)
        self._done.update(uids)
        self._refresh_row_marks()
        self._save_draft()
        self._status.config(text=f"{len(uids)} kalimat bukan klaim faktual ditandai selesai.")

    def _restore_citation_action(self) -> None:
        if self._selected_row is None:
            self._status.config(text="Klik dulu kotak kalimat yang sitasinya ingin dipulihkan.")
            return
        sentence = self._selected_row["sentence"]
        if sentence.citation:
            self._status.config(text="Sitasi kalimat ini sudah aktif.")
            return
        new_sentence = report.restore_citation(sentence)
        self._swap_sentence(sentence.uid, [new_sentence])
        self._selected_row["sentence"] = new_sentence
        self._after_structure_change("Sitasi kalimat dipulihkan.")

    def _paraphrase(self) -> None:
        if self._selected_row is None:
            self._status.config(text="Klik dulu kotak kalimat yang ingin diparafrase.")
            return
        sentence = self._selected_row["sentence"]
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
            self._render_statuses()
            self._after_structure_change(
                "Parafrase selesai; kalimat baru dihitung ulang statusnya."
            )

        def on_error(error) -> None:
            messagebox.showerror("Parafrase gagal", str(error))
            self._status.config(text="Parafrase gagal.")

        run_in_thread(self, work, on_success=on_success, on_error=on_error)

    # -------------------------------------------------------------- sumber

    def _refresh_source_list(self) -> None:
        self._source_listbox.delete(0, "end")
        for index, record in enumerate(self._sources, start=1):
            year = f" ({record['year']})" if record.get("year") else ""
            self._source_listbox.insert("end", f"{index}. {record.get('title') or 'tanpa judul'}{year}")

    def _selected_index(self) -> int | None:
        selection = self._source_listbox.curselection()
        return selection[0] if selection else None

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

        def work():
            text = pdf_reader.extract_text_or_ocr(path)
            meta = normalize_metadata(pdf_reader.extract_metadata(path))
            source = bibliography.extract_source(text, client)
            return source_to_record(bibliography.merge_metadata(source, meta), text, "pdf")

        run_in_thread(self, work, on_success=self._append_source, on_error=self._source_failed)

    def _add_link(self) -> None:
        url = simpledialog.askstring("Tambah Sumber Link", "URL sumber:", parent=self)
        if not url or not url.strip():
            return
        self._add_link_core(url.strip())

    def _add_link_core(self, url: str) -> None:
        self._status.config(text="Mengambil halaman web...")
        client = self._ai_client()

        def work():
            text = web_reader.fetch_text(url)
            meta = normalize_metadata(web_reader.fetch_metadata(url))
            source = bibliography.extract_source(text, client)
            return source_to_record(bibliography.merge_metadata(source, meta), text, "web")

        run_in_thread(self, work, on_success=self._append_source, on_error=self._source_failed)

    def _paste_manual(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Tempel Teks Manual")
        dialog.transient(self.winfo_toplevel())
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

        run_in_thread(self, work, on_success=self._append_source, on_error=self._source_failed)

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

        run_in_thread(self, work, on_success=on_success, on_error=on_error)

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

        run_in_thread(self, work, on_success=on_success, on_error=on_error)

    def _generate(self) -> None:
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
        self._status.config(text="Menyusun isi laporan; bisa memakan waktu beberapa menit...")
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
            self._status.config(
                text=f"Generate selesai: {len(self._sections)} bab."
            )

        def on_error(error) -> None:
            messagebox.showerror("Generate gagal", str(error))
            self._status.config(text="Generate gagal.")

        run_in_thread(self, work, on_success=on_success, on_error=on_error)

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
