from pathlib import Path
from generator.web.api_bridge import ApiBridge
from generator import database, config

def test_get_document_analytics(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db)

    sections_dicts = [
        {
            "level": 1,
            "title": "BAB 1. PENDAHULUAN",
            "paragraphs": [
                {
                    "sentences": [
                        {
                            "text": "Kecerdasan buatan berkembang dengan sangat pesat di era modern saat ini.",
                            "quote": "kecerdasan buatan",
                            "source_ids": [1],
                            "is_factual": True,
                            "citation": True,
                        },
                        {
                            "text": "Laporan ini membahas analisis implementasi deep learning.",
                            "quote": "",
                            "source_ids": [],
                            "is_factual": False,
                            "citation": False,
                        }
                    ]
                }
            ]
        }
    ]

    res = bridge.get_document_analytics(sections_dicts, [])
    assert res["total_sentences"] == 2
    assert res["total_words"] > 10
    assert res["reading_time_minutes"] >= 1
    assert res["citation_coverage_pct"] == 100  # 1 factual sentence, and it has a citation!
    assert 0 <= res["academic_score"] <= 100
    assert 0 <= res["readability_score"] <= 100
    assert len(res["section_distribution"]) == 1
    assert res["section_distribution"][0]["title"] == "BAB 1. PENDAHULUAN"

