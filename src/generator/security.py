"""Modul keamanan dan enkripsi data sensitif (DPAPI Windows dan POSIX fallback).

Menyediakan enkripsi at-rest untuk draf dan konfigurasi API key, serta
pembatasan izin akses berkas pada Windows (icacls) dan Linux/macOS (chmod 0o600).
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

log = logging.getLogger("generator.security")

_ENTROPY = b"generator_laporan_academic_v2"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def is_windows() -> bool:
    """Periksa apakah sistem operasi saat ini adalah Windows."""
    return os.name == "nt" and hasattr(ctypes, "windll")


def dpapi_protect(data: bytes) -> bytes | None:
    """Enkripsi bytes menggunakan Windows DPAPI CryptProtectData."""
    if not is_windows():
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        data_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)),
        )
        entropy_blob = _DATA_BLOB(
            len(_ENTROPY),
            ctypes.cast(ctypes.create_string_buffer(_ENTROPY), ctypes.POINTER(ctypes.c_byte)),
        )
        data_out = _DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(data_in),
            "generator_security",
            ctypes.byref(entropy_blob),
            None,
            None,
            0,
            ctypes.byref(data_out),
        ):
            return None
        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            kernel32.LocalFree(data_out.pbData)
    except Exception as exc:
        log.warning("Enkripsi DPAPI gagal: %s", exc)
        return None


def dpapi_unprotect(data: bytes) -> bytes | None:
    """Dekripsi bytes menggunakan Windows DPAPI CryptUnprotectData."""
    if not is_windows():
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        data_in = _DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)),
        )
        entropy_blob = _DATA_BLOB(
            len(_ENTROPY),
            ctypes.cast(ctypes.create_string_buffer(_ENTROPY), ctypes.POINTER(ctypes.c_byte)),
        )
        data_out = _DATA_BLOB()
        # Coba unprotect dengan entropy dahulu (v2), bila gagal coba tanpa entropy (v1 backward-compatible)
        success = crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            0,
            ctypes.byref(data_out),
        )
        if not success:
            success = crypt32.CryptUnprotectData(
                ctypes.byref(data_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(data_out),
            )
        if not success:
            return None
        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            kernel32.LocalFree(data_out.pbData)
    except Exception as exc:
        log.warning("Dekripsi DPAPI gagal: %s", exc)
        return None


def _get_machine_key() -> bytes:
    """Hasilkan kunci mesin unik per pengguna untuk POSIX/fallback encryption."""
    user = os.environ.get("USER", os.environ.get("USERNAME", "default_user"))
    node = str(os.environ.get("HOST", os.uname().nodename if hasattr(os, "uname") else "localhost"))
    return hashlib.sha256(f"{user}@{node}:{_ENTROPY.decode('ascii')}".encode("utf-8")).digest()


def _posix_encrypt(data: bytes) -> bytes:
    """Enkripsi berbasis key stream XOR + HMAC per pengguna untuk lingkungan POSIX."""
    key = _get_machine_key()
    keystream = hashlib.sha512(key + b":stream").digest()
    while len(keystream) < len(data):
        keystream += hashlib.sha512(keystream).digest()
    encrypted = bytes(b ^ k for b, k in zip(data, keystream[:len(data)]))
    tag = hashlib.sha256(key + encrypted).digest()
    return tag + encrypted


def _posix_decrypt(data: bytes) -> bytes | None:
    """Dekripsi berbasis key stream XOR + HMAC untuk lingkungan POSIX."""
    if len(data) < 32:
        return None
    key = _get_machine_key()
    expected_tag = data[:32]
    encrypted = data[32:]
    actual_tag = hashlib.sha256(key + encrypted).digest()
    if actual_tag != expected_tag:
        log.warning("Verifikasi tag integritas POSIX encryption gagal.")
        return None
    keystream = hashlib.sha512(key + b":stream").digest()
    while len(keystream) < len(encrypted):
        keystream += hashlib.sha512(keystream).digest()
    return bytes(b ^ k for b, k in zip(encrypted, keystream[:len(encrypted)]))


def encrypt_string(plaintext: str) -> str:
    """Enkripsi teks menjadi amplop JSON terenkripsi (base64 payload)."""
    raw_bytes = plaintext.encode("utf-8")
    blob = dpapi_protect(raw_bytes)
    method = "dpapi"
    if blob is None:
        blob = _posix_encrypt(raw_bytes)
        method = "posix_machine"

    envelope = {
        "version": 2,
        "encrypted": True,
        "method": method,
        "payload": base64.b64encode(blob).decode("ascii"),
    }
    return json.dumps(envelope, indent=2)


def decrypt_string(ciphertext: str) -> str | None:
    """Dekripsi amplop JSON atau string polos. Mengembalikan teks asli atau None jika rusak."""
    text = ciphertext.strip()
    if not text:
        return ""
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        # Bukan JSON, anggap sebagai plaintext asli
        return text

    if not isinstance(raw, dict) or not raw.get("encrypted") or "payload" not in raw:
        # JSON biasa yang tidak terenkripsi
        return text

    try:
        blob = base64.b64decode(raw["payload"])
        method = raw.get("method", "dpapi")
        if method == "dpapi" or is_windows():
            dec = dpapi_unprotect(blob)
            if dec is not None:
                return dec.decode("utf-8")
        # Coba POSIX fallback bila DPAPI gagal atau method adalah posix
        dec_posix = _posix_decrypt(blob)
        if dec_posix is not None:
            return dec_posix.decode("utf-8")
    except Exception as exc:
        log.error("Gagal mendekripsi payload: %s", exc)
    return None


def restrict_file_permissions(path: Path) -> bool:
    """Set izin berkas agar hanya pengguna saat ini yang memiliki akses baca/tulis."""
    path = Path(path)
    if not path.is_file():
        return False
    if not is_windows():
        try:
            os.chmod(path, 0o600)
            return True
        except OSError:
            return False

    username = os.environ.get("USERNAME")
    if not username:
        return False
    try:
        cmd = ["icacls", str(path), "/inheritance:r", "/grant:r", f"{username}:(F)"]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return res.returncode == 0
    except Exception as exc:
        log.warning("Gagal membatasi izin berkas %s: %s", path.name, exc)
        return False

