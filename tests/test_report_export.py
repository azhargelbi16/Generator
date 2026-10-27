"""Tes gerbang ekspor: format tanggal dan pengisian fields (Task 17c)."""

from datetime import date

from generator import report


def test_format_tanggal_indonesian():
    assert report.format_tanggal(date(2026, 10, 18)) == "18 Oktober 2026"


def test_build_fields_fills_placeholders():
    f = report.build_fields("Judul", {"nama": "Budi", "nim": "1", "prodi": "Agro"},
                            "Dr. X", "Agronomi", date(2026, 10, 18))
    assert f["{{JUDUL}}"] == "Judul" and f["{{NAMA}}"] == "Budi"
    # Identitas sampul selalu kapital (PROGRAM STUDI AGROTEKNOLOGI, dst.)
    assert f["{{NIM}}"] == "1" and f["{{PRODI}}"] == "AGRO"
    assert f["{{DOSEN}}"] == "Dr. X" and f["{{MATA_KULIAH}}"] == "Agronomi"
    assert f["{{TANGGAL}}"] == "18 Oktober 2026" and f["{{TAHUN}}"] == "2026"


def test_build_fields_mengkapitalisasi_identitas_sampul():
    f = report.build_fields(
        "J", {"nama": "B", "nim": "1", "prodi": "Agroteknologi",
              "fakultas": "Pertanian", "institusi": "Universitas Jember"},
        "D", "M", date(2026, 10, 25),
    )
    assert f["{{PRODI}}"] == "AGROTEKNOLOGI"
    assert f["{{FAKULTAS}}"] == "PERTANIAN"
    assert f["{{INSTITUSI}}"] == "UNIVERSITAS JEMBER"


def test_build_fields_omits_empty_optional():
    f = report.build_fields("J", {"nama": "B", "nim": "1", "prodi": ""},
                            "D", "M", date(2026, 1, 2))
    assert "{{PRODI}}" not in f  # renderer mengosongkan penandanya (18.5)


def test_format_tanggal_teks_menerjemahkan_bulan_inggris():
    assert report.format_tanggal_teks("25 October 2026") == "25 Oktober 2026"
    assert report.format_tanggal_teks("1 January 2026") == "1 Januari 2026"


def test_format_tanggal_teks_membiarkan_format_lain():
    assert report.format_tanggal_teks("25 Oktober 2026") == "25 Oktober 2026"
    assert report.format_tanggal_teks("Oktober 2026") == "Oktober 2026"
    assert report.format_tanggal_teks("") == ""


def test_build_fields_menormalkan_tanggal_string_inggris():
    f = report.build_fields("Judul", {"nama": "Budi", "nim": "1"}, "Dr. X", "M",
                            "25 October 2026")
    assert f["{{TANGGAL}}"] == "25 Oktober 2026"
