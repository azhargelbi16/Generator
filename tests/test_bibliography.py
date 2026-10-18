import pytest
from generator.ai.bibliography import extract_source, merge_metadata, excerpt, BibliographyError
from generator.ai.citation import Author, Source


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages, json_mode=False):
        self.calls += 1
        return self.replies.pop(0)


def test_excerpt_bounds_long_text():
    ex = excerpt("A" * 20000, max_chars=6000, tail_chars=500)
    assert ex.startswith("A" * 100) and ex.endswith("A" * 500)
    assert len(ex) <= 6000 + 500 + 10
    assert excerpt("pendek") == "pendek"


def test_extract_parses_authors_as_objects():
    reply = ('{"authors":[{"family":"Santoso","given":"Budi","is_org":false}],'
             '"year":"2020","title":"T","container":"J","doi":"10.1/x","url":""}')
    s = extract_source("teks", FakeClient([reply]))
    assert s.authors == [Author("Santoso", "Budi", False)]
    assert s.doi == "10.1/x"


def test_extract_retries_once_then_raises():
    c = FakeClient(["bukan json", "masih bukan json"])
    with pytest.raises(BibliographyError):
        extract_source("teks", c)
    assert c.calls == 2


def test_merge_prefers_document_metadata_but_keeps_author_model():
    ai = Source([Author("Salah", "X")], "1999", "Judul AI", "J", "", "")
    s = merge_metadata(ai, {"title": "Judul Asli", "year": "2021", "doi": "10.5/y"})
    assert s.title == "Judul Asli" and s.year == "2021" and s.doi == "10.5/y"
    assert s.authors == [Author("Salah", "X")]
