from generator.ai.content import repair_truncated_json, _first_json_object

def test_repair_truncated_json_simple():
    raw = '{"sections": [{"level": 1, "title": "BAB 1", "paragraphs": [{"sentences": [{"text": "Kalimat 1", "quote": "q", "source_ids": [1], "is_factual": true}]}]}, {"level": 1, "title": "BAB 2", "paragraphs": [{"sentences": [{"text": "Terpotong'
    repaired = repair_truncated_json(raw)
    assert repaired is not None
    assert "sections" in repaired
    assert len(repaired["sections"]) >= 1
    assert repaired["sections"][0]["title"] == "BAB 1"
    assert repaired["sections"][0]["paragraphs"][0]["sentences"][0]["text"] == "Kalimat 1"

def test_repair_truncated_json_with_outer_text():
    raw = 'Berikut adalah hasil laporan:\n```json\n{"sections": [{"level": 1, "title": "BAB 1", "paragraphs": [{"sentences": [{"text": "Halo", "quote": "h", "source_ids": [0], "is_factual": true}]}]}'
    parsed = _first_json_object(raw)
    assert parsed is not None
    assert parsed["sections"][0]["title"] == "BAB 1"

def test_repair_truncated_json_invalid():
    assert repair_truncated_json("bukan json sama sekali") is None
    assert repair_truncated_json("") is None
    assert repair_truncated_json(None) is None

