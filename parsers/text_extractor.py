"""
parsers/text_extractor.py
─────────────────────────
Extracts plain text from PDF, DOCX, and plain .txt files.
Used by the Parser Agent before sending text to Mistral.
"""

import pathlib
from loguru import logger


def extract_text(file_path: str) -> str:
    """
    Auto-detects file type and extracts plain text.
    Supports: .pdf, .docx, .txt
    """
    path = pathlib.Path(file_path)
    ext = path.suffix.lower()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext == ".docx":
        return _extract_docx(file_path)
    elif ext == ".txt":
        return _extract_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(file_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    logger.debug(f"PDF extracted | pages={len(reader.pages)} | chars={len(text)}")
    return text.strip()


def _extract_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    logger.debug(f"DOCX extracted | chars={len(text)}")
    return text.strip()


def _extract_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    logger.debug(f"TXT extracted | chars={len(text)}")
    return text.strip()