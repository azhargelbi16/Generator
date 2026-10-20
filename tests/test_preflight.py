"""Tes engine pemeriksaan akhir (preflight) tanpa UI (addendum D.3)."""

from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.preflight import Check, PreflightIssue, find_issues, fix_mojibake, run_checks
from generator.verification import verify_sections

GOOD_QUOTE = "pertanian organik di indonesia sangat penting bagi petani"


def _fixture():
    sources = [Source([Author("NemÃ©nyi", "GÃ¡bor")], "2020", "Judul", "Jurnal")]
    sections = [Section(1, "Bab", [Paragraph([Sentence("Klaim.", GOOD_QUOTE, [0])])])]
    return sources, sections


def _verified_statuses(sources, sections):
    return verify_sections(sections, {0: GOOD_QUOTE})


def test_find_issues_menangkap_mojibake_filename_dan_logo_kosong():
    sources, sections = _fixture()
    statuses = _verified_statuses(sources, sections)
    issues = find_issues("Laporan Pertanian 4.0", sources, statuses, {0}, None, style="et_al")
    kinds = {issue.kind for issue in issues}
    assert kinds == {"mojibake", "filename", "logo_missing"}


def test_run_checks_selalu_ada_dan_konsisten_selalu_ok():
    sources, sections = _fixture()
    statuses = _verified_statuses(sources, sections)
    checks = run_checks("Laporan Pertanian 4.0", sources, statuses, {0}, None, style="et_al")
    assert [check.label for check in checks] == [
        "Kalimat tertunda",
        "Sitasi & pustaka konsisten",
        "Nama berkas",
        "Nama penulis",
        "Logo",
        "Gaya sitasi",
    ]
    assert checks[0].ok is True  # semua kalimat lolos
    assert checks[1].ok is True and checks[1].detail
    assert checks[2].ok is False  # judul mengandung titik
    assert checks[3].ok is False  # nama penulis mojibake
    assert checks[4].ok is False  # logo kosong
    assert checks[5].ok is True and "et al." in checks[5].detail


def test_fix_mojibake_mengembalikan_salinan_baru():
    sources, sections = _fixture()
    new_sources, new_sections = fix_mojibake(sources, sections)
    assert new_sources is not sources and new_sections is not sections
    assert new_sources[0].authors[0].family == "Neményi"
    assert new_sources[0].authors[0].given == "Gábor"
    assert sources[0].authors[0].family == "NemÃ©nyi"  # objek asli tak berubah


def test_tanpa_temuan_find_issues_kosong(tmp_path):
    sources = [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]
    sections = [Section(1, "Bab", [Paragraph([Sentence("Klaim.", GOOD_QUOTE, [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")
    assert find_issues("Laporan Pertanian", sources, statuses, {0}, logo, style="dkk") == []
