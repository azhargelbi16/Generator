"""Tes penyimpanan draf (Task 16)."""

import pytest

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


def test_save_gagal_tidak_merusak_draf_lama(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    lama = drafts.DraftState("d3", {"judul": "Lama"}, [], [])
    drafts.save_draft(lama)

    def rusak(self, *args, **kwargs):
        with open(self, "w", encoding="utf-8") as handle:
            handle.write("{rusak")
        raise OSError("disk penuh")

    monkeypatch.setattr(Path, "write_text", rusak)
    with pytest.raises(OSError):
        drafts.save_draft(drafts.DraftState("d3", {"judul": "Baru"}, [], []))
    assert drafts.load_draft("d3").fields["judul"] == "Lama"
    assert [p.name for p in tmp_path.iterdir()] == ["d3.json"]


def test_draft_id_tidak_boleh_keluar_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    for buruk in ("../evil", "..\\evil", "a/b", "", "CON:1"):
        with pytest.raises(ValueError):
            drafts.save_draft(drafts.DraftState(buruk, {}, [], []))
    assert list(tmp_path.iterdir()) == []
