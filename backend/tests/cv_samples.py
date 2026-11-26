"""Sample CVs generated in memory for the US05 tests (fictional people)."""

import io
import json
from pathlib import Path

import docx
import pymupdf

FIXTURES = Path(__file__).parent / "fixtures"

CV_FR = """\
Sarra Ben Ali
Développeuse full-stack junior
sarra.benali@example.com | +216 20 000 000 | Tunis, Tunisie
github.com/sarra-ben-ali

PROFIL
Jeune diplômée en génie logiciel, passionnée par le développement web et les API REST.

EXPÉRIENCES PROFESSIONNELLES
Développeuse web - Startup Exemple, Ariana (septembre 2025 - aujourd'hui)
Développement de nouvelles fonctionnalités sur une application React et TypeScript.

Stage de fin d'études (PFE) - Société Exemple SARL, Tunis (février 2025 - juillet 2025)
Conception d'une plateforme de suivi des réclamations : API REST avec FastAPI et PostgreSQL.

FORMATION
Licence en génie logiciel et systèmes d'information - Institut Supérieur Exemple (2022 - 2025)
Baccalauréat sciences de l'informatique - Lycée Exemple (2022)

COMPÉTENCES
Python, FastAPI, React, TypeScript, PostgreSQL, Docker, Git, Scrum
Travail en équipe, communication

LANGUES
Arabe : langue maternelle - Français : courant - Anglais : intermédiaire
"""

CV_EN = """\
Youssef Trabelsi
Data Engineer
youssef.trabelsi@example.com - Sousse, Tunisia

SUMMARY
Data engineer with more than three years of experience building batch and streaming
data pipelines on the cloud for retail and analytics companies.

EXPERIENCE
Data Engineer, Example Analytics (January 2023 - present)
Own the ingestion platform for more than forty data sources. Moved the nightly jobs to
Apache Spark and cut the batch time from six hours to forty-five minutes.

BI Developer, Example Retail (June 2021 - December 2022)
Built the sales dashboards with SQL and Power BI.

EDUCATION
Engineering degree in Computer Science, Example School of Engineering (2018 - 2021)

SKILLS
Python, SQL, Apache Spark, Airflow, AWS, Kafka, mentoring, problem solving

LANGUAGES
Arabic (native), English (fluent), French (B2)
"""

CV_ES = """\
María García López
Desarrolladora de software con cinco años de experiencia en el desarrollo de aplicaciones
web y móviles para empresas del sector bancario y de seguros en Madrid y Barcelona.
Experiencia profesional: desarrolladora sénior en una empresa de consultoría, donde
diseñé y mantuve servicios de pagos utilizados por millones de clientes cada día.
Formación: grado en ingeniería informática por la universidad de Madrid.
Idiomas: español nativo, inglés avanzado.
"""


def make_pdf(text: str) -> bytes:
    """A real text PDF, wrapped on A4 pages."""
    document = pymupdf.open()
    lines = text.splitlines()
    while lines:
        page = document.new_page()
        chunk, lines = lines[:45], lines[45:]
        page.insert_textbox(pymupdf.Rect(50, 50, 545, 800), "\n".join(chunk), fontsize=10)
    return document.tobytes()


def make_scanned_pdf() -> bytes:
    """A PDF with no text layer, like a scanned CV (just a drawn shape)."""
    document = pymupdf.open()
    page = document.new_page()
    page.draw_rect(pymupdf.Rect(50, 50, 300, 300), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
    return document.tobytes()


def make_protected_pdf(text: str) -> bytes:
    document = pymupdf.open(stream=make_pdf(text), filetype="pdf")
    return document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret"
    )


def make_docx(text: str, *, header: str | None = None, as_two_column_table: bool = False) -> bytes:
    """A DOCX CV. `as_two_column_table` mimics the common template where the left column
    (contact, skills) and the right column (experience) are cells of one table."""
    document = docx.Document()
    if header:
        document.sections[0].header.paragraphs[0].text = header

    paragraphs = text.split("\n\n")
    if as_two_column_table:
        table = document.add_table(rows=1, cols=2)
        left, right = table.rows[0].cells
        half = len(paragraphs) // 2
        left.text = "\n\n".join(paragraphs[:half])
        right.text = "\n\n".join(paragraphs[half:])
        # A merged title row spanning both columns.
        title_row = table.add_row().cells
        title_row[0].merge(title_row[1]).text = "Références disponibles sur demande"
    else:
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def llm_answer_from_fixture(name: str) -> dict:
    """What a strict-schema LLM answer looks like for one of the example profiles:
    no ids, no schema_version, no language (the application sets those)."""
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    for key in ("schema_version", "language"):
        data.pop(key)
    for section in ("experiences", "education", "certifications", "projects"):
        for item in data[section]:
            item.pop("id")
    return data
