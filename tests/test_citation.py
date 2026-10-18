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


def test_no_author_uses_title():
    assert reference(S([], title="Judul Tanpa Penulis")).startswith("Judul Tanpa Penulis")


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
