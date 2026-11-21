"""US09 - Analyse automatique de l'offre: from a saved offer to stored requirements."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.llm import (
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)
from app.services.llm.fake import FakeLLMClient
from app.services.offer_analysis_service import (
    OFFER_EXTRACTION_SCHEMA,
    SYSTEM_PROMPT,
)

OFFER_FR = """\
Développeuse / Développeur full-stack (H/F)

Nous recherchons un développeur full-stack pour rejoindre notre équipe produit. \
Vous développerez des interfaces React et des API Python/FastAPI.

Profil recherché :
- Trois à cinq ans d'expérience professionnelle en développement web ;
- Maîtrise de React, Python et PostgreSQL ;
- Bac+5 en informatique ou diplôme d'ingénieur ;
- Bonnes capacités de communication et de travail en équipe.
"""

OFFER_EN = """\
Full-stack developer

We are looking for a full-stack developer to join our product team. You will \
build React interfaces and Python/FastAPI services.

Requirements:
- At least 2 years of professional experience in web development;
- Strong knowledge of React, Python and PostgreSQL;
- Bachelor's degree in computer science or an equivalent qualification;
- Good communication and teamwork skills.
"""

OFFER_ES = """\
Buscamos un ingeniero de software para desarrollar aplicaciones web y bases de \
datos. Se requiere experiencia profesional, trabajo en equipo y buena \
comunicación con los clientes.
"""

ANSWER_FR: dict[str, Any] = {
    "job_title": "Développeur full-stack",
    "skills": [
        {"name": "React", "category": "hard", "level": "advanced"},
        {"name": "Python", "category": "hard", "level": None},
        {"name": "Communication", "category": "soft", "level": None},
    ],
    "experiences": [
        {
            "min_years": 3,
            "max_years": 5,
            "job_title": "Développeur full-stack",
            "employment_type": "full_time",
            "description": "Trois à cinq ans d'expérience en développement web",
            "skills": ["React", "Python"],
        }
    ],
    "education": [
        {
            "level": "master",
            "degree": "Master en informatique",
            "field_of_study": "informatique",
            "description": "Bac+5 en informatique ou diplôme d'ingénieur",
        }
    ],
}

ANSWER_EN: dict[str, Any] = {
    "job_title": "Full-stack developer",
    "skills": [
        {"name": "React", "category": "hard", "level": None},
        {"name": "Python", "category": "hard", "level": "expert"},
    ],
    "experiences": [
        {
            "min_years": 2,
            "max_years": None,
            "job_title": "Full-stack developer",
            "employment_type": "full_time",
            "description": "At least 2 years of professional experience in web development",
            "skills": ["React", "Python"],
        }
    ],
    "education": [
        {
            "level": "bachelor",
            "degree": "Bachelor's degree in computer science",
            "field_of_study": "computer science",
            "description": "Bachelor's degree or an equivalent qualification",
        }
    ],
}


@pytest.fixture
def llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def client(llm: FakeLLMClient) -> Iterator[TestClient]:
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
    app.dependency_overrides[get_llm_client] = lambda: llm
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, "candidat@example.com")


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "S3cret!23"}  # ggignore
    client.post("/api/auth/register", json=credentials)
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_offer(client: TestClient, headers: dict[str, str], text: str) -> str:
    response = client.post("/api/offers", headers=headers, json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def analyze(client: TestClient, headers: dict[str, str], offer_id: str, *, refresh: bool = False):
    params = {"refresh": "true"} if refresh else None
    return client.post(f"/api/offers/{offer_id}/analyze", headers=headers, params=params)


def get_analysis(client: TestClient, headers: dict[str, str], offer_id: str):
    return client.get(f"/api/offers/{offer_id}/analysis", headers=headers)


# --- Full pipeline -------------------------------------------------------------


def test_french_offer_becomes_stored_requirements(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    llm._answers.append(ANSWER_FR)
    offer_id = add_offer(client, headers, OFFER_FR)

    response = analyze(client, headers, offer_id)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["offer_id"] == offer_id
    requirements = data["requirements"]
    assert requirements["schema_version"] == 1
    assert requirements["language"] == "fr"
    assert requirements["job_title"] == "Développeur full-stack"
    assert {skill["name"] for skill in requirements["skills"]} == {
        "React",
        "Python",
        "Communication",
    }
    assert requirements["experiences"][0]["min_years"] == 3
    assert requirements["experiences"][0]["max_years"] == 5
    assert requirements["education"][0]["level"] == "master"

    stored = get_analysis(client, headers, offer_id)
    assert stored.status_code == 200, stored.text
    assert stored.json()["requirements"] == requirements

    assert len(llm.calls) == 1
    call = llm.calls[0]
    assert call["system"] == SYSTEM_PROMPT
    assert call["schema"] is OFFER_EXTRACTION_SCHEMA
    assert call["schema_name"] == "offer_requirements"
    assert "written in French" in call["user"]
    assert "<offer>" in call["user"] and OFFER_FR in call["user"]


def test_english_offer_has_the_same_shape(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    llm._answers.append(ANSWER_EN)
    offer_id = add_offer(client, headers, OFFER_EN)

    response = analyze(client, headers, offer_id)
    assert response.status_code == 201, response.text
    requirements = response.json()["requirements"]
    assert requirements["language"] == "en"
    assert requirements["job_title"] == "Full-stack developer"
    assert requirements["experiences"][0]["min_years"] == 2
    assert requirements["experiences"][0]["max_years"] is None
    assert requirements["education"][0]["level"] == "bachelor"
    assert "written in English" in llm.calls[0]["user"]
    assert set(requirements) == {
        "schema_version",
        "language",
        "job_title",
        "skills",
        "experiences",
        "education",
    }


def test_cached_result_is_reused_and_refresh_replaces_it(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    refreshed = {**ANSWER_FR, "job_title": "Ingénieur full-stack"}
    llm._answers.append(ANSWER_FR)
    llm._answers.append(refreshed)
    offer_id = add_offer(client, headers, OFFER_FR)

    first = analyze(client, headers, offer_id)
    assert first.status_code == 201
    analysis_id = first.json()["id"]

    cached = analyze(client, headers, offer_id)
    assert cached.status_code == 200
    assert cached.json()["requirements"]["job_title"] == "Développeur full-stack"
    assert len(llm.calls) == 1

    updated = analyze(client, headers, offer_id, refresh=True)
    assert updated.status_code == 200
    assert updated.json()["id"] == analysis_id
    assert updated.json()["requirements"]["job_title"] == "Ingénieur full-stack"
    assert len(llm.calls) == 2


# --- Access control and errors -------------------------------------------------


def test_analysis_is_only_available_to_a_candidate_who_has_the_offer(
    client: TestClient, headers: dict[str, str]
) -> None:
    offer_id = add_offer(client, headers, OFFER_FR)
    assert get_analysis(client, headers, offer_id).json()["detail"] == "Analyse introuvable."

    other = auth_headers(client, "autre@example.com")
    assert get_analysis(client, other, offer_id).status_code == 404
    assert get_analysis(client, other, offer_id).json()["detail"] == "Offre introuvable."
    assert analyze(client, other, offer_id).status_code == 404


def test_analysis_requires_authentication(client: TestClient, headers: dict[str, str]) -> None:
    offer_id = add_offer(client, headers, OFFER_FR)
    assert get_analysis(client, {}, offer_id).status_code == 401
    assert analyze(client, {}, offer_id).status_code == 401


def test_unsupported_language_is_rejected_before_calling_the_llm(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    offer_id = add_offer(client, headers, OFFER_ES)

    response = analyze(client, headers, offer_id)
    assert response.status_code == 422, response.text
    assert "français ou en anglais" in response.json()["detail"]
    assert llm.calls == []


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_header"),
    [
        (LLMNotConfiguredError("no key"), 503, None),
        (LLMRateLimitError("slow down", retry_after=42.4), 429, "42"),
        (LLMUnavailableError("timeout"), 503, None),
        (LLMResponseError("bad json"), 502, None),
    ],
)
def test_llm_errors_are_mapped_and_nothing_is_saved(
    client: TestClient,
    headers: dict[str, str],
    llm: FakeLLMClient,
    error: Exception,
    expected_status: int,
    expected_header: str | None,
) -> None:
    llm._answers.append(error)
    offer_id = add_offer(client, headers, OFFER_FR)

    response = analyze(client, headers, offer_id)
    assert response.status_code == expected_status, response.text
    if expected_header is not None:
        assert response.headers["retry-after"] == expected_header
    assert get_analysis(client, headers, offer_id).status_code == 404


def test_unrepairable_answer_is_reported_as_a_bad_gateway(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    llm._answers.append({**ANSWER_FR, "skills": "not a list"})
    offer_id = add_offer(client, headers, OFFER_FR)

    response = analyze(client, headers, offer_id)
    assert response.status_code == 502, response.text
    assert get_analysis(client, headers, offer_id).status_code == 404


# --- Validation and schema -----------------------------------------------------


def test_llm_answers_are_repaired_and_normalised(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    answer: dict[str, Any] = {
        **ANSWER_FR,
        "unexpected_extra_key": "ignored",
        "skills": [
            {"name": "R" * 250, "category": "hard", "level": "beginner"},
            {"name": "react ", "category": "hard", "level": "expert"},
            {"name": "React", "category": "hard", "level": "intermediate"},
        ],
        "experiences": [
            {**ANSWER_FR["experiences"][0], "min_years": 99, "max_years": None},
            {
                **ANSWER_FR["experiences"][0],
                "min_years": 3,
                "max_years": 1,
                "employment_type": "unknown-type",
            },
        ],
    }
    llm._answers.append(answer)
    offer_id = add_offer(client, headers, OFFER_FR)

    response = analyze(client, headers, offer_id)
    assert response.status_code == 201, response.text
    requirements = response.json()["requirements"]
    assert "unexpected_extra_key" not in requirements
    react = [skill for skill in requirements["skills"] if skill["name"].lower() == "react"]
    assert len(react) == 1  # the two spellings were merged
    assert react[0]["level"] == "expert"
    assert any(len(skill["name"]) == 200 for skill in requirements["skills"])
    first, second = requirements["experiences"]
    assert first["min_years"] is None  # 99 is out of range
    assert second["max_years"] is None  # 1 < min_years 3
    assert second["employment_type"] is None


def test_strict_schema_excludes_app_fields_and_every_object_is_closed() -> None:
    def objects(node: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(node, list):
            for item in node:
                found.extend(objects(item))
        elif isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                found.append(node)
            found.extend(objects(list(node.values())))
        return found

    assert "schema_version" not in OFFER_EXTRACTION_SCHEMA["properties"]
    assert "language" not in OFFER_EXTRACTION_SCHEMA["properties"]
    assert "anyOf" not in str(OFFER_EXTRACTION_SCHEMA)
    for obj in objects(OFFER_EXTRACTION_SCHEMA):
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])
