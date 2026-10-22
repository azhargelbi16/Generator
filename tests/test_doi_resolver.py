from unittest.mock import MagicMock
from generator.sources import doi_resolver


def test_extract_doi():
    assert doi_resolver.extract_doi("10.1016/j.jclepro.2021.129342") == "10.1016/j.jclepro.2021.129342"
    assert doi_resolver.extract_doi("https://doi.org/10.1038/s41586-020-2649-2.") == "10.1038/s41586-020-2649-2"
    assert doi_resolver.extract_doi("teks acak tanpa doi") is None


def test_fetch_doi_metadata_mock(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {
            "title": ["Penelitian Biochar Presisi"],
            "author": [
                {"family": "Santoso", "given": "Budi"},
                {"name": "Badan Riset Nasional"}
            ],
            "issued": {"date-parts": [[2023, 5, 10]]},
            "container-title": ["Jurnal Pertanian"],
            "DOI": "10.1234/jp.2023.01",
            "URL": "https://doi.org/10.1234/jp.2023.01",
            "abstract": "<jats:p>Biochar meningkatkan kesuburan tanah secara signifikan.</jats:p>"
        }
    }

    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    rec = doi_resolver.fetch_doi_metadata("10.1234/jp.2023.01")
    assert rec["title"] == "Penelitian Biochar Presisi"
    assert len(rec["authors"]) == 2
    assert rec["authors"][0]["family"] == "Santoso"
    assert rec["authors"][1]["is_org"] is True
    assert rec["year"] == "2023"
    assert rec["container"] == "Jurnal Pertanian"
    assert "Biochar meningkatkan kesuburan tanah" in rec["text"]
    assert rec["kind"] == "doi"
