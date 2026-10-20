"""Menjalankan smoke nyata semua tab Qt sebagai bagian suite.

Smoke membuat jendela Qt sesungguhnya (bukan offscreen) sehingga butuh sesi
bermonitor; di CI tanpa layar tes ini gagal dan boleh dimatikan dengan env
GENERATOR_SKIP_GUI=1.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_qt_smoke_semua_tab_real_window():
    if os.environ.get("GENERATOR_SKIP_GUI"):
        pytest.skip("Dimatikan lewat GENERATOR_SKIP_GUI")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.pop("QT_QPA_PLATFORM", None)  # smoke nyata: jangan offscreen
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "qt_smoke_all.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=300,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "SMOKE OK" in result.stdout
