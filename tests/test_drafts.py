"""Tes penyimpanan draf (Task 16)."""

from generator import drafts


def test_draft_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    state = drafts.DraftState("d1", {"judul": "X"}, [{"title": "T"}], [])
    drafts.save_draft(state)
    assert drafts.load_draft("d1").fields["judul"] == "X"
    assert "d1" in drafts.list_drafts()
    drafts.delete_draft("d1")
    assert drafts.list_drafts() == []


def test_draft_roundtrips_done_marks(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.save_draft(drafts.DraftState("d2", {}, [], [], done=["a1", "b2"]))
    assert drafts.load_draft("d2").done == ["a1", "b2"]


def test_load_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    assert drafts.load_draft("nope") is None
