"""Klien untuk endpoint OpenAI-compatible dan tes koneksi."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from ..config import Config

TIMEOUT = 120
STREAM_TIMEOUT = 300
PROBE_TIMEOUT = 8
DEFAULT_MAX_TOKENS = 4096
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_BACKOFFS = (2.0, 4.0, 8.0)

log = logging.getLogger("generator.ai.client")


class AIError(Exception):
    """Panggilan ke layanan AI gagal."""


class StreamError(AIError):
    """Streaming tidak didukung server atau terputus di tengah jalan."""


def _parse_retry_after(header_val: str | None, default_backoff: float) -> float:
    """Hormati header Retry-After (detik atau HTTP date), fallback ke backoff bawaan."""
    if not header_val:
        return default_backoff
    header_val = header_val.strip()
    try:
        val = float(header_val)
        return max(0.0, val)
    except ValueError:
        pass
    try:
        from datetime import datetime, timezone
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(header_val)
        now = datetime.now(timezone.utc)
        diff = (dt - now).total_seconds()
        return max(0.0, diff)
    except Exception:
        return default_backoff


def _parse_body(text: str) -> dict:
    """Parsih badan respons JSON; toleran bingkai SSE dari router."""
    stripped = text.strip()
    if stripped.startswith("data:"):
        stripped = stripped[5:].lstrip()
    data, _end = json.JSONDecoder().raw_decode(stripped)
    return data


def _get_headers(cfg: Config) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GeneratorLaporan/2.0",
        "HTTP-Referer": "https://generator-laporan.local",
        "X-Title": "Generator Laporan",
    }
    if cfg.ai_api_key and cfg.ai_api_key.strip():
        headers["Authorization"] = f"Bearer {cfg.ai_api_key.strip()}"
    return headers


class AIClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        url = f"{self.cfg.ai_base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.cfg.ai_model,
            "messages": messages,
            "temperature": self.cfg.ai_temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = _get_headers(self.cfg)

        data = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
                if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFFS[attempt]
                    retry_after = (
                        response.headers.get("Retry-After")
                        if hasattr(response, "headers")
                        else None
                    )
                    sleep_time = _parse_retry_after(retry_after, backoff)
                    log.warning(
                        "AI HTTP %d pada percobaan %d/%d, mencoba ulang dalam %.1fs...",
                        response.status_code,
                        attempt + 1,
                        MAX_RETRIES,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code >= 400:
                    raise AIError(
                        f"Layanan AI menolak permintaan (HTTP {response.status_code}): {response.text[:150]}"
                    )
                response.raise_for_status()
                data = _parse_body(response.text)
                break
            except requests.exceptions.Timeout as exc:
                if attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFFS[attempt]
                    log.warning(
                        "AI timeout pada percobaan %d/%d, mencoba ulang dalam %.1fs...",
                        attempt + 1,
                        MAX_RETRIES,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                raise AIError(
                    f"Gagal menghubungi layanan AI (timeout setelah {MAX_RETRIES} retry): {exc}"
                ) from exc
            except AIError:
                raise
            except ValueError as exc:
                raise AIError(f"Format respons AI tidak dikenal: {exc}") from exc
            except Exception as exc:
                raise AIError(f"Gagal menghubungi layanan AI: {exc}") from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise AIError("Respons AI tidak memuat pilihan jawaban (choices).")
        first_choice = choices[0] if isinstance(choices, list) and choices else None
        if not isinstance(first_choice, dict):
            raise AIError("Format pilihan respons AI tidak valid.")
        if first_choice.get("finish_reason") == "length":
            raise AIError("Respons AI terpotong karena batas token (finish_reason=length).")
        try:
            msg = first_choice["message"]
            content = msg.get("content")
            if not content and "reasoning_content" in msg:
                content = msg["reasoning_content"]
            return content or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Format respons AI tidak dikenal.") from exc

    def chat_stream(
        self,
        messages: list[dict],
        json_mode: bool = False,
        cancel=None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        url = f"{self.cfg.ai_base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.cfg.ai_model,
            "messages": messages,
            "temperature": self.cfg.ai_temperature,
            "stream": True,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = _get_headers(self.cfg)

        response = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=STREAM_TIMEOUT, stream=True
                )
                if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFFS[attempt]
                    retry_after = (
                        response.headers.get("Retry-After")
                        if hasattr(response, "headers")
                        else None
                    )
                    sleep_time = _parse_retry_after(retry_after, backoff)
                    log.warning(
                        "AI streaming HTTP %d pada percobaan %d/%d, mencoba ulang dalam %.1fs...",
                        response.status_code,
                        attempt + 1,
                        MAX_RETRIES,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code >= 400:
                    raise StreamError(
                        f"Layanan AI menolak streaming (HTTP {response.status_code})."
                    )
                break
            except requests.exceptions.Timeout as exc:
                if attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFFS[attempt]
                    time.sleep(backoff)
                    continue
                raise StreamError(f"Gagal membuka streaming AI (timeout): {exc}") from exc
            except StreamError:
                raise
            except Exception as exc:
                raise StreamError(f"Gagal membuka streaming AI: {exc}") from exc

        if response is None:
            raise StreamError("Tidak ada respons dari layanan AI streaming.")

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
                first_choice = choices[0]
                if isinstance(first_choice, dict) and first_choice.get("finish_reason") == "length":
                    raise StreamError(
                        "Streaming AI terpotong karena batas token (finish_reason=length)."
                    )
                delta = first_choice.get("delta") or {}
                content = delta.get("content") or delta.get("reasoning_content")
                if content:
                    yield content
        except StreamError:
            raise
        except Exception as exc:
            raise StreamError(f"Streaming AI terputus: {exc}") from exc


def check_connection(client: AIClient) -> tuple[bool, str]:
    """Tes koneksi cepat (non-blocking, timeout 8 detik) dengan verifikasi endpoint dan model."""
    base_url = client.cfg.ai_base_url.rstrip("/")
    headers = _get_headers(client.cfg)

    # 1. Tes keterjangkauan endpoint (GET /models atau /v1/models)
    models_urls = [f"{base_url}/models"]
    if not base_url.endswith("/v1"):
        models_urls.insert(0, f"{base_url}/v1/models")

    server_alive = False
    for m_url in models_urls:
        try:
            r = requests.get(m_url, headers=headers, timeout=PROBE_TIMEOUT)
            if r.status_code < 500:
                server_alive = True
                break
        except requests.exceptions.RequestException:
            continue

    if not server_alive:
        # Coba ping langsung ke root base_url
        try:
            r = requests.get(base_url, headers=headers, timeout=PROBE_TIMEOUT)
            if r.status_code < 500:
                server_alive = True
        except requests.exceptions.RequestException as exc:
            return False, f"Tidak dapat terhubung ke {base_url}. Pastikan router/server AI sudah aktif."

    # 2. Tes model spesifik bila ada model yang dipilih
    if client.cfg.ai_model:
        chat_url = f"{base_url}/chat/completions"
        payload = {
            "model": client.cfg.ai_model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        try:
            r = requests.post(chat_url, headers=headers, json=payload, timeout=PROBE_TIMEOUT)
            if r.status_code == 200:
                return True, f"Koneksi berhasil! Model '{client.cfg.ai_model}' siap digunakan."
            elif r.status_code in (404, 400):
                return False, f"Server terhubung, namun model '{client.cfg.ai_model}' tidak ditemukan (HTTP {r.status_code}). Klik 'Ambil Model dari Server' untuk memilih model yang tersedia."
            elif r.status_code in (401, 403):
                return False, f"Autentikasi ditolak (HTTP {r.status_code}). Periksa API Key Anda."
            else:
                return False, f"Server merespons HTTP {r.status_code}: {r.text[:120]}"
        except requests.exceptions.Timeout:
            return False, "Koneksi timeout (>8 detik). Endpoint merespons lambat."
        except requests.exceptions.RequestException as exc:
            return False, f"Gagal menghubungi chat/completions: {exc}"

    return True, "Server terhubung dan siap."


def list_models(cfg: Config) -> list[str]:
    """Ambil daftar id model dari GET /models atau /v1/models secara cepat dan toleran."""
    base_url = cfg.ai_base_url.rstrip("/")
    headers = _get_headers(cfg)

    candidate_urls = [f"{base_url}/models"]
    if not base_url.endswith("/v1"):
        candidate_urls.insert(0, f"{base_url}/v1/models")
    else:
        # Base url berakhir /v1, juga sediakan tanpa /v1
        candidate_urls.append(f"{base_url[:-3]}/models")

    last_error = "Tidak ada respons dari server."
    data = None
    for url in candidate_urls:
        try:
            response = requests.get(url, headers=headers, timeout=PROBE_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                break
            elif response.status_code < 500:
                last_error = f"HTTP {response.status_code}: {response.text[:100]}"
        except Exception as exc:
            last_error = str(exc)
            continue

    if data is None:
        raise AIError(f"Gagal mengambil daftar model: {last_error}")

    ids: list[str] = []
    # 1. Format OpenAI / 9Router / OpenRouter ({"data": [{"id": "..."}, ...]})
    if isinstance(data, dict):
        raw_list = data.get("data") or data.get("models") or data.get("result") or data.get("items")
        if isinstance(raw_list, list):
            for entry in raw_list:
                if isinstance(entry, dict):
                    m_id = entry.get("id") or entry.get("name") or entry.get("model")
                    if m_id:
                        ids.append(str(m_id))
                elif isinstance(entry, str):
                    ids.append(entry)
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                m_id = entry.get("id") or entry.get("name") or entry.get("model")
                if m_id:
                    ids.append(str(m_id))
            elif isinstance(entry, str):
                ids.append(entry)

    if not ids:
        raise AIError("Server tidak mendukung format daftar model standar atau respons kosong.")

    # Deduplikasi dengan menjaga urutan server
    seen = set()
    unique_ids: list[str] = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            unique_ids.append(item)
    return unique_ids
