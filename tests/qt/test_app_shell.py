"""Tes cangkang jendela utama Qt: 5 tab bernama persis seperti Tk (addendum A.7)."""


def test_shell_punya_lima_tab_dengan_nama_tk(qapp, db_tmp, cfg_default):
    from generator.qt.app import build_main_window

    window = build_main_window(db_tmp, cfg_default)
    names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert names == ["Data", "Template", "Laporan", "Review Hasil", "Pengaturan"]
    assert window.windowTitle() == "Generator Laporan"


def test_shell_memperingatkan_api_key_kosong(qapp, db_tmp, cfg_default):
    from generator.qt.app import build_main_window

    window = build_main_window(db_tmp, cfg_default)
    assert "API key" in window.statusBar().currentMessage()


def test_shell_tanpa_peringatan_bila_api_key_ada(qapp, db_tmp):
    from generator.config import Config
    from generator.qt.app import build_main_window

    cfg = Config("http://x/v1", "k", "m", 0.2)
    window = build_main_window(db_tmp, cfg)
    assert "API key" not in window.statusBar().currentMessage()
