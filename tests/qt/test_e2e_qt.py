"""Menjalankan simulasi E2E Qt (biochar) tanpa AI nyata sebagai bagian suite.

Sim membangun jendela Qt OFFSCREEN dengan data di tempfile dan fake AI client
(jawaban kanonik + aliran SSE), lalu meng-assert isi DOCX hasil ekspor.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / ".superpowers" / "user_sim_qt_biochar.py"


def test_simulasi_e2e_qt_biochar_tanpa_ai_nyata():
    assert SIM.is_file(), f"sim tidak ada: {SIM}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"  # sim memang dirancang offscreen
    result = subprocess.run(
        [sys.executable, str(SIM)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=600,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "SIM OK" in result.stdout
