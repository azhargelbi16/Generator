"""Tes modul intake: kebijakan penerimaan sumber untuk semua jalur masuk.

Success-path parity: record dari PDF/web/manual/DOI membawa bentuk kunci dan
kebijakan yang sama (ref, content_status, metadata precedence).
"""

import re
from pathlib import Path

from generator import database
from generator.ai.citation import Author, Source
from generator.sources import doi_resolver, intake
from generator.web.api_bridge import ApiBridge


def _crossref_msg():
    return {
        "title": ["Deep Phenology for Apple Flowers"],
        "author": [
            {"family": "Zhang", "given": "L."},
            {"name": "FAO"},
        ],
        "issued": {"date-parts": [[2021]]},
        "container-title": ["Computers and Electronics in Agriculture"],
        "DOI": "10.1016/j.compag.2021.106123",
        "URL": "https://doi.org/10.1016/j.compag.2021.106123",
    }


def test_source_from_crossref_message_lengkap():
    src = intake.source_from_crossref_message("10.1016/j.compag.2021.106123", _crossref_msg())
    assert src.title == "Deep Phenology for Apple Flowers"
    assert [a.family for a in src.authors] == ["Zhang", "FAO"]
    assert src.authors[0].is_org is False
    assert src.authors[1].is_org is True
    assert src.year == "2021"
    assert src.container == "Computers and Electronics in Agriculture"
    assert src.url.startswith("https://doi.org/")


def test_source_from_doi_record():
    record = {
        "title": "Judul Jurnal",
        "year": "2023",
        "container": "Jurnal Uji",
        "doi": "10.1234/abc",
        "url": "https://doi.org/10.1234/abc",
        "authors": [
            {"family": "Santoso", "given": "A.", "is_org": False, "abbrev": ""},
        ],
    }
    src = intake.source_from_doi_record(record)
    assert src is not None
    assert src.title == "Judul Jurnal"
    assert src.authors[0].family == "Santoso"

    assert intake.source_from_doi_record({"authors": []}) is None
    assert intake.source_from_doi_record(None) is None


def test_fast_doi_source(monkeypatch):
    record = {"title": "Judul", "year": "2023", "container": "", "doi": "10.1234/x",
              "url": "", "authors": [{"family": "Satu", "given": "", "is_org": False, "abbrev": ""}]}

    monkeypatch.setattr(doi_resolver, "fetch_doi_metadata", lambda doi: record)
    src = intake.fast_doi_source({"doi": "10.1234/x"}, "")
    assert src is not None and src.authors[0].family == "Satu"

    # DOI dari teks saat metadata tidak memuatnya
    src = intake.fast_doi_source({}, "Lihat https://doi.org/10.1234/x untuk detail.")
    assert src is not None

    # Tanpa DOI -> None
    assert intake.fast_doi_source({}, "tanpa doi sama sekali") is None

    # Gagal jaringan -> None (bukan exception)
    def boom(doi):
        raise ConnectionError("server down")

    monkeypatch.setattr(doi_resolver, "fetch_doi_metadata", boom)
    assert intake.fast_doi_source({"doi": "10.1234/x"}, "") is None


def test_ensure_title_dan_needs_enrichment():
    kosong = Source([], "", "", "", "", "")
    assert intake.ensure_title(kosong, "nama_berkas").title == "nama_berkas"
    berisi = Source([], "", "Judul Ada", "", "", "")
    assert intake.ensure_title(berisi, "fallback").title == "Judul Ada"

    assert intake.needs_enrichment(Source([], "", "T", "", "", "")) is True
    assert intake.needs_enrichment(Source([Author(family="S")], "", "T", "", "", "")) is False


def test_make_record_ref_dan_content_status():
    src = Source([Author(family="Santoso", given="A.")], "2024", "Judul", "", "", "")
    record = intake.make_record(src, "Teks sumber lengkap. " * 100, "pdf")
    assert record["kind"] == "pdf"
    assert record["ref"].startswith("pdf-")
    assert re.match(r"^pdf-\d{12}-\d+$", record["ref"])
    assert record["content_status"] == "fulltext"
    assert record["text"].startswith("Teks sumber")


def test_metadata_precedence_doc_menang_atas_ai():
    ai = Source([Author(family="Ai", given="X.")], "1999", "Judul AI", "Jurnal AI", "", "")
    doc_meta = {"title": "Judul Dokumen", "year": "2025"}
    merged = intake.merge_metadata(ai, doc_meta)
    assert merged.title == "Judul Dokumen"
    assert merged.year == "2025"
    # Penulis tetap dari AI (tidak pernah ditebak dari string mentah)
    assert merged.authors[0].family == "Ai"


