from generator import logging_setup


def test_logging_writes_to_file(tmp_path):
    log = tmp_path / "app.log"
    logging_setup.setup_logging(log)
    logging_setup.get_logger("x").error("boom")
    assert "boom" in log.read_text(encoding="utf-8")


def test_log_dirotasi(tmp_path):
    import logging
    from logging.handlers import RotatingFileHandler

    logging_setup.setup_logging(tmp_path / "app.log")
    handler = logging.getLogger().handlers[0]
    assert isinstance(handler, RotatingFileHandler)
    assert handler.maxBytes > 0 and handler.backupCount >= 1


def test_api_key_disamarkan_di_log(tmp_path):
    log = tmp_path / "app.log"
    logging_setup.setup_logging(log)
    logging_setup.get_logger("x").error("gagal memakai sk-rahasia123456 dan Bearer tokenabc")
    isi = log.read_text(encoding="utf-8")
    assert "sk-rahasia123456" not in isi
    assert "tokenabc" not in isi
