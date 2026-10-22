from pathlib import Path


def test_run_bat_bootstraps_and_launches():
    txt = Path("run.bat").read_text(encoding="utf-8").lower()
    assert "python" in txt
    assert "venv" in txt
    assert "requirements.txt" in txt
    assert "generator.web.app" in txt
    assert "ocr" in txt or "onnx" in txt  # pesan progres dependensi besar (16)
