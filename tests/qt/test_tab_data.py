"""Tes tab Data Qt: parity CRUD Tk + tabel cari + pratinjau logo (Task 2.3)."""

import base64

from generator.database import Dosen

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _make_tab(db_tmp):
    from generator.qt.tab_data import DataTab

    return DataTab(db_tmp)


def test_subtab_nama_persis_seperti_tk(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    names = [tab.inner.tabText(i) for i in range(tab.inner.count())]
    assert names == ["Profil Mahasiswa", "Dosen", "Mata Kuliah", "Logo"]


def test_profil_simpan_parity(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    form = tab.profil_form
    form._vars["nama"].setText("Budi")
    form._vars["nim"].setText("12345")
    form._vars["prodi"].setText("Agroteknologi")
    form._save()
    profil = db_tmp.get_profil()
    assert (profil.nama, profil.nim, profil.prodi) == ("Budi", "12345", "Agroteknologi")
    assert form._status.text() == "Profil tersimpan."


def test_dosen_tambah_memperbarui_tabel_dan_db(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    panel = tab.dosen_panel
    panel._vars["nama"].setText("Dr. Sitohang")
    panel._vars["gelar"].setText("S.T., M.T.")
    panel._vars["identitas"].setText("19800101")
    panel._add()
    assert panel._status.text() == "Ditambahkan."
    assert panel._table.rowCount() == 1
    dosen = db_tmp.list_dosen()
    assert len(dosen) == 1
    assert dosen[0].nama == "Dr. Sitohang"
    assert dosen[0].gelar == "S.T., M.T."


def test_tambah_kosong_ditolak_parity(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    panel = tab.dosen_panel
    panel._add()
    assert panel._status.text() == "Isi minimal satu kolom."
    assert panel._table.rowCount() == 0
    assert db_tmp.list_dosen() == []


def test_update_tanpa_pilih_ditolak_parity(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    panel = tab.matkul_panel
    panel._update()
    assert panel._status.text() == "Pilih baris dulu."
    panel._delete()
    assert panel._status.text() == "Pilih baris dulu."


def test_update_dan_delete_dosen_parity(qapp, db_tmp):
    db_tmp.add_dosen(Dosen(0, "Lama", "", "1"))
    tab = _make_tab(db_tmp)
    panel = tab.dosen_panel
    panel._table.selectRow(0)
    panel._vars["nama"].setText("Baru")
    panel._update()
    assert db_tmp.list_dosen()[0].nama == "Baru"
    assert panel._status.text() == "Diubah."
    panel._table.selectRow(0)
    panel._delete()
    assert db_tmp.list_dosen() == []
    assert panel._status.text() == "Dihapus."


def test_mata_kuliah_tambah_dengan_kode(qapp, db_tmp):
    tab = _make_tab(db_tmp)
    panel = tab.matkul_panel
    panel._vars["nama"].setText("Agroekologi")
    panel._vars["kode"].setText("AGT101")
    panel._add()
    mk = db_tmp.list_mata_kuliah()[0]
    assert (mk.nama, mk.kode) == ("Agroekologi", "AGT101")
    assert panel._table.rowCount() == 1


def test_filter_realtime_menyembunyikan_baris(qapp, db_tmp):
    db_tmp.add_dosen(Dosen(0, "Dr. Sitohang", "", "1"))
    db_tmp.add_dosen(Dosen(0, "Dr. Manurung", "", "2"))
    tab = _make_tab(db_tmp)
    panel = tab.dosen_panel
    assert panel._table.rowCount() == 2
    panel._filter.setText("sit")
    assert panel._table.isRowHidden(0) is False
    assert panel._table.isRowHidden(1) is True
    panel._filter.setText("")
    assert panel._table.isRowHidden(1) is False


def test_logo_pratinjau_punya_pixmap(qapp, db_tmp, tmp_path):
    png = tmp_path / "logo.png"
    png.write_bytes(_PNG)
    tab = _make_tab(db_tmp)
    panel = tab.logo_panel
    panel._vars["nama"].setText("Kampus")
    panel._vars["path"].setText(str(png))
    panel._add()
    assert panel._status.text() == "Ditambahkan."
    assert len(db_tmp.list_logo()) == 1
    panel._table.selectRow(0)  # pilih baris -> form terisi -> pratinjau tampil
    assert panel._preview.pixmap() is not None
    assert not panel._preview.pixmap().isNull()
