"""US14 - Adaptation du CV à une offre: du profil et de l'écart du matching au CV adapté."""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.cv_adaptation_service import ADAPTATION_SCHEMA, SYSTEM_PROMPT
from app.services.llm import (
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)
from app.services.llm.fake import FakeLLMClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"

OFFER_FR = """\
Développeuse / Développeur full-stack (H/F)

Nous recherchons un développeur full-stack pour rejoindre notre équipe produit. \
Vous développerez des interfaces React et des API Python, déployées sur Kubernetes.

Profil recherché :
- Un an d'expérience professionnelle en développement web ;
- Maîtrise de React, Python et Kubernetes ;
- Licence en informatique ;
- Bonnes capacités de communication et de travail en équipe.
"""

OFFER_ANSWER: dict[str, Any] = {
    "job_title": "Développeur full-stack",
    "skills": [
        {"name": "Python", "category": "hard", "level": None},
        {"name": "React", "category": "hard", "level": None},
        {"name": "Kubernetes", "category": "hard", "level": None},
    ],
    "experiences": [
        {
            "min_years": 1,
            "max_years": None,
            "job_title": "Développeur full-stack",
            "employment_type": "full_time",
            "description": "Un an d'expérience professionnelle en développement web",
            "skills": ["Python"],
        }
    ],
    "education": [
        {
            "level": "bachelor",
            "degree": "Licence en informatique",
            "field_of_study": "informatique",
            "description": "Licence en informatique",
        }
    ],
}

# Contains two things the application must remove: a skill the candidate does not have
# (Kubernetes) and an experience that is not in the profile.
ADAPTED_ANSWER: dict[str, Any] = {
    "headline": "Développeuse full-stack Python / React",
    "summary": "Développeuse full-stack à l'aise avec Python et React, habituée aux API REST.",
    "highlighted_skills": ["Python", "React", "Kubernetes", "FastAPI"],
    "experiences": [
        {
            "experience_id": "exp-pfe",
            "description": "Développement d'une plateforme web en Python et React.",
            "achievements": ["Développement d'une API REST FastAPI de 25 endpoints"],
        },
        {
            "experience_id": "exp-inconnue",
            "description": "Expérience inventée.",
            "achievements": [],
        },
    ],
    "changes": ["Résumé recentré sur Python et React, demandés par l'offre."],
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


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "S3cret!23"}  # ggignore
    client.post("/api/auth/register", json=credentials)
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, "candidat@example.com")


def load_profile() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "profile_fr.json").read_text(encoding="utf-8"))


def put_profile(client: TestClient, headers: dict[str, str]) -> None:
    response = client.put("/api/profile/me", headers=headers, json=load_profile())
    assert response.status_code == 200, response.text


