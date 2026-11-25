"""US33 - Compétences manquantes et prioritaires, agrégées sur toutes les offres analysées."""

import json
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
from app.services.llm import get_llm_client
from app.services.llm.fake import FakeLLMClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROFILE_FR = json.loads((FIXTURES_DIR / "profile_fr.json").read_text("utf-8"))
PASSWORD = "S3cret!23"  # ggignore: test-only password

OFFER_BACKEND = """\
Développeur backend (H/F)

Nous recherchons un développeur backend pour renforcer notre équipe produit. \
Vous travaillerez sur des services en Python et en Java, déployés sur Kubernetes.

Profil recherché :
- Une expérience confirmée en développement backend ;
- Maîtrise de Python et de Java ;
- Connaissance de Kubernetes pour le déploiement des services.
"""

OFFER_CLOUD = """\
Ingénieur cloud (H/F)

Nous recherchons un ingénieur cloud pour faire évoluer notre infrastructure. \
Vous interviendrez sur des projets Python et Java, hébergés sur AWS.

Profil recherché :
- Une expérience en ingénierie cloud ;
- Maîtrise de Python et de Java ;
- Connaissance d'AWS pour l'hébergement des services.
"""

ANSWER_BACKEND: dict[str, Any] = {
    "job_title": "Développeur backend",
    "skills": [
        {"name": "Python", "category": "hard", "level": None},
        {"name": "Java", "category": "hard", "level": None},
        {"name": "Kubernetes", "category": "hard", "level": None},
    ],
    "experiences": [],
    "education": [],
}

ANSWER_CLOUD: dict[str, Any] = {
    "job_title": "Ingénieur cloud",
    "skills": [
        {"name": "Python", "category": "hard", "level": None},
        {"name": "Java", "category": "hard", "level": None},
        {"name": "AWS", "category": "hard", "level": None},
    ],
    "experiences": [],
    "education": [],
}


@pytest.fixture
def llm() -> FakeLLMClient:
    return FakeLLMClient(ANSWER_BACKEND, ANSWER_CLOUD)


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


def auth_headers(client: TestClient, email: str = "candidat@example.com") -> dict[str, str]:
    credentials = {"email": email, "password": PASSWORD}
    client.post("/api/auth/register", json=credentials)
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_and_analyze_offer(client: TestClient, headers: dict[str, str], text: str) -> str:
    created = client.post("/api/offers", headers=headers, json={"text": text})
    assert created.status_code == 201, created.text
    offer_id = created.json()["id"]
    analyzed = client.post(f"/api/offers/{offer_id}/analyze", headers=headers)
    assert analyzed.status_code == 201, analyzed.text
    return offer_id


def test_skill_gaps_requires_a_profile(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.get("/api/matching/skill-gaps", headers=headers)

    assert response.status_code == 404


def test_skill_gaps_with_no_analysed_offer(client: TestClient) -> None:
    headers = auth_headers(client)
    assert client.put("/api/profile/me", headers=headers, json=PROFILE_FR).status_code == 200

    response = client.get("/api/matching/skill-gaps", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body == {"skills": [], "offers_considered": 0}


def test_skill_gaps_ranks_the_most_frequently_missing_skill_first(client: TestClient) -> None:
    headers = auth_headers(client)
    assert client.put("/api/profile/me", headers=headers, json=PROFILE_FR).status_code == 200

    add_and_analyze_offer(client, headers, OFFER_BACKEND)
    add_and_analyze_offer(client, headers, OFFER_CLOUD)

    response = client.get("/api/matching/skill-gaps", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["offers_considered"] == 2

    by_name = {skill["name"]: skill for skill in body["skills"]}
    # Python is in the candidate's profile: never missing.
    assert "Python" not in by_name
    # Java is required by both offers and missing from both.
    assert by_name["Java"]["missing_in_offers"] == 2
    assert by_name["Kubernetes"]["missing_in_offers"] == 1
    assert by_name["AWS"]["missing_in_offers"] == 1
    # Most frequently missing first.
    assert body["skills"][0]["name"] == "Java"


def test_skill_gaps_skips_offers_without_an_analysis_yet(client: TestClient) -> None:
    headers = auth_headers(client)
    assert client.put("/api/profile/me", headers=headers, json=PROFILE_FR).status_code == 200

    add_and_analyze_offer(client, headers, OFFER_BACKEND)
    # A second offer is added but never analysed.
    not_analyzed = client.post("/api/offers", headers=headers, json={"text": OFFER_CLOUD})
    assert not_analyzed.status_code == 201, not_analyzed.text

    response = client.get("/api/matching/skill-gaps", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["offers_considered"] == 1
    by_name = {skill["name"]: skill for skill in body["skills"]}
    assert by_name["Java"]["missing_in_offers"] == 1
    assert "AWS" not in by_name  # only required by the unanalysed offer


def test_skill_gaps_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/matching/skill-gaps").status_code == 401
