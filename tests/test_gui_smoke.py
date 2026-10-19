"""Menjalankan smoke GUI penuh sebagai bagian suite (penjaga regresi alur tab).

Smoke membuat jendela Tk sesungguhnya sehingga butuh sesi ber monitor; di CI
tanpa layar tes ini gagal dan boleh dimatikan dengan env GENERATOR_SKIP_GUI=1.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gui_smoke_end_to_end():
    if os.environ.get("GENERATOR_SKIP_GUI"):
        import pytest

        pytest.skip("Dimatikan lewat GENERATOR_SKIP_GUI")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "gui_smoke.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=300,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "SMOKE OK" in result.stdout
