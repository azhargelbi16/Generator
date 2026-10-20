"""Dialog Pemeriksaan Akhir (addendum D.3) + jalur ekspor DOCX.

Dialog hanya muncul bila `preflight.find_issues` menemukan sesuatu; tanpa
temuan ekspor langsung. Ekspor berjalan di Worker; sukses -> draf dihapus
(parity Tk); "buka di Word" lewat injeksi `opener` (default os.startfile).
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from .. import config, drafts, paths, preflight, report
from ..document import renderer
from ..sources.records import DRAFT_ACTIVE_ID, record_to_source
from ..textutil import has_mojibake, repair_mojibake
from .workers import run_in_thread

_YES = QMessageBox.StandardButton.Yes


def _mojibake_names(sources) -> list[str]:
    names: list[str] = []
    for source in sources:
        for author in source.authors:
            for value in (author.family, author.given, author.abbrev):
                if value and has_mojibake(value):
                    names.append(value)
        for value in (source.title, source.container):
            if value and has_mojibake(value):
                names.append(value)
    return names


class PreflightDialog(QDialog):
    """Perbaikan pilihan user; atribut hasil dibaca setelah exec() Accepted."""

    def __init__(self, judul, sources, statuses, cited, logo_path, issues, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pemeriksaan Akhir")
        self.issues = list(issues)
        self.chosen_style = cfg.citation_style
        self.logo_path = logo_path
        self.fix_mojibake = False
        self.open_after_save = False
        self._judul = judul
        self._sources = sources

        layout = QVBoxLayout(self)
        checks = preflight.run_checks(
            judul, sources, statuses, cited, logo_path, style=cfg.citation_style
        )
        for check in checks:
            tanda = "✓" if check.ok else "⚠"
            layout.addWidget(QLabel(f"{tanda} {check.label}: {check.detail}"))
        kinds = {issue.kind for issue in self.issues}

        self._names_before = _mojibake_names(sources)
        self._names_label = QLabel("")
        self._fix_button = QPushButton("Perbaiki semua nama rusak")
        self._fix_button.clicked.connect(self._apply_fix_names)
        if "mojibake" in kinds:
            self._names_label.setText("Nama rusak: " + "; ".join(self._names_before))
            layout.addWidget(self._names_label)
            layout.addWidget(self._fix_button)
        else:
            self._names_label.hide()
            self._fix_button.hide()

        baris_nama = QHBoxLayout()
        self._filename_edit = QLineEdit(report.sanitize_filename(judul))
        baris_nama.addWidget(self._filename_edit)
        self._tidy_button = QPushButton("Rapikan nama berkas")
        self._tidy_button.clicked.connect(
            lambda: self._filename_edit.setText(report.sanitize_filename(self._judul))
        )
        baris_nama.addWidget(self._tidy_button)
        layout.addLayout(baris_nama)
        if "filename" not in kinds:
            self._tidy_button.hide()

        baris_gaya = QHBoxLayout()
        baris_gaya.addWidget(QLabel("Gaya sitasi:"))
        self._radio_et_al = QRadioButton("et al.")
        self._radio_dkk = QRadioButton("dkk.")
        grup = QButtonGroup(self)
        grup.addButton(self._radio_et_al)
        grup.addButton(self._radio_dkk)
        (self._radio_dkk if cfg.citation_style == "dkk" else self._radio_et_al).setChecked(True)
        self._radio_et_al.toggled.connect(lambda _c: self._on_style_changed())
        self._radio_dkk.toggled.connect(lambda _c: self._on_style_changed())
        baris_gaya.addWidget(self._radio_et_al)
        baris_gaya.addWidget(self._radio_dkk)
        self._example_label = QLabel("")
        baris_gaya.addWidget(self._example_label)
        baris_gaya.addStretch(1)
        layout.addLayout(baris_gaya)
        self._on_style_changed()

        if "logo_missing" in kinds:
            layout.addWidget(QLabel("⚠ Logo belum dipilih atau berkas tidak ada."))
            pilih_logo = QPushButton("Pilih logo...")
            pilih_logo.clicked.connect(self._pick_logo)
            layout.addWidget(pilih_logo)

        self._dosen_checkbox = QCheckBox("Minta review Dosen")
        self._dosen_checkbox.setChecked(cfg.dosen_review)
        layout.addWidget(self._dosen_checkbox)

        baris = QHBoxLayout()
        self._save_open_button = QPushButton("Simpan & buka di Word")
        self._save_open_button.clicked.connect(self._accept_open)
        baris.addWidget(self._save_open_button)
        simpan = QPushButton("Simpan saja")
        simpan.clicked.connect(self.accept)
        baris.addWidget(simpan)
        batal = QPushButton("Batal")
        batal.clicked.connect(self.reject)
        baris.addWidget(batal)
        layout.addLayout(baris)

    @property
    def filename(self) -> str:
        return self._filename_edit.text().strip()

    @property
    def dosen_review(self) -> bool:
        return self._dosen_checkbox.isChecked()

    def _on_style_changed(self) -> None:
        self.chosen_style = "dkk" if self._radio_dkk.isChecked() else "et_al"
        if not self._sources:
            self._example_label.setText("contoh: (—)")
            return
        label = report.labels_for([self._sources[0]], {0}, style=self.chosen_style).get(0, "(—)")
        self._example_label.setText(f"contoh: {label}")

    def _apply_fix_names(self) -> None:
        self.fix_mojibake = True
        diperbaiki = [repair_mojibake(n) for n in self._names_before]
        self._names_label.setText("Nama diperbaiki: " + "; ".join(diperbaiki))

    def _pick_logo(self) -> None:
        chosen, _selected = QFileDialog.getOpenFileName(
            self, "Pilih berkas logo", "", "Gambar (*.png *.jpg *.jpeg);;Semua berkas (*.*)"
        )
        if chosen:
            self.logo_path = Path(chosen)

    def _accept_open(self) -> None:
        self.open_after_save = True
        self.accept()


def _resolve_logo_path(state) -> Path | None:
    logo_name = (state.fields or {}).get("logo", "")
    item = next(
        (logo for logo in getattr(state, "_logo_list", []) if logo.nama == logo_name), None
    )
    if item is not None and item.path:
        return Path(item.path)
    return None


def export_report(state, opener=None) -> Path | None:
    """Jalur ekspor penuh dengan gerbang parity Tk; None bila user membatalkan."""
    sources = [record_to_source(r) for r in state.sources]
    judul = (state.fields or {}).get("judul", "").strip()
    cited = report.cited_ids(state.statuses)
    cfg_path = Path(getattr(state, "_config_path", None) or paths.CONFIG_PATH)
    cfg = config.load_config(cfg_path)
    logo_path = _resolve_logo_path(state)
    template_path = Path(state.template.path)

    ok, gate_message = report.can_export(state.statuses, frozenset(state.done))
    if not ok:
        jawab = QMessageBox.question(
            None, "Ekspor terblokir", f"{gate_message}\n\nTetap simpan DOCX sekarang?"
        )
        if jawab != _YES:
            return None
    unknown = list(getattr(state, "unknown_markers", []) or [])
    if unknown:
        jawab = QMessageBox.question(
            None,
            "Penanda tak dikenal",
            "Template memuat penanda tak dikenal: "
            + ", ".join(unknown)
            + "\n\nTetap simpan DOCX?",
        )
        if jawab != _YES:
            return None

    export_sections = report.sections_from_dicts(report.sections_to_dicts(state.sections))
    chosen_style = cfg.citation_style
    filename = report.sanitize_filename(judul)
    open_after = False
    issues = preflight.find_issues(
        judul, sources, state.statuses, cited, logo_path, style=cfg.citation_style
    )
    if issues:
        dialog = PreflightDialog(judul, sources, state.statuses, cited, logo_path, issues, cfg)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        chosen_style = dialog.chosen_style
        filename = dialog.filename or filename
        if dialog.logo_path is not None:
            logo_path = dialog.logo_path
        if dialog.fix_mojibake:
            sources, export_sections = preflight.fix_mojibake(sources, export_sections)
        if dialog.dosen_review != cfg.dosen_review:
            cfg.dosen_review = dialog.dosen_review
            config.save_config(cfg, cfg_path)
        open_after = dialog.open_after_save

    paths.ensure_dirs()
    out_path = paths.OUTPUT_DIR / f"{filename}.docx"
    if out_path.exists():
        jawab = QMessageBox.question(
            None,
            "Berkas sudah ada",
            f"'{out_path.name}' sudah ada di folder output.\nTimpa berkas lama?",
        )
        if jawab != _YES:
            return None

    labels = report.labels_for(sources, cited, style=chosen_style)
    references = report.references_for(sources, cited)
    profil = state._db.get_profil()
    profile = {"nama": profil.nama, "nim": profil.nim, "prodi": profil.prodi} if profil else {}
    fields = report.build_fields(
        judul,
        profile,
        state.fields.get("dosen", ""),
        state.fields.get("matkul", ""),
        date.today(),
    )

    holder = QObject()
    hasil: dict = {}
    galat: list = []

    def work():
        return renderer.render_report(
            template_path,
            fields,
            export_sections,
            references,
            logo_path,
            out_path,
            labels=labels,
            update_fields=True,
        )

    thread, worker = run_in_thread(holder, work)
    loop = QEventLoop()
    worker.result.connect(lambda path: hasil.setdefault("path", path))
    worker.error.connect(lambda err: (galat.append(err), loop.quit()))
    worker.finished.connect(loop.quit)
    loop.exec()
    thread.wait(5000)
    if galat:
        raise RuntimeError(f"Gagal menyimpan DOCX: {galat[0]}")
    path = hasil.get("path")
    if path is None:
        return None
    drafts.delete_draft(DRAFT_ACTIVE_ID)
    if open_after:
        (opener or os.startfile)(path)
    return path
