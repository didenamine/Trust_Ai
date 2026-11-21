"""US24 - ATS analysis of the imported CV (Sprint 1)."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.ats_analysis_service import ATS_ANALYSIS_SCHEMA, SYSTEM_PROMPT
from app.services.llm import (
    LLMRateLimitError,
    LLMResponseError,
    get_llm_client,
)
from app.services.llm.fake import FakeLLMClient
from app.services.storage import LocalFileStorage, get_storage
from tests.cv_samples import CV_EN, CV_ES, CV_FR, make_docx, make_pdf, make_scanned_pdf

ANSWER_FR = {
    "sections": [
        {"section": "summary", "line": 6, "confidence": 0.9},
        {"section": "experience", "line": 9, "confidence": 0.95},
        {"section": "education", "line": 16, "confidence": 0.95},
        {"section": "skills", "line": 20, "confidence": 0.95},
        {"section": "languages", "line": 24, "confidence": 0.9},
    ],
    "keywords": [
        {
            "canonical": "Python",
            "kind": "hard_skill",
            "line": 21,
            "section": "skills",
            "alias_count": 0,
        },
        {"canonical": "React", "kind": "tool", "line": 21, "section": "skills", "alias_count": 0},
        {"canonical": "FastAPI", "kind": "tool", "line": 21, "section": "skills", "alias_count": 0},
        {
            "canonical": "PostgreSQL",
            "kind": "tool",
            "line": 21,
            "section": "skills",
            "alias_count": 0,
        },
        {"canonical": "Scrum", "kind": "method", "line": 21, "section": "skills", "alias_count": 0},
        {
            "canonical": "Développer",
            "kind": "action_verb",
            "line": 11,
            "section": "experience",
            "alias_count": 0,
        },
        {
            "canonical": "solution",
            "kind": "generic",
            "line": 11,
            "section": "experience",
            "alias_count": 0,
        },
    ],
}

ANSWER_EN = {
    "sections": [
        {"section": "summary", "line": 5, "confidence": 0.9},
        {"section": "experience", "line": 8, "confidence": 0.95},
        {"section": "education", "line": 14, "confidence": 0.95},
        {"section": "skills", "line": 17, "confidence": 0.95},
        {"section": "languages", "line": 20, "confidence": 0.9},
    ],
    "keywords": [
        {
            "canonical": "Python",
            "kind": "hard_skill",
            "line": 18,
            "section": "skills",
            "alias_count": 0,
        },
        {
            "canonical": "SQL",
            "kind": "hard_skill",
            "line": 18,
            "section": "skills",
            "alias_count": 0,
        },
        {
            "canonical": "Apache Spark",
            "kind": "tool",
            "line": 18,
            "section": "skills",
            "alias_count": 0,
        },
        {"canonical": "Airflow", "kind": "tool", "line": 18, "section": "skills", "alias_count": 0},
        {
            "canonical": "built",
            "kind": "action_verb",
            "line": 12,
            "section": "experience",
            "alias_count": 0,
        },
    ],
}

# No summary / languages / certifications: those sections must be N/A and excluded.
CV_MINIMAL_EN = """\
Alex Morgan
alex.morgan@example.com - Paris, France

EXPERIENCE
Software Engineer, Example Corp (2021 - present)
Built web services with Python and PostgreSQL.
Analysed logs and improved the release process.

EDUCATION
BSc Computer Science, Example University (2018 - 2021)

