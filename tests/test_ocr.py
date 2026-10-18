import pytest
from tests.fixtures.scan import make_scanned_pdf
from generator.sources import ocr

WORDS = ["laporan", "pertanian", "organik", "indonesia", "penelitian"]


def test_ocr_reads_indonesian_scan(tmp_path):
    pdf = make_scanned_pdf(tmp_path / "scan.pdf",
                           "Laporan penelitian pertanian organik Indonesia")
    text = ocr.normalize(ocr.ocr_pdf(pdf))
    assert sum(w in text for w in WORDS) >= 3


def test_ocr_missing_file_raises(tmp_path):
    with pytest.raises(ocr.OcrError):
        ocr.ocr_pdf(tmp_path / "nope.pdf")
