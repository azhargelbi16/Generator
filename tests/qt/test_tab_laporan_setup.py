"""Tes halaman setup Laporan Qt: sumber, koreksi, outline, draf (Task 3.1)."""

import json

from PySide6.QtCore import QEventLoop, QTimer

from generator import drafts, paths, report
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.database import Dosen, Logo, MataKuliah
from generator.sources.records import source_to_record


def _wait(controller, timeout_ms=5000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    controller._worker.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    controller._thread.wait(2000)


def _record(title="Judul A", kind="manual"):
    return source_to_record(
        Source([Author("Santoso", "Budi")], "2020", title, "Jurnal"),
        "teks sumber yang panjang",
        kind,
    )


def _ctl(db_tmp):
    from generator.qt.report_controller import ReportController

    return ReportController(db_tmp)


def test_injeksi_sumber_manual_daftar_tampil(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl.append_source(_record())
    assert ctl._source_list.count() == 1
    assert "Judul A" in ctl._source_list.item(0).text()
    assert ctl.sources[0]["title"] == "Judul A"
    assert "manual" in ctl._status.text()


def test_koreksi_metadata_menulis_ulang_record(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl.append_source(_record())
    ctl._source_list.setCurrentRow(0)
    ctl._meta_fields["title"].setText("Judul Baru")
    ctl._meta_fields["year"].setText("2021")
    ctl._author_rows[0]["family"].setText("Manurung")
    ctl._apply_corrections()
    assert ctl.sources[0]["title"] == "Judul Baru"
    assert ctl.sources[0]["year"] == "2021"
    assert ctl.sources[0]["authors"][0]["family"] == "Manurung"
    assert ctl._status.text() == "Koreksi metadata diterapkan."


def test_koreksi_tanpa_pilih_ditolak(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl.append_source(_record())
    ctl._source_list.setCurrentRow(-1)
    ctl._apply_corrections()
    assert ctl._status.text() == "Pilih sumber di daftar lebih dulu."


def test_usulan_outline_fake_client_mengisi_editor(qapp, db_tmp, monkeypatch):
    monkeypatch.setattr(
        "generator.ai.content.suggest_outline", lambda topic, sources, texts, client: ["Bab Satu", "Bab Dua"]
    )
    ctl = _ctl(db_tmp)
    ctl._judul_edit.setText("Topik Laporan")
    ctl._suggest_outline()
    _wait(ctl)
    assert ctl._outline_edit.toPlainText() == "Bab Satu\nBab Dua"
    assert ctl._status.text() == "Usulan outline siap."


def test_tombol_usulan_tersembunyi_setelah_outline_terisi(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    assert ctl._suggest_button.isVisibleTo(ctl.setup_page)
    ctl._outline_edit.setPlainText("Pendahuluan")
    ctl._on_outline_edited()
    assert not ctl._suggest_button.isVisibleTo(ctl.setup_page)


def test_muat_draf_format_tk_semua_field_kembali(qapp, db_tmp):
    db_tmp.add_dosen(Dosen(0, "Dr. Sitohang", "", "1"))
    db_tmp.add_mata_kuliah(MataKuliah(0, "Agroekologi", "AGT101"))
    db_tmp.add_logo(Logo(0, "Kampus", ""))
    fields = {
        "judul": "Laporan X",
        "outline": "Pendahuluan\nMetode",
        "template": "",
        "dosen": "Dr. Sitohang",
        "matkul": "Agroekologi",
        "logo": "Kampus",
    }
    sections = report.sections_to_dicts(
        [Section(1, "Pendahuluan", [Paragraph([Sentence("Klaim faktual.", "kutipan", [0])])])]
    )
    drafts.save_draft(
        drafts.DraftState(draft_id="aktif", fields=fields, sources=[_record()], sections=sections, done=[])
    )
    ctl = _ctl(db_tmp)
    assert ctl._judul_edit.text() == "Laporan X"
    assert ctl._outline_edit.toPlainText() == "Pendahuluan\nMetode"
    assert ctl._pickers["dosen"].currentText() == "Dr. Sitohang"
    assert ctl._pickers["matkul"].currentText() == "Agroekologi"
    assert ctl._pickers["logo"].currentText() == "Kampus"
    assert len(ctl.sources) == 1
    assert len(ctl.sections) == 1
    assert len(ctl.statuses) == 1  # draf lama diverifikasi ulang saat dimuat


def test_simpan_draf_format_json_sama_dengan_tk(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl.append_source(_record())
    raw = json.loads((paths.DRAFTS_DIR / "aktif.json").read_text(encoding="utf-8"))
    assert set(raw) == {"draft_id", "fields", "sources", "sections", "done"}
    assert raw["draft_id"] == "aktif"
    assert set(raw["fields"]) == {"judul", "outline", "template", "dosen", "matkul", "logo"}


def test_hapus_sumber_melepas_sitasi_dan_menggeser_indeks(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl.append_source(_record("A"))
    ctl.append_source(_record("B"))
    ctl.sections = [Section(1, "Bab", [Paragraph([Sentence("Klaim.", "q", [0, 1])])])]
    ctl._source_list.setCurrentRow(0)
    ctl._hapus_source()
    assert len(ctl.sources) == 1
    sentence = ctl.sections[0].paragraphs[0].sentences[0]
    assert sentence.source_ids == [0]
    assert ctl._source_list.count() == 1


def test_hapus_tanpa_pilih_memperingatkan(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    ctl._hapus_source()
    assert ctl._status.text() == "Pilih dulu sumbernya di daftar."


def test_tombol_generate_memancarkan_signal(qapp, db_tmp):
    ctl = _ctl(db_tmp)
    got = []
    ctl.generateRequested.connect(lambda: got.append(True))
    ctl._generate_button.click()
    assert got == [True]

def test_muat_draf_tidak_menimpa_sumber_di_disk(qapp, db_tmp):
    """Restore draf tidak boleh menulis ulang berkas dengan state setengah jadi."""
    fields = {"judul": "Laporan Y", "outline": "Pendahuluan", "template": "",
              "dosen": "", "matkul": "", "logo": ""}
    sections = report.sections_to_dicts(
        [Section(1, "Pendahuluan", [Paragraph([Sentence("Klaim faktual.", "kutipan", [0])])])]
    )
    drafts.save_draft(
        drafts.DraftState(draft_id="aktif", fields=fields, sources=[_record()], sections=sections, done=[])
    )
    _ctl(db_tmp)
    state = drafts.load_draft("aktif")
    assert len(state.sources) == 1, "sumber terhapus dari draf di disk saat load"
    assert len(state.sections) == 1, "isi laporan terhapus dari draf di disk saat load"
