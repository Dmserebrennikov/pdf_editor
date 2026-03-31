"""PDF splitting logic."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from editor.constants import PDF_EXTENSION


def split_pdf_to_individual_pages(
    input_pdf_path: Path,
    output_dir: Path,
    filename_prefix: str | None = None,
) -> list[Path]:
    """
    Split a PDF into one PDF file per page.
    Returns the list of created file paths.
    """
    input_pdf_path = Path(input_pdf_path)
    output_dir = Path(output_dir)

    if not input_pdf_path.exists():
        raise FileNotFoundError(f"File not found: {input_pdf_path}")
    if input_pdf_path.suffix.lower() != PDF_EXTENSION:
        raise ValueError("Input file must be a PDF.")

    reader = PdfReader(str(input_pdf_path))
    page_count = len(reader.pages)
    if page_count == 0:
        raise ValueError("Input PDF has no pages.")

    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = (filename_prefix or "").strip() or input_pdf_path.stem
    created_files: list[Path] = []

    for page_number, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        output_path = output_dir / f"{prefix}_page_{page_number:03d}.pdf"
        with open(output_path, "wb") as f:
            writer.write(f)
        created_files.append(output_path)

    return created_files
