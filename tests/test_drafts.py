"""Tes penyimpanan draf (Task 16)."""

import os
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


@pytest.mark.skipif(os.name != "nt", reason="DPAPI hanya tersedia di Windows")
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


# --- Rekonsiliasi draf aktif: kebijakan merge/preserve/clear/archive --------


def _section_dict(text: str, uid: str = "uid-1", origin: str | None = None):
    sentence = {"uid": uid, "text": text, "quote": text, "source_ids": [0],
                "is_factual": True, "citation": True}
    if origin:
        sentence["origin"] = origin
    return {
        "level": 2,
        "title": "1.1 Latar Belakang",
        "paragraphs": [{"sentences": [sentence]}],
    }


def _source_record(title: str = "Jurnal Uji"):
    return {"kind": "pdf", "title": title, "year": "2025", "container": "",
            "doi": "", "url": "", "authors": [], "text": "Teks sumber " + title}


def test_reconcile_payload_review_pertahankan_fields_dan_sources(tmp_path, monkeypatch):
    """Payload Tab Review (sections+done tanpa fields) tidak boleh menghapus
    fields/sumber milik Tab Laporan."""
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.reconcile_draft("aktif", {
        "fields": {"JUDUL": "Laporan Uji", "DOSEN": "Dr. Uji"},
        "sources": [_source_record()],
        "sections": [_section_dict("Kalimat pertama.")],
        "done": [],
    })

    merged = drafts.reconcile_draft("aktif", {
        "sections": [_section_dict("Kalimat disunting.", "uid-1", origin="edit")],
        "sources": [],
        "done": ["uid-1"],
    })
    assert merged.fields["JUDUL"] == "Laporan Uji"
    assert merged.fields["DOSEN"] == "Dr. Uji"
    assert len(merged.sources) == 1
    assert merged.done == ["uid-1"]
    assert "disunting" in merged.sections[0]["paragraphs"][0]["sentences"][0]["text"]


def test_reconcile_payload_report_pertahankan_sections_dan_done(tmp_path, monkeypatch):
    """Payload Tab Laporan (fields+sources tanpa sections/done) tidak boleh
    menghapus isi dokumen dan tanda review milik Tab Review."""
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.reconcile_draft("aktif", {
        "sections": [_section_dict("Bab utuh dari review.")],
        "done": ["uid-9"],
    })

    merged = drafts.reconcile_draft("aktif", {
        "fields": {"JUDUL": "Judul Baru"},
        "sources": [_source_record("Jurnal Kedua")],
    })
    assert "Bab utuh dari review." in merged.sections[0]["paragraphs"][0]["sentences"][0]["text"]
    assert merged.done == ["uid-9"]
    assert merged.fields["JUDUL"] == "Judul Baru"
    assert len(merged.sources) == 1


def test_reconcile_draf_baru_belum_ada_berkas(tmp_path, monkeypatch):
    """Payload parsial pada draf yang belum pernah ada membuat draf dengan
    nilai bawaan kosong, bukan crash (regresi AttributeError produksi)."""
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    merged = drafts.reconcile_draft("aktif", {
        "fields": {"JUDUL": "Draf Baru"},
        "sources": [_source_record()],
    })
    assert merged.fields["JUDUL"] == "Draf Baru"
    assert merged.sections == []
    assert merged.done == []
    assert len(merged.sources) == 1

    assert drafts.reconcile_draft("aktif", {}).sections == []


def test_reconcile_sumber_kosong_eksplisit_dengan_fields_menghapus(tmp_path, monkeypatch):
    """Payload Studio yang membawa fields + sources:[] berhak menghapus sumber;
    payload tanpa fields (pola Tab Review) tetap mempertahankan."""
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.reconcile_draft("aktif", {
        "fields": {"JUDUL": "Ada Sumber"},
        "sources": [_source_record()],
    })

    # Tanpa fields: sumber kosong dipertahankan
    merged = drafts.reconcile_draft("aktif", {"sources": []})
    assert len(merged.sources) == 1

    # Dengan fields: sumber kosong berarti hapus eksplisit
    merged = drafts.reconcile_draft("aktif", {"fields": {"JUDUL": "Tanpa Sumber"}, "sources": []})
    assert merged.sources == []


def test_reconcile_clear_sections_mengosongkan_bagian_dan_done(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.reconcile_draft("aktif", {
        "sections": [_section_dict("Isi awal.")],
        "done": ["uid-1"],
    })

    merged = drafts.reconcile_draft("aktif", {"sections": [], "done": [], "clear_sections": True})
    assert merged.sections == []
    assert merged.done == []

    # Tanpa clear_sections: sections kosong justru dipertahankan yang tersimpan
    drafts.reconcile_draft("aktif", {"sections": [_section_dict("Isi kedua.")]})
    merged = drafts.reconcile_draft("aktif", {"sections": []})
    assert "Isi kedua." in merged.sections[0]["paragraphs"][0]["sentences"][0]["text"]


def test_reconcile_fields_gabung_per_kunci(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    drafts.reconcile_draft("aktif", {"fields": {"JUDUL": "Judul", "DOSEN": "Dosen A"}})
    merged = drafts.reconcile_draft("aktif", {"fields": {"DOSEN": "Dosen B"}})
    assert merged.fields["JUDUL"] == "Judul"
    assert merged.fields["DOSEN"] == "Dosen B"


def test_has_content_dan_has_review_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    kosong = drafts.DraftState("aktif", {}, [], [])
    assert drafts.has_content(kosong) is False
    assert drafts.has_review_progress(kosong) is False

    judul_saja = drafts.DraftState("aktif", {"JUDUL": "Judul"}, [], [])
    assert drafts.has_content(judul_saja) is True
    assert drafts.has_review_progress(judul_saja) is False

    ditandai = drafts.DraftState("aktif", {}, [], [_section_dict("Isi.")], done=["uid-1"])
    assert drafts.has_review_progress(ditandai) is True

    disunting = drafts.DraftState("aktif", {}, [], [_section_dict("Isi.", origin="edit")])
    assert drafts.has_review_progress(disunting) is True

    baru_generate = drafts.DraftState("aktif", {}, [], [_section_dict("Isi.")])
    assert drafts.has_review_progress(baru_generate) is False


def test_archive_draft_membuat_salinan_bertanda_waktu(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts.paths, "DRAFTS_DIR", tmp_path)
    asal = drafts.DraftState(
        "aktif",
        {"JUDUL": "Pengaruh Biochar terhadap Tanah"},
        [_source_record()],
        [_section_dict("Isi terarsip.")],
        done=["uid-1"],
    )
    drafts.save_draft(asal)
    path = drafts.archive_draft(asal, prefix="arsip_pregen")

    assert path is not None and path.is_file()
    assert path.name.startswith("arsip_pregen_")
    assert "Pengaruh_Biochar" in path.name
    salinan = drafts.load_draft(path.stem)
    assert salinan.fields["JUDUL"] == "Pengaruh Biochar terhadap Tanah"
    assert salinan.done == ["uid-1"]
    assert salinan.draft_id == path.stem
    # Draf asli tetap utuh di tempatnya
    assert drafts.load_draft("aktif") is not None
