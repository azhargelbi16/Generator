"""Tes tab Template Qt: parity validasi + panel penanda terdeteksi (Task 2.4)."""

from docx import Document

from generator import paths
from generator.document import template as template_mod


def _make_docx(path, markers):
    doc = Document()
    for marker in markers:
        doc.add_paragraph(marker)
    doc.save(path)


def _tab(db_tmp):
    from generator.qt.tab_template import TemplateTab

    return TemplateTab(db_tmp)


def test_import_lengkap_status_disimpan(qapp, db_tmp, tmp_path):
    src = tmp_path / "laporan.docx"
    _make_docx(src, template_mod.REQUIRED_PLACEHOLDERS)
    tab = _tab(db_tmp)
    assert tab._import_template(src, nama="Laporan", deskripsi="Standar") is True
    assert tab._status.text() == "Template 'Laporan' disimpan."
    assert len(db_tmp.list_template()) == 1
    assert (paths.TEMPLATES_DIR / "laporan.docx").is_file()
    assert tab._table.rowCount() == 1
    assert "lengkap" in tab._table.item(0, 1).text()


def test_import_kurang_penanda_tetap_disimpan_dengan_pesan(qapp, db_tmp, tmp_path):
    src = tmp_path / "min.docx"
    _make_docx(src, ["{{JUDUL}}", "{{NAMA}}"])
    tab = _tab(db_tmp)
    assert tab._import_template(src, nama="Min") is True
    assert "tidak lengkap" in tab._table.item(0, 1).text()
    assert "kurang" in tab._table.item(0, 1).text()
    assert "Penanda wajib yang kurang" in tab._last_message


def test_import_berkas_rusak_ditolak(qapp, db_tmp, tmp_path):
    src = tmp_path / "rusak.docx"
    src.write_bytes(b"bukan docx")
    tab = _tab(db_tmp)
    assert tab._import_template(src, nama="X") is False
    assert db_tmp.list_template() == []
    assert "tidak valid" in tab._last_message


def test_tabrakan_nama_memakai_suffix_angka(qapp, db_tmp, tmp_path):
    src = tmp_path / "a.docx"
    _make_docx(src, template_mod.REQUIRED_PLACEHOLDERS)
    tab = _tab(db_tmp)
    assert tab._import_template(src, nama="A")
    assert tab._import_template(src, nama="A2")
    files = sorted(p.name for p in paths.TEMPLATES_DIR.iterdir())
    assert files == ["a.docx", "a_1.docx"]
    assert len(db_tmp.list_template()) == 2


def test_hapus_menghilangkan_baris_dan_berkas(qapp, db_tmp, tmp_path):
    src = tmp_path / "a.docx"
    _make_docx(src, template_mod.REQUIRED_PLACEHOLDERS)
    tab = _tab(db_tmp)
    tab._import_template(src, nama="A")
    tab._table.selectRow(0)
    tab._delete()
    assert db_tmp.list_template() == []
    assert tab._table.rowCount() == 0
    assert not (paths.TEMPLATES_DIR / "a.docx").exists()
    assert tab._status.text() == "Template 'A' dihapus."


def test_hapus_tanpa_pilih_memperingatkan(qapp, db_tmp):
    tab = _tab(db_tmp)
    tab._delete()
    assert tab._status.text() == "Pilih template yang akan dihapus."


def test_status_berkas_hilang_dihitung_ulang(qapp, db_tmp, tmp_path):
    src = tmp_path / "a.docx"
    _make_docx(src, template_mod.REQUIRED_PLACEHOLDERS)
    tab = _tab(db_tmp)
    tab._import_template(src, nama="A")
    (paths.TEMPLATES_DIR / "a.docx").unlink()
    tab.refresh()
    assert "berkas hilang" in tab._table.item(0, 1).text()


def test_panel_penanda_terdeteksi_urut_abjad(qapp, db_tmp, tmp_path):
    src = tmp_path / "a.docx"
    _make_docx(src, ["{{ZZZ_UNKNOWN}}", "{{JUDUL}}", "{{NAMA}}"])
    tab = _tab(db_tmp)
    tab._import_template(src, nama="A")
    tab._table.selectRow(0)
    assert tab._detected_placeholder_texts() == sorted(
        ["{{JUDUL}}", "{{NAMA}}", "{{ZZZ_UNKNOWN}}"]
    )
