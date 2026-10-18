from generator import config


def test_roundtrip_config(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.Config("http://localhost:1234/v1", "k", "m", 0.2)
    config.save_config(cfg, p)
    assert config.load_config(p) == cfg


def test_load_missing_returns_default(tmp_path):
    assert config.load_config(tmp_path / "nope.json").ai_temperature == 0.2
