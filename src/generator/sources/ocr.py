"""OCR untuk PDF pindaian.

Halaman dirender ke gambar dengan pypdfium2, lalu dikenali dengan rapidocr.
Mesin OCR dimuat sekali (lazy) supaya model tidak dibaca ulang tiap panggilan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DPI = 200


class OcrError(Exception):
    """Kegagalan membaca PDF atau mengenali teksnya (12.1)."""


_ENGINE: Any = None


def _engine() -> Any:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    try:
        from rapidocr import RapidOCR
    except Exception as exc:  # pragma: no cover - bergantung lingkungan
        raise OcrError(
            "Mesin OCR tidak bisa dimuat. Pastikan paket rapidocr dan "
            "onnxruntime sudah terpasang."
        ) from exc
    try:
        _ENGINE = RapidOCR()
    except Exception as exc:  # pragma: no cover - bergantung unduhan model
        raise OcrError(
            "Model OCR gagal dimuat. Sambungkan internet supaya model bisa "
            "diunduh sekali, lalu coba lagi."
        ) from exc
    return _ENGINE


def normalize(text: str) -> str:
    """Rapikan spasi dan ubah ke huruf kecil untuk pencocokan."""
    return " ".join(text.split()).lower()


def ocr_pdf(pdf_path: Path) -> str:
    """Kembalikan teks hasil OCR dari seluruh halaman PDF pindaian."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise OcrError(f"Berkas PDF tidak ditemukan: {pdf_path}")

    try:
        import pypdfium2 as pdfium
    except Exception as exc:  # pragma: no cover - bergantung lingkungan
        raise OcrError("Pustaka pypdfium2 tidak bisa dimuat.") from exc

    try:
        document = pdfium.PdfDocument(str(pdf_path))
    except Exception as exc:
        raise OcrError(f"PDF tidak bisa dibuka, mungkin rusak: {pdf_path}") from exc

    engine = _engine()
    pages: list[str] = []
    try:
        for index in range(len(document)):
            try:
                bitmap = document[index].render(scale=DPI / 72)
                image = bitmap.to_pil()
            except Exception as exc:
                raise OcrError(f"Halaman {index + 1} gagal dirender: {exc}") from exc
            try:
                result = engine(image)
            except Exception as exc:
                raise OcrError(f"OCR halaman {index + 1} gagal: {exc}") from exc
            txts = getattr(result, "txts", None)
            if txts:
                pages.append("\n".join(txts))
    finally:
        document.close()
    return "\n".join(pages)
