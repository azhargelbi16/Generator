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



# --- Task 3.3: Backup sebelum migrasi ----------------------------------------


def test_migrasi_database_lama_dan_backup(tmp_path, monkeypatch):
    import sqlite3
    from generator.database import Database, Dosen, Profil, Template, backup_database

    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("generator.paths.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("generator.paths.DATA_DIR", tmp_path)

    db_path = tmp_path / "old.db"

    # 1. Buat database versi 1 lama secara manual dengan data profil, dosen, template
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE profil_mahasiswa (nama TEXT, nim TEXT, prodi TEXT);
        CREATE TABLE dosen (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, gelar TEXT, identitas TEXT);
        CREATE TABLE mata_kuliah (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, kode TEXT);
        CREATE TABLE logo (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, path TEXT);
        CREATE TABLE template (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, deskripsi TEXT, path TEXT);
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version (version) VALUES (1);

        INSERT INTO profil_mahasiswa (nama, nim, prodi) VALUES ('Mahasiswa Lama', 'NIM123', 'Ilmu Komputer');
        INSERT INTO dosen (nama, gelar, identitas) VALUES ('Dr. Dosen Lama', 'M.Sc', '19800101');
        INSERT INTO template (nama, deskripsi, path) VALUES ('Template Lama', 'Deskripsi template', 'tpl.docx');
    """)
    conn.commit()
    conn.close()

    # 2. Buka database dengan class Database dan panggil init_schema
    db = Database(db_path)
    assert db.schema_version() == 1
    db.init_schema(backup_dir=backup_dir)

    # Versi database kini sudah naik ke versi target (>= 2)
    assert db.schema_version() >= 2

    # 3. Buktikan berkas backup terbentuk di folder backup
    backup_files = list(backup_dir.glob("app-*.db"))
    assert len(backup_files) >= 1
    assert backup_files[0].is_file()

    # 4. Buktikan data profil, dosen, dan template tetap utuh
    profil = db.get_profil()
    assert profil.nama == "Mahasiswa Lama"
    assert profil.nim == "NIM123"
    assert profil.prodi == "Ilmu Komputer"

    dosen_list = db.list_dosen()
    assert len(dosen_list) == 1
    assert dosen_list[0].nama == "Dr. Dosen Lama"
    assert dosen_list[0].gelar == "M.Sc"

    tpl_list = db.list_template()
    assert len(tpl_list) == 1
    assert tpl_list[0].nama == "Template Lama"
    assert tpl_list[0].path == "tpl.docx"

    db.close()


def test_retensi_maksimal_10_berkas_backup(tmp_path):
    from generator.database import backup_database

    backup_dir = tmp_path / "backup"
    db_path = tmp_path / "test.db"
    db_path.write_text("dummy database content", encoding="utf-8")

    # Buat 13 backup berturut-turut
    for i in range(13):
        b_file = backup_database(db_path=db_path, backup_dir=backup_dir, max_retention=10)
        assert b_file is not None

    remaining = list(backup_dir.glob("app-*.db"))
    assert len(remaining) == 10
