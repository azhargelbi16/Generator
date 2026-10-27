import json
from pathlib import Path

from generator.ai.citation import Author, Source, in_text, reference, order_and_label


def A(family, given="", is_org=False, abbrev=""):
    return Author(family, given, is_org, abbrev)


def S(authors, year="2020", title="Judul", container="Jurnal", doi="", url=""):
    return Source(authors, year, title, container, doi, url)


def test_one_two_three_authors():
    assert in_text(S([A("Santoso", "Budi")])) == "(Santoso, 2020)"
    assert in_text(S([A("Santoso", "Budi"), A("Wijaya", "Ani")])) == "(Santoso & Wijaya, 2020)"
    assert in_text(S([A("Santoso", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")])) == "(Santoso et al., 2020)"


def test_no_year_is_nd():
    assert in_text(S([A("Sukarno")], year="")) == "(Sukarno, n.d.)"


def test_reference_lists_all_authors():
    r = reference(S([A("Santoso", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")], doi="10.1/x"))
    assert "Santoso, B." in r and "&" in r and "et al." not in r
    assert "(2020)" in r and "https://doi.org/10.1/x" in r


def test_twenty_one_authors():
    r = reference(S([A(f"Fam{i}", f"P{i}") for i in range(1, 22)]))
    assert "Fam1" in r and "Fam19" in r and "Fam20" not in r
    assert "…" in r and "&" not in r and "Fam21" in r


# --- APA 7: volume, nomor, halaman, dan italic -------------------------------


def test_reference_memuat_volume_nomor_dan_halaman():
    src = Source(
        [A("Santoso", "Budi")], "2024", "Judul Artikel", "Healthcare",
        volume="9", issue="10", pages="1272",
    )
    r = reference(src)
    assert "Healthcare, 9(10), 1272." in r


def test_reference_tanpa_volume_tetap_bentuk_lama():
    src = Source([A("Santoso", "Budi")], "2020", "Judul", "Jurnal Tanah")
    assert "Jurnal Tanah." in reference(src)


def test_reference_segments_memiringkan_container_dan_volume():
    src = Source(
        [A("Santoso", "Budi")], "2024", "Judul", "Healthcare",
        volume="9", issue="10", pages="1272",
    )
    from generator.ai.citation import reference_segments

    runs = reference_segments(src)
    italics = [text for text, italic in runs if italic]
    assert italics == ["Healthcare, 9"]
    assert any(text == "(10), 1272." and not italic for text, italic in runs)


def test_labeled_source_membawa_run_referensi():
    from generator.ai.citation import _join_runs

    labeled = order_and_label([S([A("Santoso", "Budi")], container="Jurnal")])
    runs = labeled[0].reference_runs
    assert _join_runs(runs) == labeled[0].reference
    assert any(italic for _, italic in runs)


def test_no_author_uses_title():
    assert reference(S([], title="Judul Tanpa Penulis")).startswith("Judul tanpa penulis")


def test_website_uses_url_when_no_doi():
    r = reference(S([A("Wijaya", "Ani")], title="T", container="", url="https://contoh.id/a"))
    assert "https://contoh.id/a" in r and "https://doi.org" not in r


def test_organization_with_abbrev():
    s = S([A("Kementerian Pertanian", is_org=True, abbrev="Kementan")])
    assert in_text(s, first_use=True) == "(Kementerian Pertanian [Kementan], 2020)"
    assert in_text(s, first_use=False) == "(Kementan, 2020)"


def test_organization_without_abbrev():
    assert in_text(S([A("Stanford University", is_org=True)])) == "(Stanford University, 2020)"


def test_single_word_author():
    assert in_text(S([A("Sukarno")])) == "(Sukarno, 2020)"


def test_order_is_alphabetical():
    labels = order_and_label([S([A("Zed")], title="Z"), S([A("Abadi", "T")], title="A")])
    assert labels[0].source.title == "A"
    assert labels[0].source_index == 1 and labels[1].source_index == 0


def test_labels_keyed_by_original_index_not_sorted_position():
    labels = order_and_label([S([A("Zed")], title="Z"), S([A("Abadi", "T")], title="A")])
    by_index = {l.source_index: l.source.title for l in labels}
    assert by_index == {0: "Z", 1: "A"}


def test_suffix_only_among_cited_sources():
    src = [S([A("Santoso", "Budi")], title="A"),
           S([A("Santoso", "Budi")], title="B"),
           S([A("Wijaya", "Ani")], year="2021", title="C")]
    labels = order_and_label(src, cite={0, 2})
    assert {l.source_index: l.suffix for l in labels} == {0: "", 2: ""}
    assert {l.source_index: l.in_text for l in labels}[0] == "(Santoso, 2020)"


def test_same_author_year_gets_suffix():
    labels = order_and_label([S([A("Santoso", "Budi")], title="B"),
                              S([A("Santoso", "Budi")], title="A")])
    assert {l.suffix for l in labels} == {"a", "b"}
    assert "2020a" in labels[0].in_text


def test_first_author_same_second_differs_disambiguates():
    a = S([A("Cooper", "A"), A("Lee", "B"), A("X", "C")], year="2015")
    b = S([A("Cooper", "A"), A("Ross", "Y"), A("X", "C")], year="2015")
    assert in_text(a, family_with=[a, b]) == "(Cooper, Lee, et al., 2015)"
    assert in_text(b, family_with=[a, b]) == "(Cooper, Ross, et al., 2015)"


# --- Task 1.5: gaya sitasi et al./dkk. --------------------------------------


def test_gaya_dkk_untuk_satu_dua_dan_tiga_penulis():
    one = S([A("Saleh", "Budi")], year="2023")
    two = S([A("Saleh", "Budi"), A("Wijaya", "Ani")], year="2023")
    three = S([A("Saleh", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")], year="2023")
    assert in_text(one, style="dkk") == "(Saleh, 2023)"
    assert in_text(two, style="dkk") == "(Saleh & Wijaya, 2023)"
    assert in_text(three, style="dkk") == "(Saleh dkk., 2023)"
    assert in_text(three) == "(Saleh et al., 2023)"


def test_labeled_source_menyediakan_bentuk_pendek_organisasi():
    org = S([A("Kementerian Pertanian", is_org=True, abbrev="Kementan")])
    (labeled,) = order_and_label([org], cite={0})
    assert labeled.in_text == "(Kementerian Pertanian [Kementan], 2020)"
    assert labeled.in_text_short == "(Kementan, 2020)"


def test_keluarga_sama_inisial_beda_memakai_inisial_di_teks():
    sources = [S([A("Santoso", "Budi")], "2020"), S([A("Santoso", "Ani")], "2021")]
    labels = {item.source_index: item.in_text for item in order_and_label(sources, cite={0, 1})}
    assert labels[0] == "(B. Santoso, 2020)"
    assert labels[1] == "(A. Santoso, 2021)"


def test_keluarga_sama_inisial_sama_tetap_tanpa_inisial_dan_berbedsufiks():
    sources = [S([A("Santoso", "Budi")], "2020"), S([A("Santoso", "Budi")], "2020")]
    labels = {item.source_index: item.in_text for item in order_and_label(sources, cite={0, 1})}
    assert labels[0] == "(Santoso, 2020a)"
    assert labels[1] == "(Santoso, 2020b)"


def test_gaya_dkk_organisasi_dan_sufiks_tetap():
    org = S([A("Kementerian Pertanian", is_org=True, abbrev="Kementan")])
    assert in_text(org, style="dkk") == "(Kementerian Pertanian [Kementan], 2020)"
    labels = order_and_label(
        [S([A("Saleh", "Budi")], title="B"), S([A("Saleh", "Budi")], title="A")],
        style="dkk",
    )
    assert {label.suffix for label in labels} == {"a", "b"}
    assert all("Saleh, 2020" in label.in_text for label in labels)


def test_gaya_dkk_pada_kasus_nama_bentrok():
    a = S([A("Cooper", "A"), A("Lee", "B"), A("X", "C")], year="2015")
    b = S([A("Cooper", "A"), A("Ross", "Y"), A("X", "C")], year="2015")
    assert in_text(a, family_with=[a, b], style="dkk") == "(Cooper, Lee, dkk., 2015)"


def test_labels_for_meneruskan_gaya_sitasi():
    from generator.report import labels_for

    sources = [S([A("Saleh", "Budi"), A("Wijaya", "Ani"), A("Lestari", "Cici")], year="2023")]
    assert labels_for(sources, {0}, style="dkk") == {0: "(Saleh dkk., 2023)"}
    assert labels_for(sources, {0}) == {0: "(Saleh et al., 2023)"}


# --- Fase 3: sentence case judul artikel daftar pustaka (APA 7, 17.2) --------

_SOURCES_FILE = Path(__file__).resolve().parents[1] / "scratch" / "student_run" / "final_sources.json"


def _source_from_entry(entry: dict) -> Source:
    from generator.ai.bibliography import _source_from_dict

    return _source_from_dict(entry)


def test_judul_artikel_sumber_nyata_sentence_case_apa7():
    """Tiga referensi MDPI/Liebert pada sumber e2e dikonversi sesuai APA 7."""
    data = json.loads(_SOURCES_FILE.read_text(encoding="utf-8"))
    refs = [reference(_source_from_entry(entry)) for entry in data]
    assert (
        "The wired generation: Academic and social outcomes of electronic media use "
        "among university students." in refs[0]
    )
    assert (
        "Social media improves students’ academic performance: Exploring the role of "
        "social media adoption in the open learning environment among international "
        "medical students in China." in refs[1]
    )
    assert (
        "The impact of social media use motives on students’ GPA: The mediating role "
        "of daily time usage." in refs[2]
    )
    # Nama jurnal (container) tidak ikut dikonversi.
    assert "Cyberpsychology, Behavior, and Social Networking" in refs[0]
    assert "Healthcare" in refs[1]


def test_sentence_case_judul_artikel_menghormati_akronim_dan_nama_diri():
    src = Source(
        [A("Santoso", "Budi")], "2024",
        "The Impact of COVID-19 on Public Health in Vietnam: A Review of WHO Guidance",
        "Jurnal Kesehatan",
    )
    assert (
        "The impact of COVID-19 on public health in Vietnam: A review of WHO guidance."
        in reference(src)
    )


def test_sentence_case_tidak_menyentuh_nama_jurnal():
    src = Source(
        [A("Santoso", "Budi")], "2024", "The Impact of Social Media",
        "Journal of Health Psychology",
    )
    assert "Journal of Health Psychology." in reference(src)




def test_sentence_case_menormalkan_judul_all_caps_dari_pdf():
    from generator.ai.citation import Source, Author, reference
    src = Source(
        [Author("Putra", "Rizki Aditya"), Author("Sadono", "Dwi")],
        "2024",
        "EXAMINING THE RELATIONSHIP BETWEEN INNOVATION CHARACTERISTICS AND EXTENSION SUPPORT WHEN USING JAJAR LEGOWO AS AN AGRICULTURAL INNOVATION",
        "Jurnal AGRISEP: Kajian Masalah Sosial Ekonomi Pertanian dan Agribisnis",
    )
    ref = reference(src)
    assert "Examining the relationship between innovation characteristics and extension support when using jajar legowo as an agricultural innovation." in ref
    assert "Jurnal AGRISEP: Kajian Masalah Sosial Ekonomi Pertanian dan Agribisnis." in ref
