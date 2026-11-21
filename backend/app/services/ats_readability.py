"""US24 - document-level ATS readability diagnostics.

Existing libraries (PyMuPDF / python-docx) are enough: no new dependency and no OCR.
Layout features (columns, tables, headers, images) are reported as warnings. A score
deduction is only attached when there is evidence that text is missing or read in the
wrong order.
"""

import io
import re

import docx
import pymupdf
from docx.oxml.ns import qn

from app.schemas.ats import ATSReadabilityFinding, ATSReadingLocation, ATSSeverity
from app.services.cv_text import MAX_CV_TEXT_CHARS, CVTextError

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _finding(
    code: str,
    *,
    severity: ATSSeverity = ATSSeverity.WARNING,
    location: ATSReadingLocation = ATSReadingLocation.UNKNOWN,
    page: int | None = None,
    degraded_extraction: bool = False,
    deduction: float = 0.0,
) -> ATSReadabilityFinding:
    return ATSReadabilityFinding(
        code=code,
        severity=severity,
        location=location,
        page=page,
        line=None,
        degraded_extraction=degraded_extraction,
        deduction=deduction,
    )


def analyze_pdf_readability(content: bytes) -> list[ATSReadabilityFinding]:
    findings: list[ATSReadabilityFinding] = []
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:  # pragma: no cover - extract_cv_text rejects these first
        raise CVTextError("The PDF can't be read") from exc

    with document:
        if document.needs_pass:  # pragma: no cover - handled before this stage
            raise CVTextError("The PDF is password-protected")

        multi_column_pages = 0
        header_only_contact = False
        contact_in_body = False
        image_only_pages = 0

        for _page_number, page in enumerate(document, start=1):
            blocks = [
                block
                for block in page.get_text("blocks")
                if len(block) > 6 and block[6] == 0 and str(block[4]).strip()
            ]
            text_chars = sum(len(str(block[4])) for block in blocks)
            images = page.get_images(full=True)

            if text_chars == 0 and images:
                image_only_pages += 1

            centers = [((block[0] + block[2]) / 2, block[1], block[3]) for block in blocks]
            if len(centers) >= 4:
                width = page.rect.width or 1
                left = sum(1 for center, _, _ in centers if center < width * 0.45)
                right = sum(1 for center, _, _ in centers if center > width * 0.55)
                if left >= 2 and right >= 2:
                    multi_column_pages += 1

            height = page.rect.height or 1
            for _x0, y0, _x1, y1, text, *_ in blocks:
                if not _EMAIL_RE.search(str(text)):
                    continue
                if y0 < height * 0.12 or y1 > height * 0.88:
                    header_only_contact = True
                else:
                    contact_in_body = True

        if image_only_pages:
            findings.append(
                _finding(
                    "pdf.image_only_page",
                    location=ATSReadingLocation.IMAGE,
                    degraded_extraction=True,
                    deduction=min(4 * image_only_pages, 8),
                )
            )
        if multi_column_pages:
            findings.append(_finding("pdf.multi_column", location=ATSReadingLocation.BODY))
        if header_only_contact and not contact_in_body:
            findings.append(
                _finding("common.contact_in_header_only", location=ATSReadingLocation.HEADER)
            )

    return findings


def analyze_docx_readability(content: bytes) -> list[ATSReadabilityFinding]:
    findings: list[ATSReadabilityFinding] = []
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as exc:  # pragma: no cover - extract_cv_text rejects these first
        raise CVTextError("The DOCX can't be read") from exc

    body = document.element.body
    textboxes = body.findall(f".//{qn('w:txbxContent')}")
    tables = document.tables
    paragraphs = document.paragraphs
    images = document.inline_shapes

    if textboxes:
        # python-docx's body iteration (used by US05/US24) does not read text boxes:
        # this is real missing content, not just a visual preference.
        findings.append(
            _finding(
                "docx.textbox_content_not_extracted",
                location=ATSReadingLocation.TEXTBOX,
                degraded_extraction=True,
                deduction=min(6 * len(textboxes), 12),
            )
        )
    if tables and not paragraphs:
        findings.append(_finding("docx.body_only_tables", location=ATSReadingLocation.TABLE))
    if images:
        findings.append(_finding("docx.images_detected", location=ATSReadingLocation.IMAGE))

    multi_column = False
    for section in document.sections:
        sect_pr = section._sectPr
        cols = sect_pr.find(qn("w:cols")) if sect_pr is not None else None
        if cols is not None and int(cols.get(qn("w:num"), "1") or "1") > 1:
            multi_column = True
    if multi_column:
        findings.append(_finding("docx.multi_column_section", location=ATSReadingLocation.BODY))

    body_text = "\n".join([paragraph.text for paragraph in paragraphs])
    body_text += "\n" + "\n".join(
        cell.text for table in tables for row in table.rows for cell in row.cells
    )
    header_text = "\n".join(
        paragraph.text for section in document.sections for paragraph in section.header.paragraphs
    )
    if _EMAIL_RE.search(header_text) and not _EMAIL_RE.search(body_text):
        findings.append(
            _finding("common.contact_in_header_only", location=ATSReadingLocation.HEADER)
        )

    return findings


def analyze_readability(
    content: bytes, content_type: str, extracted_text: str
) -> list[ATSReadabilityFinding]:
    findings: list[ATSReadabilityFinding]
    if content_type == "application/pdf":
        findings = analyze_pdf_readability(content)
    else:
        findings = analyze_docx_readability(content)

    if len(extracted_text) >= MAX_CV_TEXT_CHARS:
        findings.append(_finding("common.text_truncated", severity=ATSSeverity.INFO))
    return findings
