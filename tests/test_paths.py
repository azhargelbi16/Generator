import pytest
from generator import paths


def test_ensure_dirs_creates_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path / "data" / "logos")
    monkeypatch.setattr(paths, "TEMPLATES_DIR", tmp_path / "data" / "templates")
    monkeypatch.setattr(paths, "DRAFTS_DIR", tmp_path / "data" / "drafts")
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")
    paths.ensure_dirs()
    assert paths.DRAFTS_DIR.is_dir() and paths.OUTPUT_DIR.is_dir()


def test_set_data_dir_repoints_paths(tmp_path, monkeypatch):
    for name in ["DATA_DIR", "DB_PATH", "LOGOS_DIR", "TEMPLATES_DIR",
                 "DRAFTS_DIR", "CONFIG_PATH", "LOG_PATH"]:
        monkeypatch.setattr(paths, name, getattr(paths, name))
    paths.set_data_dir(tmp_path)
    assert paths.DB_PATH == tmp_path / "app.db"
    assert paths.CONFIG_PATH == tmp_path / "config.json"


def test_ensure_dirs_wraps_oserror(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path / "data" / "logos")
    monkeypatch.setattr(paths, "TEMPLATES_DIR", tmp_path / "data" / "templates")
    monkeypatch.setattr(paths, "DRAFTS_DIR", tmp_path / "data" / "drafts")
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")

    def boom(self, *a, **k):
        raise OSError("read-only")

    monkeypatch.setattr(paths.Path, "mkdir", boom)
    with pytest.raises(paths.PathsError):
        paths.ensure_dirs()
