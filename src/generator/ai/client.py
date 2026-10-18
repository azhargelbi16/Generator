"""Klien untuk endpoint OpenAI-compatible dan tes koneksi (15)."""

from __future__ import annotations

import requests

from ..config import Config

TIMEOUT = 60


class AIError(Exception):
    """Panggilan ke layanan AI gagal."""


class AIClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        url = f"{self.cfg.ai_base_url.rstrip('/')}/chat/completions"
        payload: dict = {
            "model": self.cfg.ai_model,
            "messages": messages,
            "temperature": self.cfg.ai_temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.cfg.ai_api_key}"}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            if response.status_code >= 400:
                raise AIError(
                    f"Layanan AI menolak permintaan (HTTP {response.status_code})."
                )
            response.raise_for_status()
            data = response.json()
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"Gagal menghubungi layanan AI: {exc}") from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise AIError("Respons AI tidak memuat pilihan jawaban (choices).")
        try:
            return choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Format respons AI tidak dikenal.") from exc


def check_connection(client: AIClient) -> tuple[bool, str]:
    """Kirim pesan uji singkat; kembalikan (berhasil, pesan) untuk tab Pengaturan."""
    try:
        client.chat([{"role": "user", "content": "ping"}])
    except AIError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)
    return True, "Koneksi berhasil"
