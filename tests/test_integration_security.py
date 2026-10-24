"""Integration tests for cross-platform security, encryption at rest, and permissions."""

import json
from pathlib import Path
import pytest

from generator import config, drafts, security


def test_security_encryption_roundtrip():
    secret_text = "sk-super-secret-production-key-12345"
    encrypted_envelope = security.encrypt_string(secret_text)
    
    assert "payload" in encrypted_envelope
    assert secret_text not in encrypted_envelope
    
    decrypted = security.decrypt_string(encrypted_envelope)
    assert decrypted == secret_text


def test_security_corrupted_payload_graceful_handling():
    corrupted_envelope = json.dumps({
        "version": 2,
        "encrypted": True,
        "method": "dpapi",
        "payload": "not-valid-base64-!@#$%"
    })
    decrypted = security.decrypt_string(corrupted_envelope)
    assert decrypted is None


def test_security_tampered_payload_rejected():
    tampered_envelope = json.dumps({
        "version": 2,
        "encrypted": True,
        "method": "posix_machine",
        "payload": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh"
    })
    decrypted = security.decrypt_string(tampered_envelope)
    assert decrypted is None


def test_config_encrypted_at_rest_and_transparent_read(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    cfg = config.Config(
        ai_base_url="https://api.openai.com/v1",
        ai_api_key="sk-test-secret-at-rest-9999",
        ai_model="gpt-4o",
        ai_temperature=0.7,
    )
    
    config.save_config(cfg, cfg_file)
    
    # 1. Inspect raw disk content - must be encrypted!
    raw_disk_content = cfg_file.read_text(encoding="utf-8")
    assert "sk-test-secret-at-rest-9999" not in raw_disk_content
    assert '"encrypted": true' in raw_disk_content or '"encrypted":true' in raw_disk_content.lower()
    
    # 2. Transparently load through load_config
    loaded = config.load_config(cfg_file)
    assert loaded.ai_api_key == "sk-test-secret-at-rest-9999"
    assert loaded.ai_model == "gpt-4o"
    assert loaded.ai_temperature == 0.7


def test_config_migration_from_plaintext(tmp_path: Path):
    cfg_file = tmp_path / "legacy_config.json"
    legacy_json = {
        "ai_base_url": "http://legacy:1234/v1",
        "ai_api_key": "legacy-plain-key",
        "ai_model": "legacy-model",
        "ai_temperature": 0.5,
    }
    cfg_file.write_text(json.dumps(legacy_json), encoding="utf-8")
    
    # Reading legacy plaintext works cleanly
    loaded = config.load_config(cfg_file)
    assert loaded.ai_api_key == "legacy-plain-key"
    assert loaded.ai_model == "legacy-model"
    
    # Saving upgrades file to encrypted format
    config.save_config(loaded, cfg_file)
    new_raw = cfg_file.read_text(encoding="utf-8")
    assert "legacy-plain-key" not in new_raw
    assert "payload" in new_raw

