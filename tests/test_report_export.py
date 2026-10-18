"""Tes gerbang ekspor: format tanggal dan pengisian fields (Task 17c)."""

from datetime import date

from generator import report


def test_format_tanggal_indonesian():
    assert report.format_tanggal(date(2026, 10, 18)) == "18 Oktober 2026"


def test_build_fields_fills_placeholders():
    f = report.build_fields("Judul", {"nama": "Budi", "nim": "1", "prodi": "Agro"},
                            "Dr. X", "Agronomi", date(2026, 10, 18))
    assert f["{{JUDUL}}"] == "Judul" and f["{{NAMA}}"] == "Budi"
    assert f["{{NIM}}"] == "1" and f["{{PRODI}}"] == "Agro"
    assert f["{{DOSEN}}"] == "Dr. X" and f["{{MATA_KULIAH}}"] == "Agronomi"
    assert f["{{TANGGAL}}"] == "18 Oktober 2026" and f["{{TAHUN}}"] == "2026"


def test_build_fields_omits_empty_optional():
    f = report.build_fields("J", {"nama": "B", "nim": "1", "prodi": ""},
                            "D", "M", date(2026, 1, 2))
    assert "{{PRODI}}" not in f  # renderer mengosongkan penandanya (18.5)
