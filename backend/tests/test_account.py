"""US02 - account management (update info, change password, delete account)."""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base, Profile, User

PASSWORD = "S3cret!23"  # ggignore: test-only password
PROFILE_FR = json.loads((Path(__file__).parent / "fixtures" / "profile_fr.json").read_text("utf-8"))


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite ignores foreign keys by default: turn them on so that deleting a
    # user actually cascades to their owned rows, matching PostgreSQL in prod.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def auth_headers(
    client: TestClient, email: str = "candidat@example.com", password: str = PASSWORD
) -> dict[str, str]:
    client.post("/api/auth/register", json={"email": email, "password": password})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


# --- Update personal information -------------------------------------------------


def test_update_full_name(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.patch("/api/auth/me", headers=headers, json={"full_name": "Ikram K."})

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ikram K."


def test_update_email(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.patch(
        "/api/auth/me", headers=headers, json={"email": "nouvelle.adresse@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "nouvelle.adresse@example.com"
    # The new address logs in; the old one no longer does.
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "nouvelle.adresse@example.com", "password": PASSWORD},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "candidat@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_update_email_already_taken_is_rejected(client: TestClient) -> None:
    auth_headers(client, email="premier@example.com")
    headers = auth_headers(client, email="second@example.com")

    response = client.patch("/api/auth/me", headers=headers, json={"email": "premier@example.com"})

    assert response.status_code == 409


def test_update_without_body_changes_nothing(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.patch("/api/auth/me", headers=headers, json={})

    assert response.status_code == 200
    assert response.json()["email"] == "candidat@example.com"


def test_update_requires_authentication(client: TestClient) -> None:
    response = client.patch("/api/auth/me", json={"full_name": "Quelqu'un"})
    assert response.status_code == 401


# --- Change password ---------------------------------------------------------------


def test_change_password(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "NouveauPass!23"},
    )

    assert response.status_code == 204
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "candidat@example.com", "password": "NouveauPass!23"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "candidat@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_change_password_with_wrong_current_password_is_rejected(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": "mauvais-mot-de-passe", "new_password": "NouveauPass!23"},
    )

    assert response.status_code == 401
    # The password did not change.
    assert (
        client.post(
            "/api/auth/login", json={"email": "candidat@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )


# --- Delete account ------------------------------------------------------------------


def test_delete_account(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.delete("/api/auth/me", headers=headers)

    assert response.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "candidat@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_delete_account_requires_authentication(client: TestClient) -> None:
    assert client.delete("/api/auth/me").status_code == 401


def test_delete_account_cascades_owned_data(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    headers = auth_headers(client)
    user_id = uuid.UUID(client.get("/api/auth/me", headers=headers).json()["id"])

    # A profile (US06/US07) is owned data that must disappear with the account.
    assert client.put("/api/profile/me", headers=headers, json=PROFILE_FR).status_code == 200

    db = session_factory()
    try:
        assert db.query(Profile).filter(Profile.user_id == user_id).first() is not None
    finally:
        db.close()

    assert client.delete("/api/auth/me", headers=headers).status_code == 204

    db = session_factory()
    try:
        assert db.query(User).filter(User.id == user_id).first() is None
        assert db.query(Profile).filter(Profile.user_id == user_id).first() is None
    finally:
        db.close()
