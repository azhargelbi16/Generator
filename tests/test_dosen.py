"""Tes mode dosen — reviewer AI opt-in di akhir alur (addendum D.4)."""

import json

from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.ai.dosen import DosenNote, dosen_prompt, review_report

NOTES_JSON = json.dumps(
    {
        "notes": [
            {"section_title": "Metode", "sentence_uid": None,
             "severity": "pertanyaan", "comment": "Dari mana datanya?"},
            {"section_title": "Pendahuluan", "sentence_uid": "abc",
             "severity": "lemah", "comment": "Argumen lemah."},
            {"section_title": "Pendahuluan", "sentence_uid": None,
             "severity": "berani", "comment": "Klaim terlalu berani tanpa data."},
        ]
    }
)


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.messages = []

    def chat(self, messages, json_mode=False):
        self.messages.append(messages)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def _sections():
    return [
        Section(1, "Pendahuluan", [Paragraph([Sentence("Argumen utama.", "q", [0], uid="abc")])]),
        Section(1, "Metode", [Paragraph([Sentence("Data diambil tahun lalu.", "q", [0])])]),
    ]


def test_review_report_mengurutkan_severity_dan_memetakan_catatan():
    notes = review_report(_sections(), ["Santoso, B. (2020)."], FakeClient([NOTES_JSON]))
    assert [note.severity for note in notes] == ["lemah", "berani", "pertanyaan"]
    assert notes[0].section_title == "Pendahuluan"
    assert notes[0].sentence_uid == "abc"
    assert notes[0].comment == "Argumen lemah."
    assert notes[1].sentence_uid is None


def test_review_report_json_buruk_mengembalikan_kosong():
    assert review_report(_sections(), [], FakeClient(["bukan json"])) == []


def test_review_report_memangkas_max_notes():
    notes = review_report(_sections(), [], FakeClient([NOTES_JSON]), max_notes=2)
    assert [note.severity for note in notes] == ["lemah", "berani"]


def test_review_report_menyaring_severity_tidak_dikenal():
    raw = json.dumps({"notes": [{"section_title": "B", "severity": "aneh", "comment": "x"}]})
    assert review_report(_sections(), [], FakeClient([raw])) == []


def test_dosen_prompt_memuat_teks_bab_dan_referensi():
    messages = dosen_prompt("## Pendahuluan\nArgumen utama.", ["Santoso, B. (2020)."])
    joined = " ".join(m["content"] for m in messages)
    assert "Pendahuluan" in joined and "Santoso, B. (2020)." in joined
