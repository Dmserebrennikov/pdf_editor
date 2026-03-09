"""PDF merge and image-to-PDF conversion logic."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter, PdfReader
from PIL import Image
import io

# Supported image extensions for conversion to PDF
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSION = ".pdf"


def image_to_pdf_bytes(image_path: Path) -> bytes:
    """Convert a single image file to a one-page PDF as bytes."""
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    buf.seek(0)
    return buf.read()


def merge_files_to_pdf(file_paths: list[Path], output_path: Path) -> None:
    """
    Merge a list of PDF and/or image files (JPEG/PNG) into a single PDF.
    Images are converted to PDF pages on the fly.
    """
    writer = PdfWriter()
    for path in file_paths:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        suffix = path.suffix.lower()
        if suffix == PDF_EXTENSION:
            reader = PdfReader(str(path))
            for page in reader.pages:
                writer.add_page(page)
        elif suffix in IMAGE_EXTENSIONS:
            pdf_bytes = image_to_pdf_bytes(path)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)
        else:
            raise ValueError(f"Unsupported file type: {path.name}")
    with open(output_path, "wb") as f:
        writer.write(f)
