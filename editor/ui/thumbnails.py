"""Thumbnail generation helpers for supported input files."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from editor.constants import IMAGE_EXTENSIONS, PDF_EXTENSION

THUMBNAIL_SIZE = 48


def _thumbnail_for_image(path: Path, rotation: int = 0) -> QPixmap | None:
    """Generate a thumbnail from an image file."""
    try:
        img = Image.open(path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if rotation:
            img = img.rotate(-rotation, expand=True)
        img.thumbnail((THUMBNAIL_SIZE * 2, THUMBNAIL_SIZE * 2), Image.Resampling.LANCZOS)
        data = img.tobytes("raw", "RGB")
        bytes_per_line = img.width * 3
        qimg = QImage(data, img.width, img.height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(
            THUMBNAIL_SIZE,
            THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None


def _thumbnail_for_pdf(path: Path, rotation: int = 0) -> QPixmap | None:
    """Generate a thumbnail from the first page of a PDF."""
    try:
        import fitz

        doc = fitz.open(path)
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        scale = THUMBNAIL_SIZE / max(page.rect.width, page.rect.height)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
            "raw",
            "RGB",
            pix.stride,
            1,
        )
        doc.close()
        if rotation:
            img = img.rotate(-rotation, expand=True)
        data = img.tobytes("raw", "RGB")
        bytes_per_line = img.width * 3
        qimg = QImage(data, img.width, img.height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(
            THUMBNAIL_SIZE,
            THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None


def create_file_thumbnail(path: str, rotation: int = 0) -> QPixmap | None:
    """Create a small thumbnail for a file (image or PDF)."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return _thumbnail_for_image(p, rotation)
    if suffix == PDF_EXTENSION:
        return _thumbnail_for_pdf(p, rotation)
    return None
