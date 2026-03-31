"""PDF merge and image-to-PDF conversion logic."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

from editor.constants import IMAGE_EXTENSIONS, PDF_EXTENSION


def image_to_pdf_bytes(image_path: Path, rotation: int = 0) -> bytes:
    """Convert a single image file to a one-page PDF as bytes."""
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if rotation:
        img = img.rotate(-rotation, expand=True)  # PIL uses CCW, so negate for CW
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    buf.seek(0)
    return buf.read()


def merge_files_to_pdf(
    file_paths: list[Path],
    output_path: Path,
    rotations: list[int] | None = None,
) -> None:
    """
    Merge a list of PDF and/or image files (JPEG/PNG) into a single PDF.
    rotations: optional list of clockwise angles (0, 90, 180, 270) per file.
    """
    if rotations is None:
        rotations = [0] * len(file_paths)
    if len(rotations) != len(file_paths):
        rotations = rotations + [0] * (len(file_paths) - len(rotations))

    writer = PdfWriter()
    for path, rotation in zip(file_paths, rotations):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        suffix = path.suffix.lower()
        if suffix == PDF_EXTENSION:
            reader = PdfReader(str(path))
            for page in reader.pages:
                writer.add_page(page.rotate(rotation))
        elif suffix in IMAGE_EXTENSIONS:
            pdf_bytes = image_to_pdf_bytes(path, rotation)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)
        else:
            raise ValueError(f"Unsupported file type: {path.name}")

    with open(output_path, "wb") as f:
        writer.write(f)
