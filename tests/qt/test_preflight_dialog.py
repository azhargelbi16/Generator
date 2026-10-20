"""Tes Pemeriksaan Akhir + jalur ekspor Qt (Task 5.1)."""

import zipfile
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox, QRadioButton
from docx import Document

from generator import config, drafts, paths, report
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.document import template as template_mod
from generator.sources.records import source_to_record, DRAFT_ACTIVE_ID
from generator.verification import verify_sections

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"


def _make_docx(path, markers):
    doc = Document()
    for marker in markers:
        doc.add_paragraph(marker)
    doc.save(path)


class _State:
    def __init__(self, tmp_path, judul, family="Santoso", logo=True, config_path=None):
        self.sources = [
            source_to_record(
                Source([Author(family, "Budi")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        sentences = [
            Sentence(text="Kalimat pertama teruji.", quote=QUOTED, source_ids=[0]),
            Sentence(text="Kalimat kedua teruji.", quote=QUOTED, source_ids=[0]),
        ]
        self.sections = [Section(1, "Bab Satu", [Paragraph(sentences)])]
        self.statuses = verify_sections(self.sections, {0: SOURCE_TEXT})
        self.done = set()
        self.fields = {"judul": judul, "dosen": "Dr. A", "matkul": "Agro", "logo": ""}
        template_path = tmp_path / "tpl.docx"
        _make_docx(template_path, template_mod.REQUIRED_PLACEHOLDERS)
        self.template = SimpleNamespace(path=str(template_path))
        if logo:
            logo_path = tmp_path / "logo.png"
            logo_path.write_bytes(b"png")
            self._logo_list = [SimpleNamespace(nama="Kampus", path=str(logo_path))]
            self.fields["logo"] = "Kampus"
        else:
            self._logo_list = []
        self._db = SimpleNamespace(
            get_profil=lambda: SimpleNamespace(nama="Budi", nim="123", prodi="Agro")
        )
        self._config_path = config_path or (tmp_path / "config.json")


def _harness(qapp, db_tmp, tmp_path, monkeypatch, **kwargs):
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")
    (tmp_path / "output").mkdir(exist_ok=True)
    config_path = tmp_path / "config.json"
    config.save_config(config.default_config(), config_path)
    state = _State(tmp_path, config_path=config_path, **kwargs)
    from generator.qt import preflight_dialog

    return state, preflight_dialog


def test_tanpa_temuan_ekspor_langsung_dan_draf_terhapus(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(qapp, db_tmp, tmp_path, monkeypatch, judul="Laporan Biochar")
    drafts.save_draft(
        drafts.DraftState(
            draft_id=DRAFT_ACTIVE_ID, fields=state.fields, sources=state.sources, sections=[], done=[]
        )
    )

    def _larang_dialog(*args, **kwargs):
        raise AssertionError("PreflightDialog tidak boleh dibuat tanpa temuan")

    monkeypatch.setattr(preflight_dialog, "PreflightDialog", _larang_dialog)
    hasil = preflight_dialog.export_report(state)
    assert hasil is not None and hasil.exists()
    assert hasil.stem == "Laporan_Biochar"
    assert "." not in hasil.stem
    with zipfile.ZipFile(hasil) as zf:
        settings = zf.read("word/settings.xml").decode("utf-8")
    assert "updateFields" in settings
    assert not (paths.DRAFTS_DIR / f"{DRAFT_ACTIVE_ID}.json").exists()


def test_dialog_temuan_perbaiki_gaya_nama_batal(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(
        qapp,
        db_tmp,
        tmp_path,
        monkeypatch,
        judul='Laporan: "Biochar" V2?',
        family="NemÃ©nyi",
        logo=False,
    )
    jumlah_awal = len(list((tmp_path / "output").glob("*.docx")))
    selesai = []

    class _FakeDialog(preflight_dialog.PreflightDialog):
        def exec(self):
            selesai.append(self)
            # Perbaiki semua nama rusak -> daftar nama berubah.
            nama_sebelum = self._names_label.text()
            self._fix_button.click()
            assert "Neményi" in self._names_label.text()
            assert self._names_label.text() != nama_sebelum
            # Radio gaya sitasi -> dkk.
            for radio in self.findChildren(QRadioButton):
                if radio.text().startswith("dkk"):
                    radio.click()
            assert self.chosen_style == "dkk"
            # Rapikan nama berkas -> nama dipakai saat ekspor.
            self._tidy_button.click()
            assert self.filename == "Laporan_Biochar_V2"
            self._filename_edit.setText("Nama_Khusus_Laporan")
            assert self.filename == "Nama_Khusus_Laporan"
            return int(QDialog.DialogCode.Accepted)

    monkeypatch.setattr(preflight_dialog, "PreflightDialog", _FakeDialog)
    hasil = preflight_dialog.export_report(state)
    assert len(selesai) == 1
    assert hasil is not None
    assert hasil.stem == "Nama_Khusus_Laporan"
    assert len(list((tmp_path / "output").glob("*.docx"))) == jumlah_awal + 1


def test_dialog_batal_tidak_menulis_berkas(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(
        qapp, db_tmp, tmp_path, monkeypatch, judul='Laporan: "X"?', logo=False
    )

    class _BatalDialog(preflight_dialog.PreflightDialog):
        def exec(self):
            return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(preflight_dialog, "PreflightDialog", _BatalDialog)
    hasil = preflight_dialog.export_report(state)
    assert hasil is None
    assert list((tmp_path / "output").glob("*.docx")) == []


def test_mode_dosen_tahan_restart(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(
        qapp, db_tmp, tmp_path, monkeypatch, judul='Laporan: "X"?', logo=False
    )
    assert config.load_config(state._config_path).dosen_review is False

    class _DosenDialog(preflight_dialog.PreflightDialog):
        def exec(self):
            self._dosen_checkbox.setChecked(True)
            return int(QDialog.DialogCode.Accepted)

    monkeypatch.setattr(preflight_dialog, "PreflightDialog", _DosenDialog)
    preflight_dialog.export_report(state)
    assert config.load_config(state._config_path).dosen_review is True


def test_opener_dipanggil_dengan_path_docx(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(
        qapp, db_tmp, tmp_path, monkeypatch, judul='Laporan: "X"?', logo=False
    )
    dibuka = []

    class _BukaDialog(preflight_dialog.PreflightDialog):
        def exec(self):
            self._save_open_button.click()
            return int(self.result())

    monkeypatch.setattr(preflight_dialog, "PreflightDialog", _BukaDialog)
    hasil = preflight_dialog.export_report(state, opener=lambda p: dibuka.append(p))
    assert hasil is not None
    assert dibuka == [hasil]


def test_timpa_berkas_memanggil_konfirmasi(qapp, db_tmp, tmp_path, monkeypatch):
    state, preflight_dialog = _harness(qapp, db_tmp, tmp_path, monkeypatch, judul="Laporan Biochar")
    lama = tmp_path / "output" / "Laporan_Biochar.docx"
    lama.write_bytes(b"lama")
    ditanya = []

    def _question(*args, **kwargs):
        ditanya.append(args)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", _question)
    hasil = preflight_dialog.export_report(state)
    assert hasil is not None
    assert hasil.read_bytes() != b"lama"
    assert ditanya, "konfirmasi timpa tidak pernah dipanggil"
