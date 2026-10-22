from pathlib import Path
from generator.web.api_bridge import ApiBridge
from generator import database, paths, config


def test_api_bridge_config_and_profiles(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    cfg_file = tmp_path / "config.json"
    cfg = config.Config(ai_model="test-model", ai_temperature=0.3)
    config.save_config(cfg, cfg_file)

    bridge = ApiBridge(db, config_path=cfg_file)

    # Config tests
    loaded = bridge.get_config()
    assert loaded["ai_model"] == "test-model"
    assert loaded["ai_temperature"] == 0.3

    save_res = bridge.save_config({"ai_model": "new-model", "ai_temperature": 0.5})
    assert save_res["success"] is True
    assert bridge.get_config()["ai_model"] == "new-model"

    # Profile tests
    p = bridge.get_profile()
    assert p["nama"] == ""
    bridge.save_profile({"nama": "Budi", "nim": "123", "prodi": "TI"})
    p2 = bridge.get_profile()
    assert p2["nama"] == "Budi"
    assert p2["nim"] == "123"

    # Dosen tests
    add_d = bridge.add_dosen({"nama": "Dr. Dosen", "gelar": "M.Kom", "identitas": "12345"})
    assert add_d["success"] is True
    d_list = bridge.list_dosen()
    assert len(d_list) == 1
    assert d_list[0]["nama"] == "Dr. Dosen"

    # Matkul tests
    add_m = bridge.add_matkul({"nama": "Sistem Pakar", "kode": "SP101"})
    assert add_m["success"] is True
    m_list = bridge.list_matkul()
    assert len(m_list) == 1
    assert m_list[0]["kode"] == "SP101"

    # Format variants
    vars_list = bridge.get_format_variants()
    assert len(vars_list) >= 4
    codes = [v["code"].upper() for v in vars_list]
    assert "A" in codes
    assert "B" in codes
    assert "C" in codes
    assert "BEBAS" in codes

    db.close()


def test_api_bridge_connection_and_fetch_overrides(tmp_path: Path, monkeypatch):
    from generator.ai import client

    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    cfg_file = tmp_path / "config.json"
    cfg = config.Config(ai_base_url="http://default:1234/v1", ai_model="default-model")
    config.save_config(cfg, cfg_file)

    bridge = ApiBridge(db, config_path=cfg_file)

    captured_urls = []

    def fake_check(cl):
        captured_urls.append((cl.cfg.ai_base_url, cl.cfg.ai_model, cl.cfg.ai_api_key))
        return True, "Mock connected"

    def fake_list(c):
        return [f"model-from-{c.ai_base_url}"]

    monkeypatch.setattr(client, "check_connection", fake_check)
    monkeypatch.setattr(client, "list_models", fake_list)

    # 1. Default fallback to disk cfg
    res = bridge.test_ai_connection()
    assert res["ok"] is True
    assert captured_urls[-1] == ("http://default:1234/v1", "default-model", "")

    # 2. Overrides from UI input fields
    res2 = bridge.test_ai_connection("http://localhost:20128/v1", "sk-custom", "custom-model")
    assert res2["ok"] is True
    assert captured_urls[-1] == ("http://localhost:20128/v1", "custom-model", "sk-custom")

    # 3. Fetch models with override
    f_res = bridge.fetch_models("http://localhost:20128/v1", "sk-custom")
    assert f_res["ok"] is True
    assert f_res["models"] == ["model-from-http://localhost:20128/v1"]

    db.close()

