from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def make_scanned_pdf(path: Path, text: str) -> Path:
    img = Image.new("RGB", (1200, 260), "white")
    font = ImageFont.load_default(size=44)
    ImageDraw.Draw(img).text((40, 100), text, fill="black", font=font)
    img.save(path, "PDF", resolution=150)
    return path
