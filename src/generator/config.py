"""Muat dan simpan konfigurasi AI (15)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class Config:
    ai_base_url: str = DEFAULT_BASE_URL
    ai_api_key: str = ""
    ai_model: str = DEFAULT_MODEL
    ai_temperature: float = 0.2


def default_config() -> Config:
    return Config()


def _coerce_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def load_config(path: Path) -> Config:
    """Baca konfigurasi; file hilang atau rusak dikembalikan sebagai default."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_config()
    if not isinstance(raw, dict):
        return default_config()
    base = default_config()
    return Config(
        ai_base_url=str(raw.get("ai_base_url", base.ai_base_url)),
        ai_api_key=str(raw.get("ai_api_key", base.ai_api_key)),
        ai_model=str(raw.get("ai_model", base.ai_model)),
        ai_temperature=_coerce_float(raw.get("ai_temperature"), base.ai_temperature),
    )


def save_config(cfg: Config, path: Path) -> None:
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    path.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
