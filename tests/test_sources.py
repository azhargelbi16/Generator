import pytest
from generator.sources import web_reader, pdf_reader, errors


class _Resp:
    status_code = 200
    encoding = "utf-8"

    def __init__(self, body="", content_type="text/html", location=""):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        if location:
            self.headers["Location"] = location

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=65536):
        yield self._body


def _host_publik(monkeypatch):
    monkeypatch.setattr(web_reader, "_host_is_public", lambda host: True)


def test_source_read_error_is_single_class():
    assert pdf_reader.SourceReadError is web_reader.SourceReadError is errors.SourceReadError


def test_fetch_text_extracts_html(monkeypatch):
    _host_publik(monkeypatch)
    resp = _Resp(
        "<html><head><title>Judul</title></head><body><p>Halo</p>"
        "<script>x()</script></body></html>"
    )
    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: resp)
    assert "Halo" in web_reader.fetch_text("http://example.com")
    assert "x()" not in web_reader.fetch_text("http://example.com")
    assert web_reader.fetch_metadata("http://example.com")["title"] == "Judul"


def test_menolak_skema_selain_http(monkeypatch):
    dipanggil = []
    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: dipanggil.append(a))
    with pytest.raises(web_reader.SourceReadError, match="http"):
        web_reader.fetch_text("file:///C:/Windows/win.ini")
    assert dipanggil == []


def test_menolak_alamat_loopback_dan_privat(monkeypatch):
    dipanggil = []
    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: dipanggil.append(a))
    monkeypatch.setattr(
        web_reader.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(web_reader.SourceReadError, match="tidak diizinkan"):
        web_reader.fetch_text("http://localhost/admin")
    assert dipanggil == []

    monkeypatch.setattr(
        web_reader.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("169.254.169.254", 80))],
    )
    with pytest.raises(web_reader.SourceReadError, match="tidak diizinkan"):
        web_reader.fetch_text("http://metadata.example/latest")


def test_menerima_alamat_publik(monkeypatch):
    monkeypatch.setattr(
        web_reader.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    assert web_reader._host_is_public("example.com") is True


def test_membatasi_ukuran_respons(monkeypatch):
    _host_publik(monkeypatch)

    class Besar(_Resp):
        def iter_content(self, chunk_size=65536):
            yield b"x" * (web_reader.MAX_BYTES + 1)

    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: Besar())
    with pytest.raises(web_reader.SourceReadError, match="terlalu besar"):
        web_reader.fetch_text("http://example.com")


def test_redirect_ke_alamat_privat_ditolak(monkeypatch):
    publik = {"example.com": True, "169.254.169.254": False}
    monkeypatch.setattr(
        web_reader, "_host_is_public", lambda host: publik.get(host, False)
    )
    resp = _Resp(location="http://169.254.169.254/latest/meta-data")
    resp.status_code = 302
    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: resp)
    with pytest.raises(web_reader.SourceReadError, match="tidak diizinkan"):
        web_reader.fetch_text("http://example.com/artikel")


def test_pesan_error_tidak_memuat_query_sensitif(monkeypatch):
    _host_publik(monkeypatch)

    def gagal(*args, **kwargs):
        raise web_reader.requests.RequestException("blocked")

    monkeypatch.setattr(web_reader.requests, "get", gagal)
    with pytest.raises(web_reader.SourceReadError) as info:
        web_reader.fetch_text("http://example.com/artikel?token=rahasia")
    assert "token=rahasia" not in str(info.value)
    assert "example.com/artikel" in str(info.value)


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


def test_web_reader_direct_pdf_detection(monkeypatch):
    _host_publik(monkeypatch)

    class FakePdfResp(_Resp):
        def __init__(self):
            super().__init__(body="", content_type="application/pdf")
            self._body = b"%PDF-1.4 fake pdf binary bytes"

    monkeypatch.setattr(web_reader.requests, "get", lambda *a, **k: FakePdfResp())
    monkeypatch.setattr(pdf_reader, "extract_text_or_ocr", lambda p: "Full paper from direct PDF link")
    monkeypatch.setattr(pdf_reader, "extract_metadata", lambda p: {"title": "PDF Paper Title"})

    text, meta = web_reader.fetch("http://example.com/paper.pdf")
    assert text == "Full paper from direct PDF link"
    assert meta["title"] == "PDF Paper Title"


def test_web_reader_auto_follows_citation_pdf(monkeypatch):
    _host_publik(monkeypatch)

    html_body = (
        '<html><head>'
        '<title>Journal Article</title>'
        '<meta name="citation_title" content="Meta Title">'
        '<meta name="citation_author" content="Dr. Author">'
        '<meta name="citation_pdf_url" content="http://example.com/download.pdf">'
        '</head><body><p>Abstract only in HTML</p></body></html>'
    )

    def fake_get(url, *a, **k):
        if "download.pdf" in url:
            r = _Resp(body="", content_type="application/pdf")
            r._body = b"%PDF-1.4 full paper"
            return r
        return _Resp(body=html_body, content_type="text/html")

    monkeypatch.setattr(web_reader.requests, "get", fake_get)
    monkeypatch.setattr(pdf_reader, "extract_text_or_ocr", lambda p: "Full 20-page text from open-access PDF")
    monkeypatch.setattr(pdf_reader, "extract_metadata", lambda p: {"doi": "10.1234/test"})

    text, meta = web_reader.fetch("http://example.com/article/view/1")
    assert text == "Full 20-page text from open-access PDF"
    assert meta["title"] == "Meta Title"
    assert meta["author"] == "Dr. Author"
    assert meta["doi"] == "10.1234/test"

