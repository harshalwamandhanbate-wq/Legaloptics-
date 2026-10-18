"""PDF text extraction for LegalLens, with friendly errors."""
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentError(Exception):
    """The PDF could not be read. The message is safe to show to the user."""


def _clean(text: str) -> str:
    """Tidy up extracted text while keeping line breaks (the chunker splits on them)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t\u00a0]+", " ", text)           # collapse spaces and tabs
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)         # join words hyphenated at line end
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_pages(source) -> list[dict]:
    """Read a PDF (path or file-like object) into [{"page": 1, "text": "..."}, ...].

    Raises DocumentError for corrupted, password-protected or scanned PDFs.
    """
    try:
        reader = PdfReader(source)
    except (PdfReadError, ValueError, OSError, EOFError, TypeError) as e:
        raise DocumentError("This file could not be read. Make sure it is a valid PDF.") from e
    except Exception as e:  # pypdf can raise many different errors on broken files
        raise DocumentError("This file could not be read. Make sure it is a valid PDF.") from e

    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")  # many PDFs are "protected" with an empty password
        except Exception as e:
            raise DocumentError("This PDF is password-protected. Remove the password and try again.") from e
        if not ok:
            raise DocumentError("This PDF is password-protected. Remove the password and try again.")

    pages = []
    try:
        for number, page in enumerate(reader.pages, start=1):
            try:
                raw = page.extract_text() or ""
            except Exception:
                raw = ""  # one bad page should not kill the whole document
            pages.append({"page": number, "text": _clean(raw)})
    except Exception as e:
        raise DocumentError("This PDF appears to be damaged and could not be read.") from e

    if not pages:
        raise DocumentError("This PDF has no pages.")
    if not any(p["text"] for p in pages):
        raise DocumentError(
            "No extractable text found. The PDF may be scanned. Run OCR on it first, "
            "for example: ocrmypdf in.pdf out.pdf"
        )
    return pages
