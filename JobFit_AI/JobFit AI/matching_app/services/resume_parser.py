"""
Resume parsing service.

Responsible for ONE job: given a file path to a resume (PDF or DOCX),
return the plain text content of that file. No skill extraction, no
NLP, no matching happens here — this module is purely "file -> text".

Two libraries are used for PDFs (pdfplumber and PyMuPDF/fitz) because
in practice some PDFs extract cleanly with one but not the other
(depending on how the PDF was generated). We try pdfplumber first
since it tends to preserve layout/spacing better for resumes, and
fall back to PyMuPDF if pdfplumber returns little or no text.
"""

import os

import pdfplumber
import fitz  # PyMuPDF
import docx  # python-docx

from .text_preprocessing import clean_text


class ResumeParsingError(Exception):
    """Raised when a resume file cannot be read or contains no extractable text."""
    pass


def _extract_text_with_pdfplumber(file_path: str) -> str:
    """Try extracting text from a PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_text_with_pymupdf(file_path: str) -> str:
    """Try extracting text from a PDF using PyMuPDF (fitz) as a fallback."""
    text_parts = []
    with fitz.open(file_path) as pdf_document:
        for page in pdf_document:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file, trying pdfplumber first and falling
    back to PyMuPDF if the first attempt returns little/no text.
    """
    text = ""
    try:
        text = _extract_text_with_pdfplumber(file_path)
    except Exception:
        text = ""

    # If pdfplumber failed or found almost nothing, try PyMuPDF instead.
    if not text or len(text.strip()) < 20:
        try:
            text = _extract_text_with_pymupdf(file_path)
        except Exception:
            pass

    return text


def _extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    document = docx.Document(file_path)
    paragraphs = [para.text for para in document.paragraphs if para.text]

    # Also pull text out of any tables in the document (some resumes
    # use tables for layout, e.g. skills lists or a two-column format).
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    paragraphs.append(cell.text)

    return "\n".join(paragraphs)


def extract_text_from_resume(file_path: str) -> str:
    """
    Extract plain text from a resume file (PDF or DOCX).

    Args:
        file_path: absolute path to the resume file on disk
                    (e.g. resume.uploaded_resume.path).

    Returns:
        The cleaned plain text content of the resume.

    Raises:
        ResumeParsingError: if the file type is unsupported, the file
                             can't be opened, or no text could be
                             extracted from it (e.g. a scanned image
                             PDF with no selectable text).
    """
    if not os.path.exists(file_path):
        raise ResumeParsingError(f"File not found: {file_path}")

    file_extension = os.path.splitext(file_path)[1].lower()

    try:
        if file_extension == ".pdf":
            raw_text = _extract_text_from_pdf(file_path)
        elif file_extension == ".docx":
            raw_text = _extract_text_from_docx(file_path)
        else:
            raise ResumeParsingError(
                f"Unsupported file type '{file_extension}'. Only PDF and DOCX are supported."
            )
    except ResumeParsingError:
        raise
    except Exception as exc:
        raise ResumeParsingError(f"Failed to read the resume file: {exc}") from exc

    cleaned_text = clean_text(raw_text)

    if not cleaned_text or len(cleaned_text) < 20:
        raise ResumeParsingError(
            "No readable text could be found in this file. It may be a "
            "scanned image, password-protected, or empty."
        )

    return cleaned_text