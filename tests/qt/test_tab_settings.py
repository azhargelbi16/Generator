"""Tes tab Pengaturan Qt: parity + panduan /v1 + ambil model (Task 2.5)."""

from PySide6.QtCore import QEventLoop, QTimer

from generator import paths
from generator.config import Config, load_config, save_config


def _wait(tab, timeout_ms=5000):
    """Tunggu worker tab selesai lalu rapikan thread-nya."""
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    tab._worker.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    tab._thread.wait(2000)


def _tab():
    from generator.qt.tab_settings import SettingsTab

    return SettingsTab()


def test_load_menampilkan_nilai_config(qapp, db_tmp):
    cfg = Config("http://x/v1", "kunci", "model-x", 0.7)
    save_config(cfg, paths.CONFIG_PATH)
    tab = _tab()
    assert tab._fields["base_url"].text() == "http://x/v1"
    assert tab._fields["api_key"].text() == "kunci"
    assert tab._fields["model"].currentText() == "model-x"
    assert tab._fields["temperature"].text() == "0.7"


def test_simpan_menulis_config_dan_tahan_kunci_baru(qapp, db_tmp):
    cfg = Config("http://x/v1", "k", "m", 0.2, citation_style="dkk", dosen_review=True)
    save_config(cfg, paths.CONFIG_PATH)
    tab = _tab()
    tab._fields["model"].setCurrentText("m2")
    tab._save()
    loaded = load_config(paths.CONFIG_PATH)
    assert loaded.ai_model == "m2"
    assert loaded.citation_style == "dkk"
    assert loaded.dosen_review is True
    assert tab._status.text() == "Pengaturan tersimpan."


def test_temperatur_salah_ditolak_dengan_petunjuk(qapp, db_tmp):
    tab = _tab()
    tab._fields["temperature"].setText("abc")
    assert "angka" in tab._hint_temperature.text()
    tab._save()
    assert "Temperatur" in tab._status.text()
    assert not paths.CONFIG_PATH.exists()


def test_tes_koneksi_berhasil_memperbarui_status(qapp, db_tmp):
    tab = _tab()
    tab._test_connection = lambda client: (True, "ok")
    tab._test()
    _wait(tab)
    assert "Koneksi berhasil" in tab._status.text()


def test_tes_koneksi_gagal_memperbarui_status(qapp, db_tmp):
    tab = _tab()
    tab._test_connection = lambda client: (False, "layanan mati")
    tab._test()
    _wait(tab)
    assert "Gagal" in tab._status.text()


def test_url_tanpa_v1_menampilkan_petunjuk_saat_gagal(qapp, db_tmp):
    tab = _tab()
    tab._fields["base_url"].setText("http://localhost:1234")
    tab._test_connection = lambda client: (False, "layanan mati")
    tab._test()
    _wait(tab)
    assert "/v1" in tab._url_hint.text()


def test_url_dengan_v1_tidak_menampilkan_petunjuk(qapp, db_tmp):
    tab = _tab()
    tab._fields["base_url"].setText("http://localhost:1234/v1")
    tab._test_connection = lambda client: (False, "layanan mati")
    tab._test()
    _wait(tab)
    assert tab._url_hint.text() == ""


def test_ambil_model_mengisi_combo(qapp, db_tmp, monkeypatch):
    monkeypatch.setattr("generator.ai.client.list_models", lambda cfg: ["m-b", "m-a"])
    tab = _tab()
    tab._fetch_models()
    _wait(tab)
    texts = [tab._fields["model"].itemText(i) for i in range(tab._fields["model"].count())]
    assert texts == ["m-b", "m-a"]
    assert "2 model" in tab._status.text()


def test_ambil_model_gagal_memperbarui_status(qapp, db_tmp, monkeypatch):
    from generator.ai.client import AIError

    def boom(cfg):
        raise AIError("server tidak mendukung")

    monkeypatch.setattr("generator.ai.client.list_models", boom)
    tab = _tab()
    tab._fetch_models()
    _wait(tab)
    assert "Gagal" in tab._status.text()
