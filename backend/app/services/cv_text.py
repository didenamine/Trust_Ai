"""Text extraction from an imported CV (US05).

Reusable by US24 (ATS analysis), which also needs the CV's text.
"""

import io
import re
import unicodedata
import zipfile

import docx
import pymupdf
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.cv_service import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE

# A long CV is ~6,000 characters; beyond this it is noise and wasted LLM tokens.
MAX_CV_TEXT_CHARS = 20_000
# Below this, the file has no real text layer (scanned PDF, image-only DOCX...).
MIN_CV_TEXT_CHARS = 100


class CVTextError(Exception):
    """The file can't be read (corrupted, password-protected...)."""


class NoTextInCVError(CVTextError):
    """The file opens but contains (almost) no text, e.g. a scanned PDF."""


def extract_cv_text(content: bytes, content_type: str) -> str:
    if content_type == PDF_CONTENT_TYPE:
        raw = _pdf_text(content)
    elif content_type == DOCX_CONTENT_TYPE:
        raw = _docx_text(content)
    else:
        raise CVTextError(f"Unsupported content type: {content_type}")

    text = clean_text(raw)
    if len(text) < MIN_CV_TEXT_CHARS:
        raise NoTextInCVError("No text layer in the CV")
    return text[:MAX_CV_TEXT_CHARS]


def _pdf_text(content: bytes) -> str:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise CVTextError("The PDF is password-protected")
            # sort=True reads blocks top-to-bottom, left-to-right: better for 2-column CVs.
            return "\n\n".join(page.get_text("text", sort=True) for page in document)
    except CVTextError:
        raise
    except Exception as exc:  # PyMuPDF raises several exception types for broken files
        raise CVTextError("The PDF can't be read") from exc


def _docx_text(content: bytes) -> str:
    try:
        document: DocxDocument = docx.Document(io.BytesIO(content))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise CVTextError("The DOCX can't be read") from exc

    parts: list[str] = []
    # Contact details are often in the page header.
    for section in document.sections:
        parts.extend(_block_texts(section.header))
    # Body paragraphs and tables in reading order (many CV templates are tables).
    parts.extend(_block_texts(document))
    return "\n".join(parts)


def _block_texts(container) -> list[str]:
    texts: list[str] = []
    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            texts.append(block.text)
        elif isinstance(block, Table):
            texts.extend(_table_texts(block))
    return texts


def _table_texts(table: Table) -> list[str]:
    texts: list[str] = []
    for row in table.rows:
        seen_cells: set[int] = set()
        for cell in row.cells:
            # Merged cells are returned once per grid column: keep each only once.
            if id(cell._tc) in seen_cells:
                continue
            seen_cells.add(id(cell._tc))
            texts.extend(_block_texts(cell))
    return texts


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES_RE = re.compile(r"[ \t  -​ 　]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise Unicode and whitespace, keep line structure (it helps the LLM)."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")  # ligatures from some PDFs
    lines = [_SPACES_RE.sub(" ", line).strip() for line in text.split("\n")]
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()
