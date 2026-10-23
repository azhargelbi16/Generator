import json

import pytest

from generator import config


def test_roundtrip_config(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.Config("http://localhost:1234/v1", "k", "m", 0.2)
    config.save_config(cfg, p)
    assert config.load_config(p) == cfg


def test_load_missing_returns_default(tmp_path):
    assert config.load_config(tmp_path / "nope.json").ai_temperature == 0.2


def test_load_bad_temperature_falls_back(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "ai_base_url": "http://localhost:20128/v1",
        "ai_api_key": "k",
        "ai_model": "m",
        "ai_temperature": "abc",
    }), encoding="utf-8")
    cfg = config.load_config(p)
    assert cfg.ai_temperature == 0.2
    assert cfg.ai_model == "m"


def test_load_nested_temperature_falls_back(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "ai_base_url": "http://localhost:20128/v1",
        "ai_api_key": "k",
        "ai_model": "m",
        "ai_temperature": {"nested": 1},
    }), encoding="utf-8")
    assert config.load_config(p).ai_temperature == 0.2


# --- Task 1.5: preferensi gaya sitasi ---------------------------------------


def test_config_lama_tanpa_citation_style_default_et_al(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "ai_base_url": "http://localhost:20128/v1",
        "ai_api_key": "k",
        "ai_model": "m",
        "ai_temperature": 0.2,
    }), encoding="utf-8")
    assert config.load_config(p).citation_style == "et_al"


def test_roundtrip_citation_style_dkk(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.Config("http://localhost:1234/v1", "k", "m", 0.2, citation_style="dkk")
    config.save_config(cfg, p)
    assert config.load_config(p).citation_style == "dkk"


def test_config_lama_tanpa_dosen_review_default_false(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "ai_base_url": "http://localhost:20128/v1",
        "ai_api_key": "k",
        "ai_model": "m",
        "ai_temperature": 0.2,
    }), encoding="utf-8")
    assert config.load_config(p).dosen_review is False


def test_roundtrip_dosen_review_true(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.Config("http://localhost:1234/v1", "k", "m", 0.2, dosen_review=True)
    config.save_config(cfg, p)
    assert config.load_config(p).dosen_review is True


def test_save_gagal_tidak_merusak_config_lama(tmp_path, monkeypatch):
    from pathlib import Path

    p = tmp_path / "config.json"
    config.save_config(config.Config("http://x/v1", "kunci-lama", "m", 0.2), p)

    def rusak(self, *args, **kwargs):
        with open(self, "w", encoding="utf-8") as handle:
            handle.write("{rusak")
        raise OSError("disk penuh")

    monkeypatch.setattr(Path, "write_text", rusak)
    with pytest.raises(OSError):
        config.save_config(config.Config("http://x/v1", "kunci-baru", "m", 0.2), p)
    assert config.load_config(p).ai_api_key == "kunci-lama"
    assert list(tmp_path.iterdir()) == [p]





# --- Task 3.4: Batasi akses berkas sensitif ----------------------------------


def test_save_config_memanggil_fungsi_pembatas_izin(tmp_path, monkeypatch):
    from pathlib import Path
    dipanggil = []

    def mock_restrict(path):
        dipanggil.append(Path(path))
        return True

    monkeypatch.setattr(config, "restrict_file_permissions", mock_restrict)

    p = tmp_path / "config.json"
    cfg = config.Config(ai_model="test-secure")
    config.save_config(cfg, p)

    assert len(dipanggil) == 1
    assert dipanggil[0] == p


def test_restrict_file_permissions_berhasil_atau_graceful(tmp_path):
    p = tmp_path / "test_secret.json"
    p.write_text("{}", encoding="utf-8")

    res = config.restrict_file_permissions(p)
    assert isinstance(res, bool)
    assert res is True