SKILLS
Python, PostgreSQL, Docker, Git, REST APIs
"""


@pytest.fixture
def llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def client(tmp_path: Path, llm: FakeLLMClient) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = lambda: LocalFileStorage(tmp_path / "uploads")
    app.dependency_overrides[get_llm_client] = lambda: llm
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    credentials = {"email": "ats-candidat@example.com", "password": "S3cret!23"}  # ggignore
    client.post("/api/auth/register", json=credentials)
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client: TestClient, headers: dict[str, str], filename: str, content: bytes) -> dict:
    response = client.post("/api/cv", headers=headers, files={"file": (filename, content)})
    assert response.status_code == 201, response.text
    return response.json()


def analyze(client: TestClient, headers: dict[str, str]):
    return client.post("/api/ats/me/analyze", headers=headers)


def test_full_ats_analysis_is_saved_and_returned(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    cv = upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)

    response = analyze(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cv_document_id"] == cv["id"]
    assert body["scoring_version"] == 1
    assert 0 <= body["score"]["total"] <= 100
    # Certifications are absent from the sample and must not be penalised.
    assert body["score"]["denominator"] == 98
    assert "certifications" in body["score"]["na_sections"]
    assert {item["key"] for item in body["score"]["dimensions"]} == {
        "readability",
        "sections",
        "keywords",
    }
    result = body["result"]
    assert result["language"] == "fr"
    assert {item["section"] for item in result["sections"]} >= {
        "contact",
        "experience",
        "education",
        "skills",
    }
    assert result["keywords"]["verified_count"] >= 5
    assert result["keywords"]["action_verb_count"] >= 1

    # The GET endpoint returns the same result for the current CV version.
    assert client.get("/api/ats/me", headers=headers).json() == body

    # One LLM call with the shared strict schema and no raw snippets requested.
    assert len(llm.calls) == 1
    assert llm.calls[0]["system"] == SYSTEM_PROMPT
    assert llm.calls[0]["schema"] is ATS_ANALYSIS_SCHEMA
    assert "L1:" in llm.calls[0]["user"]


def test_stored_result_contains_no_cv_text(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)

    body = analyze(client, headers).json()
    serialised = json.dumps(body, ensure_ascii=False).lower()

    for forbidden in ("sarra", "ben ali", "example.com", "développement", "startup exemple"):
        assert forbidden not in serialised
    for forbidden_key in ("snippet", "quote", "cv_text", "raw_heading"):
        assert forbidden_key not in serialised


def test_optional_sections_are_na_and_excluded_from_denominator(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "minimal.docx", make_docx(CV_MINIMAL_EN))
    llm._answers.append(
        {
            "sections": [
                {"section": "experience", "line": 4, "confidence": 0.9},
                {"section": "education", "line": 9, "confidence": 0.9},
                {"section": "skills", "line": 13, "confidence": 0.9},
            ],
            "keywords": [
                {
                    "canonical": "Python",
                    "kind": "hard_skill",
                    "line": 14,
                    "section": "skills",
                    "alias_count": 0,
                },
                {
                    "canonical": "PostgreSQL",
                    "kind": "tool",
                    "line": 14,
                    "section": "skills",
                    "alias_count": 0,
                },
                {
                    "canonical": "Docker",
                    "kind": "tool",
                    "line": 14,
                    "section": "skills",
                    "alias_count": 0,
                },
                {
                    "canonical": "Built",
                    "kind": "action_verb",
                    "line": 6,
                    "section": "experience",
                    "alias_count": 0,
                },
            ],
        }
    )

    response = analyze(client, headers)

    assert response.status_code == 200, response.text
    score = response.json()["score"]
    assert set(score["na_sections"]) == {"summary", "languages", "certifications"}
    assert score["denominator"] == 93  # 100 - 3 (summary) - 2 (languages) - 2 (certifications)
    assert all(item["applicable"] is False for item in score["criteria"] if item["status"] == "na")


def test_each_uploaded_cv_has_its_own_latest_result(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)
    first = analyze(client, headers)
    assert first.status_code == 200, first.text

    upload(client, headers, "cv-en.pdf", make_pdf(CV_EN))
    # The previous result must not be presented for a different uploaded file.
    assert client.get("/api/ats/me", headers=headers).status_code == 404

    llm._answers.append(ANSWER_EN)
    second = analyze(client, headers)
    assert second.status_code == 200, second.text
    assert second.json()["cv_uploaded_at"] != first.json()["cv_uploaded_at"]
    assert client.get("/api/ats/me", headers=headers).json() == second.json()


def test_layout_warnings_do_not_deduct_points(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "two-columns.docx", make_docx(CV_EN, as_two_column_table=True))
    llm._answers.append(ANSWER_EN)

    response = analyze(client, headers)

    assert response.status_code == 200, response.text
    findings = {item["code"]: item for item in response.json()["result"]["readability"]}
    assert findings["docx.body_only_tables"]["deduction"] == 0
    assert findings["docx.body_only_tables"]["degraded_extraction"] is False


def test_scanned_pdf_returns_clear_422(client: TestClient, headers: dict[str, str]) -> None:
    upload(client, headers, "scan.pdf", make_scanned_pdf())

    response = analyze(client, headers)

    assert response.status_code == 422
    assert "scann" in response.json()["detail"].lower()


def test_unsupported_language_returns_422(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv-es.pdf", make_pdf(CV_ES))
    llm._answers.append(ANSWER_EN)

    assert analyze(client, headers).status_code == 422


def test_analysis_without_cv_returns_404(client: TestClient, headers: dict[str, str]) -> None:
    assert analyze(client, headers).status_code == 404
    assert client.get("/api/ats/me", headers=headers).status_code == 404


def test_invalid_llm_answer_returns_502(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(LLMResponseError("bad answer"))

    assert analyze(client, headers).status_code == 502


def test_rate_limit_is_forwarded_with_retry_after(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(LLMRateLimitError("slow down", retry_after=12))

    response = analyze(client, headers)

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "12"


def test_analysis_is_isolated_per_candidate(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)
    assert analyze(client, headers).status_code == 200

    other = {"email": "autre@example.com", "password": "S3cret!23"}  # ggignore
    client.post("/api/auth/register", json=other)
    token = client.post("/api/auth/login", json=other).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/ats/me", headers=other_headers).status_code == 404
