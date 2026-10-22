"""Tes inti report: gerbang ekspor, pending, sitasi, label, dan referensi (Task 17a)."""

from generator.report import (can_export, pending, references_for, labels_for,
    uncited_ids, non_factual_uids, cited_ids, display_text)
from generator.verification import verify_sections, STATUS_VERIFIED
from generator.ai.content import Sentence, Paragraph, Section
from generator.ai.citation import Author, Source

GOOD = "pertanian organik di indonesia sangat penting bagi petani"


def test_can_export_blocks_when_unverified():
    s = Section(1, "B", [Paragraph([Sentence("x", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: "teks lain sama sekali berbeda dan tidak berkaitan lagi"})
    ok, msg = can_export(st)
    assert ok is False and msg


def test_can_export_allows_when_verified():
    s = Section(1, "B", [Paragraph([Sentence(GOOD, GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert can_export(st) == (True, "")


def test_pending_excludes_verified_sentences():
    s = Section(1, "B", [Paragraph([Sentence(GOOD, GOOD, [0]),
                                    Sentence("y", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: GOOD})
    assert st[0].status == STATUS_VERIFIED
    assert pending(st, frozenset()) == [1]


def test_non_factual_blocks_until_marked_done():
    s = Section(1, "B", [Paragraph([Sentence("Bab ini membahas.", is_factual=False)])])
    st = verify_sections([s], {})
    assert can_export(st)[0] is False
    assert can_export(st, done=frozenset({st[0].sentence.uid}))[0] is True


def test_done_keyed_by_stable_uid_survives_insertion():
    a = Sentence("kalimat asli.", is_factual=False)
    st = verify_sections([Section(1, "B", [Paragraph([a])])], {})
    done = frozenset({st[0].sentence.uid})
    assert can_export(st, done=done)[0] is True

    st2 = verify_sections([Section(1, "B", [Paragraph([Sentence("kalimat baru.", is_factual=False), a])])], {})
    assert st2[1].sentence.uid == a.uid
    assert pending(st2, done) == [0]


def test_non_factual_uids_for_bulk_mark():
    s = Section(1, "B", [Paragraph([Sentence("pengantar.", is_factual=False),
                                    Sentence(GOOD, GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert non_factual_uids(st) == [st[0].sentence.uid]
    assert can_export(st, done=frozenset(non_factual_uids(st)))[0] is True


def test_cited_ids_collects_referenced_sources():
    s = Section(1, "B", [Paragraph([Sentence(GOOD, GOOD, [0, 1]),
                                    Sentence("y", is_factual=False)])])
    st = verify_sections([s], {0: GOOD})
    assert cited_ids(st) == {0, 1}


def test_cited_ids_ignores_citation_suppressed():
    s = Section(1, "B", [Paragraph([Sentence(GOOD, GOOD, [0], citation=False),
                                    Sentence(GOOD, GOOD, [1])])])
    st = verify_sections([s], {0: GOOD, 1: GOOD})
    assert cited_ids(st) == {1}


def test_references_only_cited_sources():
    src = [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "U", "J")]
    refs = references_for(src, {0})
    assert len(refs) == 1 and uncited_ids(src, {0}) == [1]


def test_labels_keyed_by_original_source_index():
    src = [Source([Author("Zed")], "2020", "Z", "J"),
           Source([Author("Abadi", "T")], "2020", "A", "J")]
    labels = labels_for(src, {0, 1})
    assert set(labels) == {0, 1}
    assert labels[0].startswith("(Zed") and labels[1].startswith("(Abadi")


def test_labels_no_suffix_from_uncited_source():
    src = [Source([Author("Santoso", "Budi")], "2020", "A", "J"),
           Source([Author("Santoso", "Budi")], "2020", "B", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "C", "J")]
    labels = labels_for(src, {0, 2})
    assert labels[0] == "(Santoso, 2020)" and labels[2] == "(Wijaya, 2021)"


def test_display_text_menambah_sitasi_sebelum_tanda_baca():
    s = Sentence("Hal ini membahayakan alam.", "q", [0, 1])
    assert display_text(s, {0: "(Sugiyono, 2025)", 1: "(Wijaya, 2021)"}) == (
        "Hal ini membahayakan alam (Sugiyono, 2025; Wijaya, 2021)."
    )


def test_display_text_tanpa_sumber_dikenal_tanpa_sitasi():
    s = Sentence("Kalimat polos.", "q", [99])
    assert display_text(s, {}) == "Kalimat polos."


def test_display_text_menghormati_flag_citation_dan_nonfactual():
    assert display_text(Sentence("A.", citation=False), {0: "(X, 2020)"}) == "A."
    assert display_text(Sentence("B.", is_factual=False), {0: "(X, 2020)"}) == "B."


def test_display_text_faktual_tanpa_sitasi_tetap_polos():
    assert display_text(Sentence("Faktual tanpa sitasi."), {0: "(X, 2020)"}) == (
        "Faktual tanpa sitasi."
    )


# --- Task 1.6: sanitasi nama berkas ------------------------------------------


def test_sanitize_filename_titik_jadi_garis_bawah():
    from generator.report import sanitize_filename

    assert sanitize_filename("Pertanian 4.0 untuk Produksi") == "Pertanian_4_0_untuk_Produksi"


def test_sanitize_filename_hapus_karakter_ilegal_windows():
    from generator.report import sanitize_filename

    assert sanitize_filename('tes<>:"/\\|?*nama') == "tesnama"


def test_sanitize_filename_potong_80_karakter():
    from generator.report import sanitize_filename

    assert len(sanitize_filename("a" * 200)) == 80


def test_sanitize_filename_kosong_jadi_laporan():
    from generator.report import sanitize_filename

    assert sanitize_filename("") == "laporan"
    assert sanitize_filename("   ...") == "laporan"


def test_sanitize_filename_buang_karakter_kontrol():
    from generator.report import sanitize_filename

    assert sanitize_filename("judul\x00kontrol\x1f") == "judulkontrol"


def test_sanitize_filename_nama_reserved_windows_diberi_akhiran():
    from generator.report import sanitize_filename

    assert sanitize_filename("CON") == "CON_"
    assert sanitize_filename("lpt1") == "lpt1_"
    assert sanitize_filename("Laporan CON") == "Laporan_CON"
