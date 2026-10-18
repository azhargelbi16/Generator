"""Lapisan SQLite: profil mahasiswa, dosen, mata kuliah, logo, dan template (7, 20)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profil_mahasiswa (
    nama TEXT NOT NULL DEFAULT '',
    nim TEXT NOT NULL DEFAULT '',
    prodi TEXT NOT NULL DEFAULT ''
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

    def init_schema(self) -> None:
        cur = self.conn.executescript(_SCHEMA)
        row = cur.execute("SELECT COUNT(*) AS n FROM schema_version").fetchone()
        if row["n"] == 0:
            cur.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        self.conn.commit()

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        return int(row["v"] or 0)

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
        row = self.conn.execute(
            "SELECT nama, nim, prodi FROM profil_mahasiswa LIMIT 1"
        ).fetchone()
        if row is None:
            return Profil()
        return Profil(row["nama"], row["nim"], row["prodi"])

    def set_profil(self, p: Profil) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM profil_mahasiswa")
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
