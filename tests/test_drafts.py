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



# --- Task 3.2: Enkripsi draf di disk -----------------------------------------


def test_draft_baru_dienkripsi_tidak_memuat_teks_sumber_langsung(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    state = drafts.DraftState(
        "d_secret",
        {"judul": "Laporan Rahasia Organik"},
        [{"title": "Jurnal Pertanian", "text": "RAHASIA_TEKS_SUMBER_12345"}],
        [{"title": "Bab 1", "paragraphs": []}],
    )
    path = drafts.save_draft(state)

    # Isi mentah berkas di disk tidak boleh memuat teks sumber polos
    raw_disk_text = path.read_text(encoding="utf-8")
    assert "RAHASIA_TEKS_SUMBER_12345" not in raw_disk_text
    assert "Laporan Rahasia Organik" not in raw_disk_text

    # Memuat kembali draf mengembalikan teks yang persis utuh
    loaded = drafts.load_draft("d_secret")
    assert loaded is not None
    assert loaded.fields["judul"] == "Laporan Rahasia Organik"
    assert loaded.sources[0]["text"] == "RAHASIA_TEKS_SUMBER_12345"


def test_draf_lama_polos_masih_bisa_dibuka(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)

    old_state = {
        "draft_id": "d_old",
        "fields": {"judul": "Draf Versi Lama Polos"},
        "sources": [{"title": "Sumber Lama", "text": "Teks polos lama"}],
        "sections": [],
        "done": ["uid-1", "uid-2"],
    }
    old_file = tmp_path / "d_old.json"
    old_file.write_text(json.dumps(old_state, indent=2), encoding="utf-8")

    loaded = drafts.load_draft("d_old")
    assert loaded is not None
    assert loaded.fields["judul"] == "Draf Versi Lama Polos"
    assert loaded.sources[0]["text"] == "Teks polos lama"
    assert loaded.done == ["uid-1", "uid-2"]


def test_fallback_polos_bila_dpapi_tidak_tersedia(tmp_path, monkeypatch, caplog):
    import logging
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    # Simulasikan DPAPI tidak tersedia (misal Linux atau kegagalan DPAPI)
    monkeypatch.setattr(drafts, "_dpapi_protect", lambda data: None)

    with caplog.at_level(logging.WARNING):
        state = drafts.DraftState(
            "d_fallback",
            {"judul": "Draf Fallback"},
            [{"title": "Sumber", "text": "Teks sumber fallback"}],
            [],
        )
        path = drafts.save_draft(state)

    # Catat warning di log tanpa membocorkan isi data
    assert any("DPAPI tidak tersedia" in record.message for record in caplog.records)
    assert not any("Teks sumber fallback" in record.message for record in caplog.records)

    # Draf tetap tersimpan dan dapat dimuat
    loaded = drafts.load_draft("d_fallback")
    assert loaded is not None
    assert loaded.fields["judul"] == "Draf Fallback"