def add_offer(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/offers", headers=headers, json={"text": OFFER_FR})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_analyzed_offer(client: TestClient, headers: dict[str, str], llm: FakeLLMClient) -> str:
    offer_id = add_offer(client, headers)
    llm._answers.append(OFFER_ANSWER)
    response = client.post(f"/api/offers/{offer_id}/analyze", headers=headers)
    assert response.status_code == 201, response.text
    return offer_id


def adapt(client: TestClient, headers: dict[str, str], offer_id: str):
    return client.post(f"/api/adaptations/{offer_id}", headers=headers)


@pytest.fixture
def ready(client: TestClient, headers: dict[str, str], llm: FakeLLMClient) -> str:
    """A candidate with a profile and an analysed offer: returns the offer id."""
    put_profile(client, headers)
    return add_analyzed_offer(client, headers, llm)


# --- Full pipeline -------------------------------------------------------------


def test_cv_is_adapted_and_stored(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, ready: str
) -> None:
    llm._answers.append(ADAPTED_ANSWER)

    response = adapt(client, headers, ready)
    assert response.status_code == 201, response.text
    data = response.json()
    adapted = data["adapted_cv"]

    assert data["offer_id"] == ready
    assert adapted["language"] == "fr"
    assert adapted["headline"] == "Développeuse full-stack Python / React"
    assert adapted["changes"] == ["Résumé recentré sur Python et React, demandés par l'offre."]

    # The adaptation starts from the matching score and keeps the gap it cannot fill.
    matching = client.get(f"/api/matching/{ready}", headers=headers).json()
    assert data["matching_score"] == matching["total_score"]
    assert data["missing_skills"] == ["Kubernetes"]

    # A skill the candidate does not have never enters the CV; the others are all kept.
    skills = adapted["highlighted_skills"]
    all_skills = [skill["name"] for skill in load_profile()["skills"]]
    assert "Kubernetes" not in skills
    assert skills[:3] == ["Python", "React", "FastAPI"]
    assert sorted(skills) == sorted(all_skills)

    # An experience that is not in the profile is ignored.
    assert [e["experience_id"] for e in adapted["experiences"]] == ["exp-pfe"]

    # The complete CV is assembled from the profile, in ATS form.
    cv = data["document"]
    assert cv["contact"]["full_name"] == "Sarra Ben Ali"
    assert cv["experiences"][0]["job_title"] == "Développeuse web"  # newest first
    assert cv["missing_sections"] == []
    assert "EXPÉRIENCE PROFESSIONNELLE" in data["ats_text"].splitlines()
    assert "Kubernetes" not in data["ats_text"]

    stored = client.get(f"/api/adaptations/{ready}", headers=headers)
    assert stored.status_code == 200, stored.text
    assert stored.json() == data


def test_prompt_carries_the_gap_and_no_contact_details(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, ready: str
) -> None:
    llm._answers.append(ADAPTED_ANSWER)
    assert adapt(client, headers, ready).status_code == 201

    call = llm.calls[-1]
    assert call["system"] == SYSTEM_PROMPT
    assert call["schema"] is ADAPTATION_SCHEMA
    assert call["schema_name"] == "cv_adaptation"
    assert "in French" in call["user"]
    assert "<profile>" in call["user"] and "<offer>" in call["user"] and "<gap>" in call["user"]
    assert "Kubernetes" in call["user"]
    assert "exp-pfe" in call["user"]
    assert "sarra.benali@example.com" not in call["user"]
    assert "+216 20 000 000" not in call["user"]


def test_adapting_again_replaces_the_stored_result(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, ready: str
) -> None:
    llm._answers.append(ADAPTED_ANSWER)
    assert adapt(client, headers, ready).status_code == 201

    llm._answers.append({**ADAPTED_ANSWER, "summary": "Nouveau résumé."})
    second = adapt(client, headers, ready)
    assert second.status_code == 200, second.text
    assert second.json()["adapted_cv"]["summary"] == "Nouveau résumé."

    stored = client.get(f"/api/adaptations/{ready}", headers=headers).json()
    assert stored["adapted_cv"]["summary"] == "Nouveau résumé."
    assert stored["id"] == second.json()["id"]


def test_text_that_is_too_long_is_shortened_not_rejected(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, ready: str
) -> None:
    llm._answers.append({**ADAPTED_ANSWER, "summary": "x" * 5200})

    response = adapt(client, headers, ready)
    assert response.status_code == 201, response.text
    assert len(response.json()["adapted_cv"]["summary"]) == 5000


# --- Access and preconditions --------------------------------------------------


def test_authentication_is_required(client: TestClient) -> None:
    offer_id = uuid.uuid4()
    assert client.post(f"/api/adaptations/{offer_id}").status_code == 401
    assert client.get(f"/api/adaptations/{offer_id}").status_code == 401


def test_unknown_offer_is_not_found(client: TestClient, headers: dict[str, str]) -> None:
    offer_id = uuid.uuid4()
    assert adapt(client, headers, str(offer_id)).status_code == 404
    assert client.get(f"/api/adaptations/{offer_id}", headers=headers).status_code == 404


def test_another_candidates_offer_is_not_found(
    client: TestClient, llm: FakeLLMClient, ready: str
) -> None:
    other = auth_headers(client, "autre@example.com")
    put_profile(client, other)

    assert adapt(client, other, ready).status_code == 404
    assert client.get(f"/api/adaptations/{ready}", headers=other).status_code == 404


def test_a_profile_is_required(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient
) -> None:
    offer_id = add_analyzed_offer(client, headers, llm)

    response = adapt(client, headers, offer_id)
    assert response.status_code == 404
    assert "Profil" in response.json()["detail"]


def test_the_offer_must_be_analyzed_first(client: TestClient, headers: dict[str, str]) -> None:
    put_profile(client, headers)
    offer_id = add_offer(client, headers)

    response = adapt(client, headers, offer_id)
    assert response.status_code == 400
    assert "analysée" in response.json()["detail"]


def test_reading_before_adapting_is_not_found(
    client: TestClient, headers: dict[str, str], ready: str
) -> None:
    response = client.get(f"/api/adaptations/{ready}", headers=headers)
    assert response.status_code == 404
    assert "Aucune adaptation" in response.json()["detail"]


# --- LLM failures --------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (LLMNotConfiguredError("no key"), 503),
        (LLMRateLimitError("slow down", retry_after=30), 429),
        (LLMUnavailableError("down"), 503),
        (LLMResponseError("garbage"), 502),
    ],
)
def test_llm_failures_are_reported_and_nothing_is_stored(
    client: TestClient,
    headers: dict[str, str],
    llm: FakeLLMClient,
    ready: str,
    error: Exception,
    status_code: int,
) -> None:
    llm._answers.append(error)

    response = adapt(client, headers, ready)
    assert response.status_code == status_code
    if status_code == 429:
        assert response.headers["Retry-After"] == "30"
    assert client.get(f"/api/adaptations/{ready}", headers=headers).status_code == 404


def test_an_unusable_answer_gives_a_502(
    client: TestClient, headers: dict[str, str], llm: FakeLLMClient, ready: str
) -> None:
    llm._answers.append({"experiences": "oops"})

    assert adapt(client, headers, ready).status_code == 502
    assert client.get(f"/api/adaptations/{ready}", headers=headers).status_code == 404
