"""Tes Panel Mode Dosen di Review (Task 5.2)."""

import json
from dataclasses import replace

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QPushButton

from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.sources.records import source_to_record
from generator.verification import verify_sections

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"

NOTES_JSON = json.dumps(
    {
        "notes": [
            {
                "section_title": "Bab Satu",
                "sentence_uid": None,
                "severity": "pertanyaan",
                "comment": "Mengapa memilih metode ini?",
            },
            {
                "section_title": "Bab Satu",
                "sentence_uid": None,
                "severity": "lemah",
                "comment": "Argumen pembuka lemah.",
            },
            {
                "section_title": "Bab Dua",
                "sentence_uid": None,
                "severity": "berani",
                "comment": "Klaim tanpa data pendukung.",
            },
        ]
    },
    ensure_ascii=False,
)


class _State:
    def __init__(self):
        self.sources = [
            source_to_record(
                Source([Author("Santoso", "Budi")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        self.done = set()
        self.fields = {"judul": "Laporan Dosen"}
        s1 = Sentence(text="Kalimat bab satu untuk dosen.", quote=QUOTED, source_ids=[0])
        s2 = Sentence(text="Kalimat bab dua untuk dosen.", quote=QUOTED, source_ids=[0])
        self.sentences = [s1, s2]
        self.sections = [
            Section(1, "Bab Satu", [Paragraph([s1])]),
            Section(1, "Bab Dua", [Paragraph([s2])]),
        ]
        self.statuses = verify_sections(self.sections, {0: SOURCE_TEXT})

    def _save_draft(self):
        pass


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def chat(self, messages, json_mode=False):
        return self._payload


def _page(qapp, cfg_default, payload=None):
    from generator.qt.review_page import ReviewPage

    state = _State()
    page = ReviewPage(state, cfg=cfg_default)
    page.render_document()
    page.show()  # isVisible() butuh ancestor terlihat, walau offscreen
    page._client_factory = lambda: FakeClient(payload if payload is not None else NOTES_JSON)
    return page, state


def _wait_worker(page, timeout_ms=5000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    page._worker.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    page._thread.wait(2000)


def test_fake_client_jumlah_catatan_dan_pengelompokan(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    page._request_dosen_review()
    _wait_worker(page)
    panel = page._dosen_panel
    assert panel.isVisible()
    teks = [panel._list.item(i).text() for i in range(panel._list.count())]
    assert "Bab Satu" in teks and "Bab Dua" in teks  # pengelompokan per bab
    assert sum(1 for t in teks if t.startswith("[")) == 3  # tiga catatan
    assert any(t.startswith("[lemah]") for t in teks)
    assert any(t.startswith("[berani]") for t in teks)
    assert any(t.startswith("[pertanyaan]") for t in teks)
    assert "Review dosen: 3 catatan." in page._info.text()


def test_klik_catatan_dengan_uid_menyeleksi_kalimat(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    uid_target = state.sentences[1].uid
    payload = json.dumps(
        {
            "notes": [
                {
                    "section_title": "Bab Dua",
                    "sentence_uid": uid_target,
                    "severity": "lemah",
                    "comment": "Perjelas kalimat ini.",
                }
            ]
        }
    )
    page._client_factory = lambda: FakeClient(payload)
    page._request_dosen_review()
    _wait_worker(page)
    item = next(
        panel_item
        for panel_item in (page._dosen_panel._list.item(i) for i in range(page._dosen_panel._list.count()))
        if panel_item.text().startswith("[lemah]")
    )
    page._dosen_panel._list.itemClicked.emit(item)
    assert page._selected_uid == uid_target
    assert page._document.textCursor().position() > 0


def test_panel_close_menghilangkan(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    page._request_dosen_review()
    _wait_worker(page)
    assert page._dosen_panel.isVisible()
    tombol = next(
        b for b in page._dosen_panel.findChildren(QPushButton) if b.text() == "✕"
    )
    tombol.click()
    assert not page._dosen_panel.isVisible()


def test_tanpa_dosen_review_tidak_auto_jalan(qapp, cfg_default, monkeypatch):
    from generator.ai import dosen as dosen_mod

    dipanggil = []
    monkeypatch.setattr(
        dosen_mod, "review_report", lambda *a, **k: dipanggil.append(1) or []
    )
    page, state = _page(qapp, cfg_default)  # dosen_review False
    page.on_generate_finished()
    assert dipanggil == []
    assert not page._dosen_panel.isVisible()


def test_dengan_dosen_review_auto_jalan(qapp, cfg_default):
    cfg = replace(cfg_default, dosen_review=True)
    page, state = _page(qapp, cfg)
    page.on_generate_finished()
    _wait_worker(page)
    assert page._dosen_panel.isVisible()
    assert page._dosen_panel._list.count() == 2 + 3  # 2 header bab + 3 catatan
