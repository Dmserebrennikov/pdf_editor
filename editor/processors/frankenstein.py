"""Overlay donor PDF area onto an acceptor PDF page."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image
from pypdf import PdfReader

from editor.constants import PDF_EXTENSION

RectNorm = tuple[float, float, float, float]


def get_pdf_page_count(pdf_path: Path) -> int:
    """Return number of pages in a PDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != PDF_EXTENSION:
        raise ValueError("Input file must be a PDF.")
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


def render_pdf_page_image(pdf_path: Path, page_index: int, dpi: int = 150) -> Image.Image:
    """Render a single PDF page as a PIL image."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != PDF_EXTENSION:
        raise ValueError("Input file must be a PDF.")

    doc = fitz.open(str(pdf_path))
    try:
        if page_index < 0 or page_index >= len(doc):
            raise ValueError("Page index is out of range.")
        page = doc[page_index]
        scale = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
            "raw",
            "RGB",
            pix.stride,
            1,
        )
    finally:
        doc.close()


def _is_landscape(width: float, height: float) -> bool:
    return width > height


def _pdf_page_orientation(pdf_path: Path, page_index: int) -> bool:
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_index]
        return _is_landscape(page.rect.width, page.rect.height)
    finally:
        doc.close()


def _normalize_rect(rect: RectNorm) -> RectNorm:
    x, y, w, h = rect
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    w = max(0.0, min(1.0 - x, w))
    h = max(0.0, min(1.0 - y, h))
    return (x, y, w, h)


def compose_overlay_page_image(
    acceptor_image: Image.Image,
    donor_image: Image.Image,
    donor_rectangles_norm: list[RectNorm],
) -> Image.Image:
    """
    Create preview/output image by overlaying donor selected area
    onto the same normalized area on acceptor.
    """
    if not donor_rectangles_norm:
        raise ValueError("Select an area on the donor preview.")

    acc = acceptor_image.convert("RGB").copy()
    don = donor_image.convert("RGB")
    don_w, don_h = don.size
    acc_w, acc_h = acc.size

    pasted_any = False
    for rect in donor_rectangles_norm:
        x, y, w, h = _normalize_rect(rect)
        if w <= 0 or h <= 0:
            continue

        sx0 = int(round(x * don_w))
        sy0 = int(round(y * don_h))
        sx1 = int(round((x + w) * don_w))
        sy1 = int(round((y + h) * don_h))
        if sx1 <= sx0 or sy1 <= sy0:
            continue

        tx0 = int(round(x * acc_w))
        ty0 = int(round(y * acc_h))
        tx1 = int(round((x + w) * acc_w))
        ty1 = int(round((y + h) * acc_h))
        if tx1 <= tx0 or ty1 <= ty0:
            continue

        crop = don.crop((sx0, sy0, sx1, sy1))
        if crop.size != (tx1 - tx0, ty1 - ty0):
            crop = crop.resize((tx1 - tx0, ty1 - ty0), Image.Resampling.LANCZOS)
        acc.paste(crop, (tx0, ty0))
        pasted_any = True

    if not pasted_any:
        raise ValueError("Selected donor areas are invalid.")

    return acc


def create_overlay_pdf(
    acceptor_pdf_path: Path,
    acceptor_page_index: int,
    donor_pdf_path: Path,
    donor_page_index: int,
    donor_rectangles_norm: list[RectNorm],
    output_path: Path,
    dpi: int = 150,
) -> None:
    """Create one-page PDF with donor region overlaid onto acceptor page."""
    acceptor_pdf_path = Path(acceptor_pdf_path)
    donor_pdf_path = Path(donor_pdf_path)
    output_path = Path(output_path)

    orientation_a = _pdf_page_orientation(acceptor_pdf_path, acceptor_page_index)
    orientation_b = _pdf_page_orientation(donor_pdf_path, donor_page_index)
    if orientation_a != orientation_b:
        raise ValueError("Acceptor and donor pages must have the same orientation.")

    acceptor_image = render_pdf_page_image(acceptor_pdf_path, acceptor_page_index, dpi=dpi)
    donor_image = render_pdf_page_image(donor_pdf_path, donor_page_index, dpi=dpi)
    output_image = compose_overlay_page_image(acceptor_image, donor_image, donor_rectangles_norm)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    output_image.save(buf, format="PDF", resolution=float(dpi))
    buf.seek(0)
    output_path.write_bytes(buf.read())
