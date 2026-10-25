"""Tes modul reviewed: satu sumber kebenaran tab Review (slice arsitektur 2)."""

import pytest

from generator import reviewed
from generator.sources.records import source_to_record
from generator.ai.citation import Author, Source


def _source_record(title="Jurnal Uji", text="Teks sumber jurnal uji."):
    return source_to_record(
        Source(authors=[Author(family="Santoso", given="A.")], year="2024", title=title),
        text,
        "pdf",
    )


def _sections_dicts():
    return [
        {"level": 1, "title": "BAB 1. PENDAHULUAN", "paragraphs": []},
        {"level": 2, "title": "1.1 Latar Belakang", "paragraphs": [{"sentences": [
            {
                "uid": "u1",
                "text": "Biochar menaikkan pH tanah asam 0,5 sampai 1,2 satuan.",
                "quote": "biochar mampu menaikkan pH tanah asam sebesar 0,5 sampai 1,2",
                "is_factual": True,
                "citation": True,
                "source_ids": [0],
            },
            {
                "uid": "u2",
                "text": "Kalimat pengantar tanpa klaim.",
                "quote": "",
                "is_factual": False,
                "citation": False,
                "source_ids": [],
            },
        ]}]},
    ]


def test_from_payload_menormalisasi_dan_menghitung_status():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    assert len(doc.sections) == 2
    assert doc.sections[0].paragraphs == []
    assert len(doc.source_texts) == 1

    payload = doc.status_payload()
    assert [s["uid"] for s in payload] == ["u1", "u2"]
    assert payload[0]["status"] in ("terverifikasi", "perlu_ditinjau", "tidak_terverifikasi")
    assert payload[1]["status"] == "bukan_klaim_faktual"
    assert payload[1]["is_factual"] is False


def test_cited_ids_semantik_citation_aktif():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    assert doc.cited_ids == {0}


def test_citation_payload_bentuk_sama_dengan_operasi_lama():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    payload = doc.citation_payload("et_al")
    assert set(payload) == {"labels", "label_forms", "references", "cited_ids"}
    assert "0" in payload["labels"]
    assert len(payload["references"]) == 1


def test_analytics_bentuk_sama_dengan_operasi_lama():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    a = doc.analytics()
    for key in (
        "total_words", "total_chars", "total_sentences", "total_paragraphs",
        "reading_time_minutes", "citation_coverage_pct", "academic_score",
        "readability_score", "section_distribution",
    ):
        assert key in a
    assert a["total_sentences"] == 2
    assert a["section_distribution"][0]["title"] == "BAB 1. PENDAHULUAN"


def test_snapshot_menggabungkan_ketiganya():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    snap = doc.snapshot("et_al")
    assert set(snap) == {"statuses", "citations", "analytics"}
    assert snap["statuses"] == doc.status_payload()
    assert snap["citations"] == doc.citation_payload("et_al")
    assert snap["analytics"] == doc.analytics()


def test_status_lazim_tidak_dihitung_bila_tak_diminta():
    doc = reviewed.ReviewedDocument.from_payload(_sections_dicts(), [_source_record()])
    assert doc._statuses is None  # verifikasi mahal belum berjalan
    doc.citation_payload("et_al")  # jalur sitasi tidak butuh status
    assert doc._statuses is None
    doc.status_payload()
    assert doc._statuses is not None
