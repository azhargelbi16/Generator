"""Tab Buat Laporan bagian 1: sumber, fallback OCR/manual, koreksi metadata (12, Task 16).

Semua operasi lama (baca PDF/OCR, ambil web, panggilan AI) berjalan lewat
`worker.run_in_thread` supaya jendela tidak membeku. Kode tidak pernah menebak
pemisahan nama penulis; nilai dari AI hanyalah usulan yang diedit user di
formulir koreksi.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import config, database, drafts, paths, report
from ..ai import bibliography, content
from ..ai.citation import Author, Source
from ..ai.client import AIClient
from ..document.template import TemplateError, validate_template
from ..sources import pdf_reader, web_reader
from ..verification import (
    STATUS_NON_FACTUAL,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    verify_sections,
)
from .worker import run_in_thread

_DRAFT_ID = "aktif"

_AUTHOR_FIELDS = ("family", "given", "is_org", "abbrev")

_STATUS_MARKS = {
    STATUS_VERIFIED: ("OK ", "status-ok"),
    STATUS_UNVERIFIED: ("BELUM ", "status-belum"),
    STATUS_NON_FACTUAL: ("BUKAN-KLAIM ", "status-nonfactual"),
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
        result = ttk.LabelFrame(parent, text="Hasil generate (status per kalimat)")
        result.pack(side="top", fill="both", expand=True, pady=(8, 0))
        self._result_text = tk.Text(result, width=48, height=10, wrap="word", state="disabled")
        self._result_text.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar = ttk.Scrollbar(result, command=self._result_text.yview)
        scrollbar.pack(side="right", fill="y")
        self._result_text.config(yscrollcommand=scrollbar.set)
        self._result_text.tag_config("status-ok", foreground="#1a7f37")
        self._result_text.tag_config("status-belum", foreground="#b42318")
        self._result_text.tag_config("status-nonfactual", foreground="#666666")
        self._result_text.tag_config("judul-bab", font=("", 10, "bold"))

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
            self._template_var.set("")
            return
        self._template = item
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
            self._sections = sections
            self._reverify()
            self._render_statuses()
            self._save_draft()
            self._status.config(text=f"Generate selesai: {len(sections)} bab.")

        def on_error(error) -> None:
            messagebox.showerror("Generate gagal", str(error))
            self._status.config(text="Generate gagal.")

        run_in_thread(self, work, on_success=on_success, on_error=on_error)

    def _source_texts_by_id(self) -> dict[int, str]:
        return {index: record.get("text", "") for index, record in enumerate(self._sources)}

    def _reverify(self) -> None:
        self._statuses = verify_sections(self._sections, self._source_texts_by_id())

    def _render_statuses(self) -> None:
        status_by_uid = {item.sentence.uid: item.status for item in self._statuses}
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        for section in self._sections:
            self._result_text.insert("end", f"## {section.title}\n", "judul-bab")
            for paragraph in section.paragraphs:
                for sentence in paragraph.sentences:
                    mark, tag = _STATUS_MARKS.get(
                        status_by_uid.get(sentence.uid, STATUS_UNVERIFIED),
                        _STATUS_MARKS[STATUS_UNVERIFIED],
                    )
                    self._result_text.insert("end", mark, tag)
                    self._result_text.insert("end", sentence.text + "\n")
        self._result_text.config(state="disabled")

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
