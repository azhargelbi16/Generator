from generator import logging_setup


def test_logging_writes_to_file(tmp_path):
    log = tmp_path / "app.log"
    logging_setup.setup_logging(log)
    logging_setup.get_logger("x").error("boom")
    assert "boom" in log.read_text(encoding="utf-8")
