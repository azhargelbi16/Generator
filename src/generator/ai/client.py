"""Klien untuk endpoint OpenAI-compatible dan tes koneksi (15)."""

from __future__ import annotations

import json

import requests

from ..config import Config

TIMEOUT = 180


class AIError(Exception):
    """Panggilan ke layanan AI gagal."""


class StreamError(AIError):
    """Streaming tidak didukung server atau terputus di tengah jalan."""


def _parse_body(text: str) -> dict:
    """Parsih badan respons JSON; toleran bingkai SSE dari router.

    9Router terbukti membalas JSON utuh diikuti penanda "data: [DONE]"
    meski streaming tidak diminta (HTTP 200, content-type event-stream);
    sebagian layanan lain memakai event "data: {...}" biasa. Ambil dokumen
    JSON pertama dari badan, apa pun sisanya.
    """
    stripped = text.strip()
    if stripped.startswith("data:"):
        stripped = stripped[5:].lstrip()
    data, _end = json.JSONDecoder().raw_decode(stripped)
    return data


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
            data = _parse_body(response.text)
        except AIError:
            raise
        except ValueError as exc:
            raise AIError(f"Format respons AI tidak dikenal: {exc}") from exc
        except Exception as exc:
            raise AIError(f"Gagal menghubungi layanan AI: {exc}") from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise AIError("Respons AI tidak memuat pilihan jawaban (choices).")
        try:
            return choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Format respons AI tidak dikenal.") from exc

    def chat_stream(self, messages: list[dict], json_mode: bool = False, cancel=None):
        """Yield potongan teks delta SSE; berhenti bersih bila `cancel` ter-set.

        Server yang menolak streaming (HTTP >= 400) memicu StreamError supaya
        pemanggil bisa fallback ke chat(). `chat()` sendiri tidak berubah.
        """
        url = f"{self.cfg.ai_base_url.rstrip('/')}/chat/completions"
        payload: dict = {
            "model": self.cfg.ai_model,
            "messages": messages,
            "temperature": self.cfg.ai_temperature,
            "stream": True,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.cfg.ai_api_key}"}
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=TIMEOUT, stream=True
            )
        except Exception as exc:
            raise StreamError(f"Gagal membuka streaming AI: {exc}") from exc
        if response.status_code >= 400:
            raise StreamError(
                f"Layanan AI menolak streaming (HTTP {response.status_code})."
            )
        try:
            for raw in response.iter_lines():
                if cancel is not None and cancel.is_set():
                    return
                if not raw:
                    continue
                line = (
                    raw.decode("utf-8", "replace")
                    if isinstance(raw, (bytes, bytearray))
                    else str(raw)
                )
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    event = json.loads(data)
                except ValueError as exc:
                    raise StreamError(f"Bingkai streaming AI tidak dikenal: {exc}") from exc
                if not isinstance(event, dict):
                    continue
                if event.get("error"):
                    raise StreamError(f"Layanan AI mengirim error streaming: {event['error']}")
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content
        except StreamError:
            raise
        except Exception as exc:
            raise StreamError(f"Streaming AI terputus: {exc}") from exc


def check_connection(client: AIClient) -> tuple[bool, str]:
    """Kirim pesan uji singkat; kembalikan (berhasil, pesan) untuk tab Pengaturan."""
    try:
        client.chat([{"role": "user", "content": "ping"}])
    except AIError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)
    return True, "Koneksi berhasil"
