"""US05 - text extraction and language detection on several CVs."""

import pytest

from app.schemas.shared import ContentLanguage
from app.services.cv_service import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.services.cv_text import (
    MAX_CV_TEXT_CHARS,
    CVTextError,
    NoTextInCVError,
    clean_text,
    extract_cv_text,
)
from app.services.language_detection import detect_language
from tests.cv_samples import (
    CV_EN,
    CV_ES,
    CV_FR,
    make_docx,
    make_pdf,
    make_protected_pdf,
    make_scanned_pdf,
)

# --- Extraction ----------------------------------------------------------------


def test_pdf_text_keeps_accents_and_lines() -> None:
    text = extract_cv_text(make_pdf(CV_FR), PDF_CONTENT_TYPE)

    assert "Développeuse full-stack junior" in text
    assert "EXPÉRIENCES PROFESSIONNELLES" in text
    assert "Arabe : langue maternelle" in text


def test_multi_page_pdf_is_read_entirely() -> None:
    long_cv = CV_EN + "\n".join(f"Project {i}: data pipeline" for i in range(80))

    text = extract_cv_text(make_pdf(long_cv), PDF_CONTENT_TYPE)

    assert "Youssef Trabelsi" in text
    assert "Project 79: data pipeline" in text


def test_docx_text_includes_header_paragraphs_and_tables() -> None:
    content = make_docx(CV_FR, header="CV - Sarra Ben Ali", as_two_column_table=True)

    text = extract_cv_text(content, DOCX_CONTENT_TYPE)

    assert text.startswith("CV - Sarra Ben Ali")
    assert "Stage de fin d'études (PFE)" in text  # right column
    assert "sarra.benali@example.com" in text  # left column
    assert text.count("Références disponibles sur demande") == 1  # merged cell read once


def test_plain_docx() -> None:
    text = extract_cv_text(make_docx(CV_EN), DOCX_CONTENT_TYPE)

    assert "Data Engineer, Example Analytics" in text


def test_scanned_pdf_has_no_text() -> None:
    with pytest.raises(NoTextInCVError):
        extract_cv_text(make_scanned_pdf(), PDF_CONTENT_TYPE)


def test_password_protected_pdf_is_unreadable() -> None:
    with pytest.raises(CVTextError):
        extract_cv_text(make_protected_pdf(CV_FR), PDF_CONTENT_TYPE)


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"%PDF-1.7 broken", PDF_CONTENT_TYPE),
        (b"PK\x03\x04 not really a docx", DOCX_CONTENT_TYPE),
    ],
)
def test_corrupted_files_are_unreadable(content: bytes, content_type: str) -> None:
    with pytest.raises(CVTextError):
        extract_cv_text(content, content_type)


def test_very_long_text_is_truncated() -> None:
    text = extract_cv_text(make_docx("Python FastAPI React. " * 2_000), DOCX_CONTENT_TYPE)

    assert len(text) == MAX_CV_TEXT_CHARS


def test_clean_text_normalizes_whitespace() -> None:
    raw = "  Nom :  Sarra \t Ben Ali \r\n\r\n\r\n\r\nProﬁl\x0c  "

    assert clean_text(raw) == "Nom : Sarra Ben Ali\n\nProfil"


# --- Language ------------------------------------------------------------------


def test_french_cv_is_detected_as_french() -> None:
    assert detect_language(CV_FR) is ContentLanguage.FR


def test_english_cv_is_detected_as_english() -> None:
    assert detect_language(CV_EN) is ContentLanguage.EN


def test_french_cv_full_of_english_tech_terms_stays_french() -> None:
    text = (
        "Expérience : développeur full-stack chez une startup. Stack : React, Node.js, "
        "Docker, Kubernetes, CI/CD, machine learning. J'ai conçu le back-end et le "
        "front-end de l'application et j'ai encadré deux stagiaires."
    )

    assert detect_language(text) is ContentLanguage.FR


@pytest.mark.parametrize("text", [CV_ES, "", "12345 - 2021 / 2022"])
def test_other_languages_are_not_supported(text: str) -> None:
    assert detect_language(text) is None


def test_detection_is_deterministic() -> None:
    assert {detect_language(CV_FR) for _ in range(5)} == {ContentLanguage.FR}