# --- Parity jalur masuk lewat ApiBridge --------------------------------------


def _bridge(tmp_path: Path):
    db = database.Database(tmp_path / "t.db")
    db.init_schema()
    return db, ApiBridge(db, config_path=tmp_path / "config.json")


def test_parity_manual_dengan_doi_tercepat(tmp_path: Path, monkeypatch):
    record = {"kind": "doi", "title": "Judul DOI", "year": "2023", "container": "Jurnal",
              "doi": "10.1234/y", "url": "https://doi.org/10.1234/y",
              "authors": [{"family": "Dua", "given": "", "is_org": False, "abbrev": ""}],
              "text": "Teks sumber cukup panjang untuk dihitung fulltext. " * 30}
    monkeypatch.setattr(doi_resolver, "fetch_doi_metadata", lambda doi: record)

    db, bridge = _bridge(tmp_path)
    try:
        res = bridge.add_manual_source("Kajian ini merujuk https://doi.org/10.1234/y sebagai dasar.")
        assert res["success"] is True
        rec = res["record"]
        # Parity bentuk dengan record DOI langsung
        for key in ("kind", "title", "year", "container", "doi", "url",
                    "authors", "text", "content_status", "ref"):
            assert key in rec
        assert rec["title"] == "Judul DOI"
        assert rec["authors"][0]["family"] == "Dua"
        assert rec["ref"].startswith("manual-")
        # Penulis ada -> tidak perlu enrichment (tidak ada event)
        assert intake.needs_enrichment(
            intake.source_from_doi_record(rec)) is False
    finally:
        db.close()


def test_parity_manual_tanpa_doi_fallback_dan_enrichment(tmp_path: Path, monkeypatch):
    from generator.ai import bibliography as bib

    def fail_extract(text, cl):
        raise bib.BibliographyError("AI tidak tersedia saat pengujian")

    monkeypatch.setattr(bib, "extract_source", fail_extract)

    db, bridge = _bridge(tmp_path)
    try:
        res = bridge.add_manual_source("Teks manual tanpa DOI di dalamnya. " * 120)
        assert res["success"] is True
        rec = res["record"]
        assert rec["title"] == "Teks Manual"
        assert rec["ref"].startswith("manual-")
        assert rec["content_status"] == "fulltext"
    finally:
        db.close()


def test_parity_resolve_doi_langsung(tmp_path: Path, monkeypatch):
    record = {"kind": "doi", "title": "Judul Langsung", "year": "2022", "container": "J",
              "doi": "10.9/z", "url": "", "authors": [],
              "text": "Abstrak resmi dari penerbit.", "content_status": "abstract"}
    monkeypatch.setattr(doi_resolver, "fetch_doi_metadata", lambda doi: record)

    db, bridge = _bridge(tmp_path)
    try:
        res = bridge.resolve_doi_source("10.9/z")
        assert res["success"] is True
        rec = res["record"]
        assert rec["kind"] == "doi"
        assert rec["content_status"] == "abstract"
        assert rec["title"] == "Judul Langsung"
    finally:
        db.close()


# --- Data bibliografis CrossRef (APA 7) --------------------------------------


def test_crossref_message_mengambil_volume_issue_page():
    msg = dict(_crossref_msg())
    msg.update({"volume": "9", "issue": "10", "page": "1272-1281"})
    src = intake.source_from_crossref_message("10.1016/j.compag.2021.106123", msg)
    assert (src.volume, src.issue, src.pages) == ("9", "10", "1272-1281")


def test_record_bolak_balik_volume_issue_pages():
    from generator.sources.records import record_to_source, source_to_record

    src = Source(
        [Author("Santoso", "Budi")], "2024", "Judul", "Healthcare",
        volume="9", issue="10", pages="1272",
    )
    record = source_to_record(src, "teks sumber", "doi")
    assert (record["volume"], record["issue"], record["pages"]) == ("9", "10", "1272")

    back = record_to_source(record)
    assert (back.volume, back.issue, back.pages) == ("9", "10", "1272")


def test_record_lama_tanpa_volume_tetap_valid():
    from generator.sources.records import record_to_source

    back = record_to_source({"title": "Judul", "year": "2020", "authors": []})
    assert (back.volume, back.issue, back.pages) == ("", "", "")
