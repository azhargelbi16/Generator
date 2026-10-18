import pytest
from generator.sources import web_reader, pdf_reader, errors


def test_source_read_error_is_single_class():
    assert pdf_reader.SourceReadError is web_reader.SourceReadError is errors.SourceReadError


def test_fetch_text_extracts_html(monkeypatch):
    class Resp:
        headers = {"Content-Type": "text/html"}
        text = "<html><head><title>Judul</title></head><body><p>Halo</p><script>x()</script></body></html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: Resp())
    assert "Halo" in web_reader.fetch_text("http://x")
    assert "x()" not in web_reader.fetch_text("http://x")
    assert web_reader.fetch_metadata("http://x")["title"] == "Judul"


def test_extract_text_missing_file_raises(tmp_path):
    with pytest.raises(pdf_reader.SourceReadError):
        pdf_reader.extract_text(tmp_path / "nope.pdf")


def test_scan_detected_and_ocr_called(tmp_path, monkeypatch):
    from tests.fixtures.scan import make_scanned_pdf

    pdf = make_scanned_pdf(tmp_path / "s.pdf", "Laporan penelitian")
    assert pdf_reader.has_text_layer(pdf) is False
    monkeypatch.setattr(pdf_reader.ocr, "ocr_pdf", lambda p: "hasil ocr")
    assert pdf_reader.extract_text_or_ocr(pdf) == "hasil ocr"


def test_ocr_failure_becomes_source_error(tmp_path, monkeypatch):
    from tests.fixtures.scan import make_scanned_pdf
    from generator.sources import ocr

    pdf = make_scanned_pdf(tmp_path / "s.pdf", "Laporan penelitian")

    def boom(p):
        raise ocr.OcrError("gagal")

    monkeypatch.setattr(pdf_reader.ocr, "ocr_pdf", boom)
    with pytest.raises(pdf_reader.SourceReadError):
        pdf_reader.extract_text_or_ocr(pdf)


def test_web_request_error_becomes_source_error(monkeypatch):
    def boom(*a, **k):
        raise web_reader.requests.RequestException("blocked")

    monkeypatch.setattr(web_reader.requests, "get", boom)
    with pytest.raises(web_reader.SourceReadError):
        web_reader.fetch_text("http://x")
