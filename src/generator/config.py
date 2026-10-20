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
    citation_style: str = "et_al"
    dosen_review: bool = False


_PESAN_SUHU_ANGKA = "Temperatur harus berupa angka, mis. 0.2"
_PESAN_SUHU_RENTANG = "Temperatur harus di antara 0 dan 2"


def parse_temperature(text: str) -> float:
    """Terima koma atau titik desimal; tolak bukan angka dan nilai di luar 0-2."""
    try:
        temperature = float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(_PESAN_SUHU_ANGKA) from None
    if not 0.0 <= temperature <= 2.0:
        raise ValueError(_PESAN_SUHU_RENTANG)
    return temperature


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
        citation_style=str(raw.get("citation_style", base.citation_style)),
        dosen_review=bool(raw.get("dosen_review", base.dosen_review)),
    )


def save_config(cfg: Config, path: Path) -> None:
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    path.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
