"""Lapisan SQLite: profil mahasiswa, dosen, mata kuliah, logo, dan template (7, 20)."""

from __future__ import annotations

import sqlite3
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import paths

SCHEMA_VERSION = 3


def _migration_1_to_2(conn: sqlite3.Connection) -> None:
    """Migrasi 1 -> 2: Buat indeks pencarian untuk template dan dosen."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_template_nama ON template(nama)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dosen_nama ON dosen(nama)")


def _migration_2_to_3(conn: sqlite3.Connection) -> None:
    """Migrasi 2 -> 3: Tambah kolom fakultas dan institusi pada profil_mahasiswa."""
    try:
        conn.execute("ALTER TABLE profil_mahasiswa ADD COLUMN fakultas TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE profil_mahasiswa ADD COLUMN institusi TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass


MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    2: _migration_1_to_2,
    3: _migration_2_to_3,
}


def backup_database(
    db_path: Path | None = None,
    backup_dir: Path | None = None,
    max_retention: int = 10,
) -> Path | None:
    """Salin app.db ke data/backup/app-YYYYMMDD-HHMMSS.db sebelum migrasi.

    Retensi maksimal `max_retention` (bawaan 10) berkas backup.
    """
    if db_path is None:
        db_path = paths.DB_PATH
    db_path = Path(db_path)
    if not db_path.is_file():
        return None

    if backup_dir is None:
        backup_dir = paths.DATA_DIR / "backup"
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = backup_dir / f"app-{timestamp}.db"
    counter = 1
    while backup_file.exists():
        backup_file = backup_dir / f"app-{timestamp}-{counter}.db"
        counter += 1

    shutil.copy2(db_path, backup_file)
    _enforce_backup_retention(backup_dir, max_retention=max_retention)
    return backup_file


def _enforce_backup_retention(backup_dir: Path, max_retention: int = 10) -> None:
    """Hapus berkas backup terlama bila jumlah berkas melebihi batas retensi."""
    backups = sorted(
        backup_dir.glob("app-*.db"),
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    while len(backups) > max_retention:
        oldest = backups.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profil_mahasiswa (
    nama TEXT NOT NULL DEFAULT '',
    nim TEXT NOT NULL DEFAULT '',
    prodi TEXT NOT NULL DEFAULT '',
    fakultas TEXT NOT NULL DEFAULT '',
    institusi TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS dosen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL DEFAULT '',
    gelar TEXT NOT NULL DEFAULT '',
    identitas TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS mata_kuliah (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL DEFAULT '',
    kode TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS logo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL DEFAULT '',
    deskripsi TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


@dataclass
class Profil:
    nama: str = ""
    nim: str = ""
    prodi: str = ""
    fakultas: str = ""
    institusi: str = ""


@dataclass
class Dosen:
    id: int
    nama: str
    gelar: str = ""
    identitas: str = ""


@dataclass
class MataKuliah:
    id: int
    nama: str
    kode: str = ""


@dataclass
class Logo:
    id: int
    nama: str
    path: str = ""


@dataclass
class Template:
    id: int
    nama: str
    deskripsi: str = ""
    path: str = ""


class Database:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self, backup_dir: Path | None = None) -> None:
        """Inisialisasi tabel dasar dan jalankan migrasi berurutan bila diperlukan."""
        current_v = self.schema_version()
        has_tables = bool(
            self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='profil_mahasiswa'"
            ).fetchone()
        )
        if not has_tables:
            self.conn.executescript(_SCHEMA)
            self.conn.execute("INSERT INTO schema_version (version) VALUES (1)")
            self.conn.commit()
            current_v = 1

        if current_v < SCHEMA_VERSION:
            self.run_migrations(target_version=SCHEMA_VERSION, backup_dir=backup_dir)

    def schema_version(self) -> int:
        try:
            row = self.conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            if row and row["v"] is not None:
                return int(row["v"])
        except sqlite3.OperationalError:
            pass
        return 0

    def run_migrations(
        self, target_version: int = SCHEMA_VERSION, backup_dir: Path | None = None
    ) -> None:
        """Bandingkan versi, buat backup, dan jalankan migrasi berurutan."""
        current_v = self.schema_version()
        if current_v >= target_version:
            return

        # Backup database sebelum migrasi
        self.conn.commit()
        backup_database(self.db_path, backup_dir=backup_dir)

        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        for v in range(current_v + 1, target_version + 1):
            if v in MIGRATIONS:
                MIGRATIONS[v](self.conn)
            self.conn.execute("INSERT INTO schema_version (version) VALUES (?)", (v,))
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _insert(self, table: str, columns: list[str], values: list) -> int:
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return int(cur.lastrowid)

    def _update_row(self, table: str, row_id: int, columns: list[str], values: list) -> None:
        assignments = ", ".join(f"{c} = ?" for c in columns)
        self.conn.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", [*values, row_id])
        self.conn.commit()

    def _delete_row(self, table: str, row_id: int) -> None:
        self.conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        self.conn.commit()

    def _list_rows(self, table: str, factory: Callable[[sqlite3.Row], object]) -> list:
        rows = self.conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        return [factory(row) for row in rows]

    # Profil mahasiswa (baris tunggal)
    def get_profil(self) -> Profil:
        try:
            row = self.conn.execute(
                "SELECT nama, nim, prodi, fakultas, institusi FROM profil_mahasiswa LIMIT 1"
            ).fetchone()
        except sqlite3.OperationalError:
            row = self.conn.execute(
                "SELECT nama, nim, prodi FROM profil_mahasiswa LIMIT 1"
            ).fetchone()
        if row is None:
            return Profil()
        keys = row.keys() if hasattr(row, "keys") else []
        return Profil(
            nama=row["nama"],
            nim=row["nim"],
            prodi=row["prodi"],
            fakultas=row["fakultas"] if "fakultas" in keys else "",
            institusi=row["institusi"] if "institusi" in keys else "",
        )

    def set_profil(self, p: Profil) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM profil_mahasiswa")
        try:
            cur.execute(
                "INSERT INTO profil_mahasiswa (nama, nim, prodi, fakultas, institusi) VALUES (?, ?, ?, ?, ?)",
                (p.nama, p.nim, p.prodi, p.fakultas, p.institusi),
            )
        except sqlite3.OperationalError:
            cur.execute(
                "INSERT INTO profil_mahasiswa (nama, nim, prodi) VALUES (?, ?, ?)",
                (p.nama, p.nim, p.prodi),
            )
        self.conn.commit()

    # Dosen
    def add_dosen(self, d: Dosen) -> int:
        return self._insert("dosen", ["nama", "gelar", "identitas"], [d.nama, d.gelar, d.identitas])

    def list_dosen(self) -> list[Dosen]:
        return self._list_rows("dosen", lambda r: Dosen(r["id"], r["nama"], r["gelar"], r["identitas"]))

    def update_dosen(self, d: Dosen) -> None:
        self._update_row("dosen", d.id, ["nama", "gelar", "identitas"], [d.nama, d.gelar, d.identitas])

    def delete_dosen(self, row_id: int) -> None:
        self._delete_row("dosen", row_id)

    # Mata kuliah
    def add_mata_kuliah(self, m: MataKuliah) -> int:
        return self._insert("mata_kuliah", ["nama", "kode"], [m.nama, m.kode])

    def list_mata_kuliah(self) -> list[MataKuliah]:
        return self._list_rows("mata_kuliah", lambda r: MataKuliah(r["id"], r["nama"], r["kode"]))

    def update_mata_kuliah(self, m: MataKuliah) -> None:
        self._update_row("mata_kuliah", m.id, ["nama", "kode"], [m.nama, m.kode])

    def delete_mata_kuliah(self, row_id: int) -> None:
        self._delete_row("mata_kuliah", row_id)

    # Logo
    def add_logo(self, item: Logo) -> int:
        return self._insert("logo", ["nama", "path"], [item.nama, item.path])

    def list_logo(self) -> list[Logo]:
        return self._list_rows("logo", lambda r: Logo(r["id"], r["nama"], r["path"]))

    def update_logo(self, item: Logo) -> None:
        self._update_row("logo", item.id, ["nama", "path"], [item.nama, item.path])

    def delete_logo(self, row_id: int) -> None:
        self._delete_row("logo", row_id)

    # Template
    def add_template(self, t: Template) -> int:
        return self._insert("template", ["nama", "deskripsi", "path"], [t.nama, t.deskripsi, t.path])

    def list_template(self) -> list[Template]:
        return self._list_rows(
            "template", lambda r: Template(r["id"], r["nama"], r["deskripsi"], r["path"])
        )

    def update_template(self, t: Template) -> None:
        self._update_row("template", t.id, ["nama", "deskripsi", "path"], [t.nama, t.deskripsi, t.path])

    def delete_template(self, row_id: int) -> None:
        self._delete_row("template", row_id)
