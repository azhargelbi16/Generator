"""Integration test verifying full compliance between ApiBridge and formal API Contract."""

from pathlib import Path
import inspect
from generator.web.api_bridge import ApiBridge
from generator.web.contract import API_VERSION, API_ENDPOINTS, get_contract_metadata
from generator import database


def test_api_contract_metadata_integrity():
    meta = get_contract_metadata()
    assert meta["version"] == API_VERSION
    assert meta["total_endpoints"] == len(API_ENDPOINTS)
    assert len(API_ENDPOINTS) >= 45


def test_every_contract_endpoint_implemented_on_bridge(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")
    
    # Verify every endpoint in contract is a real callable method on ApiBridge
    for endpoint_name in API_ENDPOINTS:
        assert hasattr(bridge, endpoint_name), f"ApiBridge missing method '{endpoint_name}' defined in contract!"
        method = getattr(bridge, endpoint_name)
        assert callable(method), f"'{endpoint_name}' on ApiBridge is not callable!"

    db.close()


def test_bridge_versioning_endpoints(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")
    
    assert bridge.get_api_version() == API_VERSION
    contract = bridge.get_api_contract()
    assert contract["version"] == API_VERSION
    assert "endpoints" in contract
    
    db.close()


def test_bridge_error_handling_contract_compliance(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")
    
    # 1. Invalid DOI should return failure envelope, not raise uncaught exception
    res_doi = bridge.resolve_doi_source("invalid/not-a-real-doi-12345")
    assert isinstance(res_doi, dict)
    assert res_doi["success"] is False
    assert "error" in res_doi
    
    # 2. Invalid Web URL should return failure envelope
    res_web = bridge.add_web_source("https://invalid-non-existent-domain-9999.org/paper")
    assert isinstance(res_web, dict)
    assert res_web["success"] is False
    assert "error" in res_web
    
    # 3. Invalid Named Draft state should return failure envelope
    res_draft = bridge.save_named_draft("test_draft", "invalid-non-dict-payload")
    assert isinstance(res_draft, dict)
    assert res_draft["success"] is False
    assert "error" in res_draft

    db.close()

