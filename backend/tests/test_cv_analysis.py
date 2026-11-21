"""US05 - Analyse automatique du CV: from the imported file to the saved profile."""

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
from app.schemas.shared import ContentLanguage
from app.services.cv_analysis_service import (
    PROFILE_EXTRACTION_SCHEMA,
    SYSTEM_PROMPT,
    parse_llm_profile,
)
from app.services.llm import (
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)
from app.services.llm.fake import FakeLLMClient
from app.services.storage import LocalFileStorage, get_storage
from tests.cv_samples import (
    CV_EN,
    CV_ES,
    CV_FR,
    llm_answer_from_fixture,
    make_docx,
    make_pdf,
    make_scanned_pdf,
)

ANSWER_FR = llm_answer_from_fixture("profile_fr.json")
ANSWER_EN = llm_answer_from_fixture("profile_en.json")


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
    credentials = {"email": "candidat@example.com", "password": "S3cret!23"}  # ggignore
    client.post("/api/auth/register", json=credentials)
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client: TestClient, headers: dict[str, str], filename: str, content: bytes) -> dict:
    response = client.post("/api/cv", headers=headers, files={"file": (filename, content)})
    assert response.status_code == 201, response.text
    return response.json()


def analyze(client: TestClient, headers: dict[str, str]):
    return client.post("/api/cv/me/analyze", headers=headers)


# --- Full pipeline on several CVs ----------------------------------------------


def test_french_pdf_cv_becomes_the_candidate_profile(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    cv = upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)

    response = analyze(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "cv_analysis"
    assert body["cv_document_id"] == cv["id"]
    profile = body["profile"]
    assert profile["language"] == "fr"
    assert profile["personal_info"]["headline"] == "Développeuse full-stack junior"
    assert all(item["id"] for item in profile["experiences"])  # ids added by the app

    # Saved: the profile endpoint returns the same thing.
    assert client.get("/api/profile/me", headers=headers).json() == body

    # What the LLM received: the rules, the CV text, the language, the strict schema.
    call = llm.calls[0]
    assert call["system"] == SYSTEM_PROMPT
    assert "The CV is written in French" in call["user"]
    assert "<cv>\nSarra Ben Ali" in call["user"]
    assert "EXPÉRIENCES PROFESSIONNELLES" in call["user"]
    assert call["schema"] is PROFILE_EXTRACTION_SCHEMA


def test_english_docx_cv(client: TestClient, headers: dict[str, str], llm: FakeLLMClient) -> None:
    upload(client, headers, "resume.docx", make_docx(CV_EN, as_two_column_table=True))
    llm._answers.append(ANSWER_EN)

    response = analyze(client, headers)

    assert response.status_code == 200, response.text
    assert response.json()["profile"]["language"] == "en"
    assert "The CV is written in English" in llm.calls[0]["user"]


def test_language_comes_from_detection_not_from_the_llm(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append({**ANSWER_FR, "language": "en", "schema_version": 7})

    profile = analyze(client, headers).json()["profile"]

    assert profile["language"] == "fr"
    assert profile["schema_version"] == 1


def test_new_analysis_replaces_a_manual_profile(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    client.put("/api/profile/me", headers=headers, json={"language": "en", "summary": "Old"})
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(ANSWER_FR)

    body = analyze(client, headers).json()

    assert body["source"] == "cv_analysis"
    assert body["profile"]["summary"] != "Old"


# --- Errors ----------------------------------------------------------------------


def test_analysis_without_cv(client: TestClient, headers: dict[str, str]) -> None:
    assert analyze(client, headers).status_code == 404


def test_analysis_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/cv/me/analyze").status_code == 401


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("scan.pdf", make_scanned_pdf(), "Aucun texte"),
        ("cv.pdf", make_pdf(CV_ES), "français ou en anglais"),
    ],
)
def test_cv_that_cannot_be_analysed(
    client: TestClient,
    headers: dict[str, str],
    llm: FakeLLMClient,
    filename: str,
    content: bytes,
    message: str,
) -> None:
    upload(client, headers, filename, content)

    response = analyze(client, headers)

    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert llm.calls == []  # no LLM call wasted


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (LLMNotConfiguredError("no key"), 503),
        (LLMUnavailableError("down"), 503),
        (LLMResponseError("bad json"), 502),
    ],
)
def test_llm_failures(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, error: Exception, status: int
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(error)

    assert analyze(client, headers).status_code == status


def test_rate_limit_tells_when_to_retry(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(LLMRateLimitError("slow down", retry_after=42.4))

    response = analyze(client, headers)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"


def test_failed_analysis_keeps_the_existing_profile(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    client.put("/api/profile/me", headers=headers, json={"language": "fr", "summary": "Mon profil"})
    upload(client, headers, "cv.pdf", make_pdf(CV_FR))
    llm._answers.append(LLMUnavailableError("down"))

    analyze(client, headers)

    assert client.get("/api/profile/me", headers=headers).json()["profile"]["summary"] == (
        "Mon profil"
    )


# --- Repairing what the LLM gets wrong -----------------------------------------


def parse(**changes) -> dict:
    answer = json.loads(json.dumps(ANSWER_FR))
    for path, value in changes.items():
        *parents, key = path.split("__")
        node = answer
        for part in parents:
            node = node[int(part)] if part.isdigit() else node[part]
        node[int(key) if key.isdigit() else key] = value
    return parse_llm_profile(answer, ContentLanguage.FR).model_dump(mode="json")


def test_valid_answer_is_kept_as_is() -> None:
    profile = parse()

    assert len(profile["experiences"]) == 2
    assert len(profile["skills"]) == 10


def test_invalid_optional_value_becomes_null() -> None:
    profile = parse(personal_info__email="sarra at example dot com")

    assert profile["personal_info"]["email"] is None
    assert profile["personal_info"]["full_name"] == "Sarra Ben Ali"


def test_invalid_date_becomes_null() -> None:
    profile = parse(experiences__0__start_date="février 2025")

    assert profile["experiences"][0]["start_date"] is None
    assert profile["experiences"][0]["job_title"].startswith("Stagiaire")


def test_end_date_before_start_is_dropped_but_the_experience_kept() -> None:
    profile = parse(experiences__0__start_date="2025-07", experiences__0__end_date="2024-02")

    assert profile["experiences"][0]["start_date"] == "2025-07"
    assert profile["experiences"][0]["end_date"] is None


def test_entry_without_required_value_is_removed() -> None:
    profile = parse(experiences__0__job_title="  ")

    assert [e["job_title"] for e in profile["experiences"]] == ["Développeuse web"]


def test_invalid_link_is_removed_others_kept() -> None:
    profile = parse(personal_info__links=["not a url at all", "github.com/sarra"])

    assert profile["personal_info"]["links"] == ["https://github.com/sarra"]


def test_too_long_values_are_shortened() -> None:
    profile = parse(summary="x" * 6_000, skills=[{"name": f"s{i}"} for i in range(200)])

    assert len(profile["summary"]) == 5_000
    assert len(profile["skills"]) == 150


def test_answer_that_cannot_be_repaired() -> None:
    with pytest.raises(LLMResponseError):
        parse_llm_profile({"skills": "not a list"}, ContentLanguage.FR)
