"""T-09 - storing and reading the candidate profile (GET / PUT /api/profile/me)."""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base, CVDocument, User
from app.schemas.profile import CandidateProfile
from app.services import profile_service
from app.services.profile_service import ProfileSource

PROFILE_FR = json.loads((Path(__file__).parent / "fixtures" / "profile_fr.json").read_text("utf-8"))


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def auth_headers(client: TestClient, email: str = "candidat@example.com") -> dict[str, str]:
    password = "S3cret!23"  # ggignore: test-only password
    client.post("/api/auth/register", json={"email": email, "password": password})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


# --- API -----------------------------------------------------------------------


def test_get_profile_returns_404_when_none(client: TestClient) -> None:
    response = client.get("/api/profile/me", headers=auth_headers(client))

    assert response.status_code == 404


def test_put_creates_a_manual_profile_then_get_returns_it(client: TestClient) -> None:
    headers = auth_headers(client)

    put = client.put("/api/profile/me", headers=headers, json=PROFILE_FR)
    get = client.get("/api/profile/me", headers=headers)

    assert put.status_code == 200
    assert get.status_code == 200
    body = get.json()
    assert body["source"] == "manual"
    assert body["cv_document_id"] is None
    assert body["profile"] == PROFILE_FR


def test_put_replaces_the_profile(client: TestClient) -> None:
    headers = auth_headers(client)
    client.put("/api/profile/me", headers=headers, json=PROFILE_FR)

    edited = {**PROFILE_FR, "summary": "Résumé corrigé", "skills": [{"name": "Go"}]}
    response = client.put("/api/profile/me", headers=headers, json=edited)

    profile = response.json()["profile"]
    assert profile["summary"] == "Résumé corrigé"
    assert [skill["name"] for skill in profile["skills"]] == ["Go"]


def test_put_normalizes_the_input(client: TestClient) -> None:
    response = client.put(
        "/api/profile/me",
        headers=auth_headers(client),
        json={
            "language": "en",
            "summary": "",
            "experiences": [{"job_title": "Dev", "start_date": "03/2021"}],
        },
    )

    profile = response.json()["profile"]
    assert profile["summary"] is None
    assert profile["experiences"][0]["start_date"] == "2021-03"
    assert profile["experiences"][0]["id"]


def test_put_rejects_an_invalid_profile(client: TestClient) -> None:
    response = client.put(
        "/api/profile/me",
        headers=auth_headers(client),
        json={"language": "fr", "experiences": [{"job_title": "Dev", "start_date": "2021-13"}]},
    )

    assert response.status_code == 422


def test_profile_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/profile/me").status_code == 401
    assert client.put("/api/profile/me", json=PROFILE_FR).status_code == 401


def test_candidates_only_see_their_own_profile(client: TestClient) -> None:
    alice = auth_headers(client, "alice@example.com")
    bob = auth_headers(client, "bob@example.com")
    client.put("/api/profile/me", headers=alice, json=PROFILE_FR)

    assert client.get("/api/profile/me", headers=bob).status_code == 404


# --- Service (used by US05) ----------------------------------------------------


def test_cv_analysis_links_the_cv_and_keeps_its_source_on_later_edits(
    session_factory: sessionmaker[Session],
) -> None:
    db = session_factory()
    user = User(email="c@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    cv = CVDocument(
        user_id=user.id,
        original_filename="cv.pdf",
        storage_key=f"{user.id}/cv.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )
    db.add(cv)
    db.commit()
    profile = CandidateProfile.model_validate(PROFILE_FR)

    record = profile_service.save_profile(
        db,
        user_id=user.id,
        profile=profile,
        source=ProfileSource.CV_ANALYSIS,
        cv_document_id=cv.id,
    )
    assert (record.source, record.cv_document_id) == ("cv_analysis", cv.id)

    edited = profile.model_copy(update={"summary": "Corrigé"})
    record = profile_service.save_profile(
        db, user_id=user.id, profile=edited, source=ProfileSource.MANUAL
    )
    assert (record.source, record.cv_document_id) == ("cv_analysis", cv.id)
    assert profile_service.get_candidate_profile(db, user.id).summary == "Corrigé"
    assert profile_service.get_candidate_profile(db, uuid.uuid4()) is None
