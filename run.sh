#!/usr/bin/env bash
# Generator Laporan - Cross-Platform Linux/macOS Launcher

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=== Generator Laporan Akademik (Cross-Platform) ==="

# 1. Deteksi Python 3.11+ / 3.12
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.11+ tidak ditemukan di sistem."
    echo "Silakan pasang Python 3.11 atau 3.12 dari https://www.python.org/downloads/ atau package manager Anda."
    exit 1
fi

echo "Menggunakan: $($PYTHON_BIN --version)"

# 2. Virtual Environment
if [ ! -f ".venv/bin/python" ]; then
    echo "[1/3] Membuat virtual environment .venv ..."
    "$PYTHON_BIN" -m venv .venv
fi

VPY="$DIR/.venv/bin/python"

# 3. Dependensi
if [ ! -f ".venv/.deps_ok" ]; then
    echo "[2/3] Memasang dependensi dari requirements.txt ..."
    "$VPY" -m pip install --upgrade pip
    "$VPY" -m pip install -r requirements.txt
    touch ".venv/.deps_ok"
fi

# 4. Jalankan Aplikasi
echo "[3/3] Menjalankan Generator Laporan Webview Desktop ..."
export PYTHONPATH="$DIR/src"
exec "$VPY" -m generator.web.app

