"""
parsers/pdf_parser.py
──────────────────────
PDF and DOCX text extraction with NLP preprocessing.
"""

import io
import re
from loguru import logger


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        logger.debug(f"PDF extracted | pages={len(reader.pages)} | chars={len(text)}")
        return clean_text(text)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        import docx
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
        logger.debug(f"DOCX extracted | chars={len(text)}")
        return clean_text(text)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


def extract_from_upload(filename: str, file_bytes: bytes) -> str:
    """Auto-detect file type and extract text."""
    filename_lower = filename.lower()
    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif filename_lower.endswith(".txt"):
        return clean_text(file_bytes.decode("utf-8", errors="ignore"))
    else:
        raise ValueError(f"Unsupported file type: {filename}")