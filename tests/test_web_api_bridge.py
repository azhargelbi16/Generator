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


def test_api_bridge_bibliography_error_fallback(tmp_path: Path, monkeypatch):
    from generator.ai import bibliography

    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    def mock_extract_raises(text, cl):
        raise bibliography.BibliographyError("Model hallucinated invalid JSON twice")

    monkeypatch.setattr(bibliography, "extract_source", mock_extract_raises)

    res = bridge.add_manual_source("Teks referensi penelitian tentang pertanian")
    assert res.get("success") is True
    assert res["record"]["title"] == "Teks Manual"
    db.close()


def test_api_bridge_export_report_none_template_id(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # Bila template_id kosong, kembalikan pesan "Pilih template terlebih dahulu" (T4.1)
    res = bridge.export_report({"template_id": None, "sources": [], "sections": []})
    assert "error" in res
    assert res["error"] == "Pilih template terlebih dahulu" 
    db.close()



def test_api_bridge_multi_project_and_doi(tmp_path: Path, monkeypatch):
    from generator.sources import doi_resolver
    from generator import paths
    paths.set_data_dir(tmp_path)

    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # 1. Test DOI resolution via bridge
    def mock_fetch(doi):
        return {"title": "Paper Biochar", "authors": [], "year": "2024", "kind": "doi"}

    monkeypatch.setattr(doi_resolver, "fetch_doi_metadata", mock_fetch)
    doi_res = bridge.resolve_doi_source("10.1016/j.demo.2024")
    assert doi_res.get("success") is True
    assert doi_res["record"]["title"] == "Paper Biochar"

    # 2. Test multi-project save, list, load, delete
    save_res = bridge.save_named_draft("Tugas Akhir AI", {
        "fields": {"JUDUL": "Tugas Akhir AI"},
        "sources": [{"title": "S1"}],
        "sections": [],
        "done": ["uid-1"]
    })
    assert save_res.get("success") is True
    draft_id = save_res["draft_id"]

    drafts_list = bridge.list_saved_drafts()
    assert any(d["draft_id"] == draft_id for d in drafts_list)

    load_res = bridge.load_named_draft(draft_id)
    assert load_res.get("success") is True
    assert load_res["draft"]["fields"]["JUDUL"] == "Tugas Akhir AI"

    del_res = bridge.delete_named_draft(draft_id)
    assert del_res.get("success") is True

    db.close()

def test_api_bridge_template_management(tmp_path: Path):
    from generator import paths
    paths.set_data_dir(tmp_path)

    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # 1. Create standard academic template with custom options
    res = bridge.create_default_template({"font_name": "Times New Roman", "margin_preset": "4433"})
    assert res.get("success") is True
    tpl_path = Path(res["path"])
    assert tpl_path.is_file()

    # 2. List templates returns spec
    tpls = bridge.list_templates()
    assert len(tpls) >= 1
    std_tpl = next(t for t in tpls if t["is_default"])
    assert std_tpl["status"] == "lengkap"
    assert std_tpl["spec"]["margin"] == "4-4-3-3 cm"
    assert std_tpl["spec"]["font"] == "Times New Roman 12pt"

    # 3. Open template folder
    f_res = bridge.open_templates_folder()
    assert f_res.get("success") is True

    db.close()


def test_api_bridge_mark_non_factual_done_excludes_factual(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")
    sections_dicts = [
        {
            "level": 1,
            "title": "Bab",
            "paragraphs": [
                {
                    "sentences": [
                        {"text": "Opini.", "quote": "", "source_ids": [], "is_factual": False, "uid": "u-nonfact"},
                        {"text": "Klaim.", "quote": "q", "source_ids": [0], "is_factual": True, "uid": "u-fact"},
                    ]
                }
            ],
        }
    ]
    res = bridge.mark_non_factual_done(sections_dicts, ["u-existing"])
    assert res.get("success") is True
    assert "u-nonfact" in res["done"]
    assert "u-fact" not in res["done"]
    assert "u-existing" in res["done"]
    db.close()



# --- Task 3.1: Jangan kirim API key ke frontend ------------------------------


def test_api_bridge_api_key_privacy(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    cfg_file = tmp_path / "config.json"
    cfg = config.Config(ai_api_key="secret-key-12345", ai_model="test-model")
    config.save_config(cfg, cfg_file)

    bridge = ApiBridge(db, config_path=cfg_file)

    # 1. Respons get_config tidak boleh memuat ai_api_key asli dan harus ada ai_api_key_set=True
    loaded = bridge.get_config()
    assert loaded["ai_api_key"] == ""
    assert loaded["ai_api_key_set"] is True
    assert "secret-key-12345" not in loaded.values()

    # 2. Simpan konfigurasi dengan ai_api_key kosong ("") tidak boleh menghapus key lama di disk
    save_res = bridge.save_config({"ai_model": "updated-model", "ai_api_key": ""})
    assert save_res["success"] is True
    assert save_res["config"]["ai_api_key"] == ""
    assert save_res["config"]["ai_api_key_set"] is True

    # Cek berkas fisik di disk: key asli tetap terjaga
    disk_cfg = config.load_config(cfg_file)
    assert disk_cfg.ai_api_key == "secret-key-12345"
    assert disk_cfg.ai_model == "updated-model"

    # 3. Simpan dengan key baru yang tidak kosong harus memperbarui key di disk
    save_res2 = bridge.save_config({"ai_api_key": "brand-new-key"})
    assert save_res2["config"]["ai_api_key"] == ""
    assert save_res2["config"]["ai_api_key_set"] is True

    disk_cfg2 = config.load_config(cfg_file)
    assert disk_cfg2.ai_api_key == "brand-new-key"

    db.close()



# --- Task 4.1: Jangan diam-diam memakai template pertama ---------------------


def test_export_report_tanpa_template_id_gagal(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = database.Database(db_file)
    db.init_schema()

    dummy_docx = tmp_path / "tpl.docx"
    dummy_docx.write_text("dummy", encoding="utf-8")
    db.add_template(database.Template(0, "Template Bawaan", "Deskripsi", str(dummy_docx)))

    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # 1. Panggil export_report dengan template_id=None
    res1 = bridge.export_report({"template_id": None})
    assert res1.get("error") == "Pilih template terlebih dahulu"

    # 2. Panggil export_report dengan state kosong
    res2 = bridge.export_report({})
    assert res2.get("error") == "Pilih template terlebih dahulu"

    db.close()
