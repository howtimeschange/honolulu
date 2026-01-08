"""PDF text extraction utility using PyMuPDF."""

import io
from typing import Optional


def extract_pdf_text(file_bytes: bytes, max_pages: Optional[int] = None) -> str:
    """Extract text content from a PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file
        max_pages: Maximum number of pages to extract (None for all)

    Returns:
        Extracted text content from the PDF
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF extraction. "
            "Install it with: pip install pymupdf"
        )

    # Open PDF from bytes
    pdf_stream = io.BytesIO(file_bytes)
    doc = fitz.open(stream=pdf_stream, filetype="pdf")

    text_parts = []
    pages_to_extract = min(len(doc), max_pages) if max_pages else len(doc)

    for page_num in range(pages_to_extract):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

    doc.close()

    if not text_parts:
        return "[PDF contains no extractable text]"

    return "\n\n".join(text_parts)


def get_pdf_info(file_bytes: bytes) -> dict:
    """Get basic information about a PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file

    Returns:
        Dictionary with PDF metadata
    """
    try:
        import fitz
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF processing. "
            "Install it with: pip install pymupdf"
        )

    pdf_stream = io.BytesIO(file_bytes)
    doc = fitz.open(stream=pdf_stream, filetype="pdf")

    info = {
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
    }

    doc.close()
    return info
