from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> tuple[str, list[str]]:
    reader = PdfReader(file_path)

    pages = []
    urls = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

        # Extract clickable hyperlinks from the PDF
        try:
            links = page.get("/Annots", [])

            for link in links:
                annotation = link.get_object()
                action = annotation.get("/A")

                if action:
                    uri = action.get("/URI")

                    if uri:
                        urls.append(str(uri))
        except Exception:
            pass

    return "\n".join(pages).strip(), list(dict.fromkeys(urls))


def extract_text_from_docx(file_path: str) -> tuple[str, list[str]]:
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs).strip(), []


def extract_resume_text(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower().strip()

    if extension == ".pdf":
        text, _ = extract_text_from_pdf(str(path))
        return text

    elif extension == ".docx":
        text, _ = extract_text_from_docx(str(path))
        return text

    raise ValueError(f"Unsupported file type: {extension}")

def extract_resume_content(file_path: str) -> dict:
    path = Path(file_path)
    extension = path.suffix.lower().strip()

    if extension == ".pdf":
        text, urls = extract_text_from_pdf(str(path))

    elif extension == ".docx":
        text, urls = extract_text_from_docx(str(path))

    else:
        raise ValueError(f"Unsupported file type: {extension}")

    return {
        "text": text,
        "urls": urls,
    }