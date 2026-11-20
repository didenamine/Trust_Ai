"""Business logic for US03 (import du CV).

Also the entry point for features that need the candidate's CV file:
US05 (analyse du CV) and US24 (analyse ATS) should call `read_current_cv`.
"""

import io
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import PurePath

from sqlalchemy.orm import Session

from app.models.cv_document import CVDocument
from app.services.storage import FileStorage

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

ALLOWED_EXTENSIONS = {".pdf": PDF_CONTENT_TYPE, ".docx": DOCX_CONTENT_TYPE}


class UnsupportedCVFormatError(Exception):
    """The file is not a PDF or DOCX (by extension or by content)."""


class CVTooLargeError(Exception):
    """The file is larger than the configured maximum size."""


class EmptyCVError(Exception):
    """The file has no content."""


def _looks_like_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-")


def _looks_like_docx(content: bytes) -> bool:
    # A DOCX is a zip archive that contains word/document.xml. Checking that entry
    # also rejects other zip-based files renamed to .docx (.xlsx, .pptx, .zip...).
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def validate_cv(filename: str, content: bytes, *, max_bytes: int) -> str:
    """Check the file's format and size and return its content type.

    The extension alone can be faked, so the content is checked too.
    """
    if not content:
        raise EmptyCVError(filename)
    if len(content) > max_bytes:
        raise CVTooLargeError(filename)

    extension = PurePath(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedCVFormatError(filename)

    content_matches = _looks_like_pdf(content) if extension == ".pdf" else _looks_like_docx(content)
    if not content_matches:
        raise UnsupportedCVFormatError(filename)

    return ALLOWED_EXTENSIONS[extension]


def _clean_filename(filename: str) -> str:
    # Keep only the base name (some browsers send a full path) and fit the column.
    name = PurePath(filename.replace("\\", "/")).name.strip() or "cv"
    if len(name) <= 255:
        return name
    suffix = PurePath(name).suffix
    return name[: 255 - len(suffix)] + suffix


def get_current_cv(db: Session, user_id: uuid.UUID) -> CVDocument | None:
    return db.query(CVDocument).filter(CVDocument.user_id == user_id).first()


def save_cv(
    db: Session,
    storage: FileStorage,
    *,
    user_id: uuid.UUID,
    filename: str,
    content: bytes,
    max_bytes: int,
) -> CVDocument:
    """Validate and store a CV, replacing the candidate's previous one if any."""
    content_type = validate_cv(filename, content, max_bytes=max_bytes)

    # The stored name never comes from the user: no clashes, no path tricks.
    extension = PurePath(filename).suffix.lower()
    storage_key = f"{user_id}/{uuid.uuid4().hex}{extension}"
    storage.save(storage_key, content)

    cv = get_current_cv(db, user_id)
    previous_key = cv.storage_key if cv else None
    if cv is None:
        cv = CVDocument(user_id=user_id)
        db.add(cv)

    cv.original_filename = _clean_filename(filename)
    cv.storage_key = storage_key
    cv.content_type = content_type
    cv.size_bytes = len(content)
    cv.uploaded_at = datetime.now(UTC)

    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise

    # Only remove the old file once the new one is safely recorded.
    if previous_key:
        storage.delete(previous_key)

    db.refresh(cv)
    return cv


def read_current_cv(
    db: Session, storage: FileStorage, user_id: uuid.UUID
) -> tuple[CVDocument, bytes] | None:
    """Return the candidate's current CV and its bytes, or None if they have none.

    For US05 / US24: PyMuPDF opens the bytes with `fitz.open(stream=content, filetype="pdf")`
    and python-docx with `Document(io.BytesIO(content))`.
    """
    cv = get_current_cv(db, user_id)
    if cv is None:
        return None
    return cv, storage.read(cv.storage_key)


def delete_cv(db: Session, storage: FileStorage, user_id: uuid.UUID) -> bool:
    """Delete the candidate's CV (record and file). Returns False if there was none.

    Account deletion (US02) should call this so the file is removed from storage too.
    """
    cv = get_current_cv(db, user_id)
    if cv is None:
        return False
    storage_key = cv.storage_key
    db.delete(cv)
    db.commit()
    storage.delete(storage_key)
    return True
