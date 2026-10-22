"""Pembaca konten web (12.2).

Alamat divalidasi sebelum diminta: hanya http/https ke host publik. Alamat
loopback, privat, link-local, dan reserved ditolak supaya aplikasi tidak bisa
dipakai membaca layanan internal (SSRF). Pengalihan diikuti manual agar setiap
hop ikut divalidasi, dan ukuran respons dibatasi `MAX_BYTES`.
Mendukung ekstraksi otomatis teks lengkap PDF bila URL mengarah ke file PDF
atau bila halaman jurnal menyertakan tag `citation_pdf_url` (Open Access).
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from . import pdf_reader
from .errors import SourceReadError

__all__ = ["MAX_BYTES", "SourceReadError", "fetch", "fetch_text", "fetch_metadata"]

log = logging.getLogger("generator.sources.web")

TIMEOUT = 30
MAX_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_REDIRECTS = 5
_CHUNK = 64 * 1024
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _display_url(url: str) -> str:
    """URL tanpa query/fragment: token di query tidak boleh masuk pesan galat/log."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _host_is_public(host: str) -> bool:
    """True bila semua alamat hasil resolusi host adalah alamat publik."""
    try:
        addresses = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return False
    for info in addresses:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            return False
    return bool(addresses)


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise SourceReadError(
            "Hanya alamat http/https yang bisa diambil: " + _display_url(url)
        )
    if not parts.hostname or not _host_is_public(parts.hostname):
        raise SourceReadError("Alamat situs internal tidak diizinkan: " + _display_url(url))


def _unreachable(url: str, exc: Exception) -> SourceReadError:
    return SourceReadError(
        "Situs tidak bisa diakses (diblokir atau butuh JavaScript): " + _display_url(url)
    )


def _get(url: str):
    """GET dengan validasi tiap hop dan pengalihan manual."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_url(current)
        try:
            response = requests.get(
                current,
                headers=BROWSER_HEADERS,
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise _unreachable(current, exc) from exc
        if response.status_code in _REDIRECT_CODES:
            location = response.headers.get("Location") or ""
            if not location:
                raise SourceReadError("Pengalihan tanpa alamat tujuan: " + _display_url(current))
            current = urljoin(current, location)
            continue
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise _unreachable(current, exc) from exc
        return response
    raise SourceReadError("Terlalu banyak pengalihan: " + _display_url(url))


def _content_type(response) -> str:
    for key, value in getattr(response, "headers", {}).items():
        if key.lower() == "content-type":
            return str(value).lower()
    return ""


def _is_pdf_response(response, url: str) -> bool:
    ctype = _content_type(response)
    if "application/pdf" in ctype:
        return True
    path = urlsplit(url).path.lower()
    if path.endswith(".pdf"):
        return True
    return False


def _read_pdf_stream(response) -> tuple[str, dict[str, str]]:
    """Simpan stream PDF ke berkas sementara dan ekstrak teks + metadata."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = Path(tmp.name)
    total = 0
    try:
        for chunk in response.iter_content(chunk_size=_CHUNK):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_PDF_BYTES:
                raise SourceReadError(
                    f"Berkas PDF terlalu besar (lebih dari {MAX_PDF_BYTES // (1024 * 1024)} MB)."
                )
            tmp.write(chunk)
        tmp.close()

        text = pdf_reader.extract_text_or_ocr(tmp_path)
        meta = pdf_reader.extract_metadata(tmp_path)
        return text, meta
    finally:
        tmp.close()
        tmp_path.unlink(missing_ok=True)


def _read_text(response) -> str:
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.iter_content(chunk_size=_CHUNK):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                raise SourceReadError(
                    f"Halaman terlalu besar (lebih dari {MAX_BYTES // (1024 * 1024)} MB)."
                )
            chunks.append(chunk)
    except requests.RequestException as exc:
        raise SourceReadError("Gagal membaca isi halaman.") from exc
    encoding = getattr(response, "encoding", None) or "utf-8"
    return b"".join(chunks).decode(encoding, errors="replace")


def _parser(_content_type_value: str) -> str:
    return "html.parser"


def _soup(url: str) -> BeautifulSoup:
    response = _get(url)
    return BeautifulSoup(_read_text(response), _parser(_content_type(response)))


def _text_from_soup(soup: BeautifulSoup) -> str:
    # Buang elemen navigasi dan skrip agar fokus pada isi artikel/abstrak
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def _metadata_from_soup(soup: BeautifulSoup) -> dict[str, str]:
    result: dict[str, str] = {}
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    # Kumpulkan semua nama penulis jika ada banyak
    authors: list[str] = []
    for tag in soup.find_all("meta", attrs={"name": "citation_author"}):
        content = tag.get("content")
        if content and content.strip():
            authors.append(content.strip())
    if authors:
        result["author"] = "; ".join(authors)

    meta_map = {
        "citation_title": "title",
        "citation_publication_date": "date",
        "citation_date": "date",
        "citation_journal_title": "container",
        "citation_doi": "doi",
        "citation_pdf_url": "pdf_url",
    }
    for name, field in meta_map.items():
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content") and tag["content"].strip():
            result[field] = tag["content"].strip()
    return result


def fetch(url: str) -> tuple[str, dict[str, str]]:
    """Ambil teks dan metadata dari URL.
    
    Bila URL adalah PDF langsung: teks lengkap diekstrak via PDF/OCR.
    Bila URL adalah halaman HTML: diekstrak teks & metadata, lalu bila ada link
    `citation_pdf_url` (Open Access), sistem mencoba mengunduh PDF lengkapnya
    secara otomatis.
    """
    response = _get(url)

    # 1. Jika respons adalah berkas PDF langsung
    if _is_pdf_response(response, url):
        return _read_pdf_stream(response)

    # 2. Halaman web HTML
    html_text = _read_text(response)
    soup = BeautifulSoup(html_text, _parser(_content_type(response)))
    text = _text_from_soup(soup)
    meta = _metadata_from_soup(soup)

    # 3. Coba unduh PDF otomatis bila halaman jurnal menyertakan citation_pdf_url
    pdf_url = meta.pop("pdf_url", None)
    if pdf_url:
        target_pdf_url = urljoin(url, pdf_url)
        parsed_target = urlsplit(target_pdf_url)
        if parsed_target.hostname and _host_is_public(parsed_target.hostname):
            try:
                pdf_resp = _get(target_pdf_url)
                if _is_pdf_response(pdf_resp, target_pdf_url):
                    full_text, pdf_meta = _read_pdf_stream(pdf_resp)
                    if len(full_text.strip()) > len(text.strip()):
                        merged = dict(meta)
                        if not merged.get("doi") and pdf_meta.get("doi"):
                            merged["doi"] = pdf_meta["doi"]
                        return full_text, merged
            except Exception as e:
                log.info(f"Tidak dapat mengunduh PDF otomatis dari {target_pdf_url}: {e}")

    return text, meta


def fetch_text(url: str) -> str:
    text, _ = fetch(url)
    return text


def fetch_metadata(url: str) -> dict[str, str]:
    _, meta = fetch(url)
    return meta
