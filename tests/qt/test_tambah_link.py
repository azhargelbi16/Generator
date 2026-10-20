"""Tes tambah sumber link Qt: tambah beruntun dan pesan kegagalan (bugfix pesan error)."""

import json

from PySide6.QtWidgets import QMessageBox

from generator.sources.errors import SourceReadError

from test_tab_laporan_setup import _ctl, _wait


class _FakeAI:
    def chat(self, messages, json_mode=False):
        return json.dumps(
            {
                "authors": [{"family": "Santoso", "given": "Budi"}],
                "year": "2023",
                "title": "Judul Uji",
                "container": "Jurnal Uji",
            }
        )


def _mock_berhasil(monkeypatch):
    monkeypatch.setattr(
        "generator.qt.report_controller.web_reader.fetch",
        lambda url: ("teks halaman web yang cukup panjang untuk diuji", {"title": "Judul Uji"}),
    )
    monkeypatch.setattr(
        "generator.qt.report_controller.ReportController._ai_client",
        lambda self: _FakeAI(),
    )


def test_tiga_link_beruntun_semua_berhasil(qapp, db_tmp, monkeypatch):
    _mock_berhasil(monkeypatch)
    ctl = _ctl(db_tmp)
    for url in ("http://a.example/1", "http://a.example/2", "http://b.example/3"):
        ctl._add_link_core(url)
        _wait(ctl)
    assert len(ctl.sources) == 3
    assert "ditambahkan" in ctl._status.text()
    assert ctl._last_message == ""


def test_link_gagal_menampilkan_pesan_asli(qapp, db_tmp, monkeypatch):
    pesan_tertampung = {}

    def _warning(parent, title, text):
        pesan_tertampung["title"] = title
        pesan_tertampung["text"] = text

    monkeypatch.setattr(QMessageBox, "warning", _warning)
    monkeypatch.setattr(
        "generator.qt.report_controller.web_reader.fetch",
        lambda url: (_ for _ in ()).throw(
            SourceReadError("Situs tidak bisa diakses (diblokir atau butuh JavaScript): " + url)
        ),
    )
    monkeypatch.setattr(
        "generator.qt.report_controller.ReportController._ai_client",
        lambda self: _FakeAI(),
    )
    ctl = _ctl(db_tmp)
    ctl._add_link_core("http://a.example/2")
    _wait(ctl)
    assert len(ctl.sources) == 0
    assert ctl._status.text() == "Penambahan sumber gagal."
    assert "Situs tidak bisa diakses" in ctl._last_message
    assert "Situs tidak bisa diakses" in pesan_tertampung["text"]
