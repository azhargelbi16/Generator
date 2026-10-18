from generator.database import Database, Dosen, Profil


def test_profil_roundtrip(tmp_path):
    db = Database(tmp_path / "t.db")
    db.init_schema()
    db.set_profil(Profil("Budi", "123", "Agroteknologi"))
    assert db.get_profil().prodi == "Agroteknologi"
    assert db.get_profil().nama == "Budi"


def test_add_update_delete_dosen(tmp_path):
    db = Database(tmp_path / "t.db")
    db.init_schema()
    rid = db.add_dosen(Dosen(0, "Budi", "", ""))
    db.update_dosen(Dosen(rid, "Budi Santoso", "S.P.", ""))
    assert db.list_dosen()[0].nama == "Budi Santoso"
    db.delete_dosen(rid)
    assert db.list_dosen() == []


def test_schema_version_recorded(tmp_path):
    db = Database(tmp_path / "t.db")
    db.init_schema()
    assert db.schema_version() >= 1
