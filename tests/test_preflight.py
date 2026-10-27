"""Tes engine pemeriksaan akhir (preflight) tanpa UI (addendum D.3)."""

from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.preflight import Check, PreflightIssue, find_issues, fix_mojibake, run_checks
from generator.verification import verify_sections

GOOD_QUOTE = "pertanian organik di indonesia sangat penting bagi petani"


def _fixture():
    sources = [Source([Author("NemÃ©nyi", "GÃ¡bor")], "2020", "Judul", "Jurnal")]
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [0])])])]
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
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")
    assert find_issues("Laporan Pertanian", sources, statuses, {0}, logo, style="dkk") == []


def test_pemeriksaan_menghormati_kalimat_yang_ditandai_selesai(tmp_path):
    sources = [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]
    sections = [Section(1, "Bab", [Paragraph([Sentence("Klaim.", "tidak ada", [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    done = frozenset({statuses[0].sentence.uid})
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")

    checks = run_checks("Laporan Pertanian", sources, statuses, {0}, logo, done=done)
    assert checks[0].ok is True, checks[0].detail
    assert find_issues("Laporan Pertanian", sources, statuses, {0}, logo, done=done) == []


def test_cek_konsistensi_menemukan_sitasi_di_luar_daftar_sumber():
    sources = [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [7])])])]
    statuses = verify_sections(sections, {7: GOOD_QUOTE})
    checks = run_checks("Laporan Pertanian", sources, statuses, {7}, None)
    konsistensi = checks[1]
    assert konsistensi.ok is False
    assert "di luar" in konsistensi.detail


def test_cek_konsistensi_menemukan_entri_tanpa_penulis_dan_judul():
    sources = [Source([], "", "")]
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    checks = run_checks("Laporan Pertanian", sources, statuses, {0}, None)
    assert checks[1].ok is False
    assert "tanpa penulis" in checks[1].detail


def test_cek_konsistensi_menemukan_entri_tanpa_judul():
    sources = [Source([Author("Santoso", "Budi")], "2020", "")]
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    checks = run_checks("Laporan Pertanian", sources, statuses, {0}, None)
    assert checks[1].ok is False
    assert "tanpa judul" in checks[1].detail



# --- Task 4.2: Validasi gaya sitasi di preflight -----------------------------


def test_gaya_sitasi_tidak_dikenal_menghasilkan_baris_gagal():
    sources, sections = _fixture()
    statuses = _verified_statuses(sources, sections)

    # 1. run_checks dengan gaya tidak dikenal menghasilkan check ok is False
    checks = run_checks("Laporan Pertanian", sources, statuses, {0}, None, style="apa7_custom")
    gaya_check = next(c for c in checks if c.label == "Gaya sitasi")
    assert gaya_check.ok is False
    assert "Tidak didukung" in gaya_check.detail

    # 2. find_issues juga mendeteksi citation_style issue
    issues = find_issues("Laporan Pertanian", sources, statuses, {0}, None, style="unknown_style")
    assert any(i.kind == "citation_style" for i in issues)


# --- Gerbang ekspor keras: dokumen belum layak dikumpulkan -------------------


def test_export_blockers_menolak_laporan_tanpa_isi():
    from generator.preflight import export_blockers

    blockers = export_blockers([Section(1, "BAB 1. PENDAHULUAN", [])], [])
    assert any("masih kosong" in blocker for blocker in blockers)


def test_export_blockers_menolak_penanda_tabel_yang_belum_diisi():
    from generator.preflight import export_blockers

    sections = [
        Section(1, "BAB 3. HASIL", [
            Paragraph([Sentence("[TABEL: Ringkasan hasil penelitian]", "", [], is_factual=False)])
        ])
    ]
    blockers = export_blockers(sections, ["Santoso, B. (2020). Judul. Jurnal."])
    assert any("[TABEL/GAMBAR/FOTO]" in blocker for blocker in blockers)


def test_export_blockers_menolak_bab_wajib_kosong():
    from generator.preflight import export_blockers

    sections = [
        Section(1, "BAB 1. PENDAHULUAN", [Paragraph([Sentence("Isi.", "q", [0])])]),
        Section(1, "BAB 2. TINJAUAN PUSTAKA", []),
    ]
    blockers = export_blockers(sections, ["Santoso, B. (2020). Judul. Jurnal."])
    assert any("bagian wajib masih kosong" in blocker for blocker in blockers)
    assert any("BAB 2" in blocker for blocker in blockers)


def test_export_blockers_menolak_sitasi_tanpa_daftar_pustaka():
    from generator.preflight import export_blockers

    sections = [Section(1, "BAB 1", [Paragraph([Sentence("Klaim faktual.", "q", [0])])])]
    blockers = export_blockers(sections, [])
    assert any("daftar pustaka kosong" in blocker for blocker in blockers)


def test_export_blockers_menerima_dokumen_lengkap():
    from generator.preflight import export_blockers

    sections = [Section(1, "BAB 1", [Paragraph([Sentence("Klaim faktual dengan bukti.", "q", [0])])])]
    assert export_blockers(sections, ["Santoso, B. (2020). Judul. Jurnal."]) == []

    # Bab induk tanpa paragraf sendiri tetap sah bila subbabnya berisi.
    sections = [
        Section(1, "BAB 1. PENDAHULUAN", []),
        Section(2, "1.1 Latar Belakang", [Paragraph([Sentence("Konteks masalah.", "q", [0])])]),
    ]
    assert export_blockers(sections, ["Santoso, B. (2020). Judul. Jurnal."]) == []


def test_pemeriksaan_menandai_sumber_tanpa_penulis():
    """Kasus ekstraksi gagal (judul dokumen masuk sebagai 'penulis')."""
    sources = [Source([], "2023", "Biochar dan Kesehatan Tanah", "Jurnal Tanah")]
    sections = [Section(1, "Bab", [Paragraph([Sentence(GOOD_QUOTE, GOOD_QUOTE, [0])])])]
    statuses = verify_sections(sections, {0: GOOD_QUOTE})
    checks = run_checks("Laporan", sources, statuses, {0}, None)
    konsisten = next(c for c in checks if c.label == "Sitasi & pustaka konsisten")
    assert konsisten.ok is False
    assert "tanpa penulis" in konsisten.detail


def test_judul_panjang_tidak_memicu_peringatan_nama_berkas():
    """Fase 3: nama berkas panjang dipotong rapi, bukan diperingatkan panjang."""
    judul = (
        "Pengaruh Media Sosial terhadap Prestasi Akademik Mahasiswa dalam "
        "Pembelajaran Jarak Jauh di Perguruan Tinggi Indonesia dan Malaysia"
    )
    checks = run_checks(judul, [], [], set(), None)
    nama = next(check for check in checks if check.label == "Nama berkas")
    assert nama.ok is True
    assert len(nama.detail) <= 80
    assert "filename" not in {issue.kind for issue in find_issues(judul, [], [], set(), None)}

