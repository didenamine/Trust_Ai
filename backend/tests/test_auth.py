from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import PASSWORD_RESET_TOKEN_TYPE
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User  # noqa: F401 (registers the table on Base.metadata)


@pytest.fixture
def client() -> TestClient:
    """Overrides the module-level `client` fixture with one backed by an in-memory
    SQLite database, so auth tests don't need a real PostgreSQL instance."""
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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_register_then_login_and_me(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={"email": "candidate@example.com", "password": "S3cret!23", "full_name": "Ikram"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "candidate@example.com"
    assert body["full_name"] == "Ikram"
    assert "id" in body
    assert "password" not in body and "hashed_password" not in body

    login_response = client.post(
        "/api/auth/login", json={"email": "candidate@example.com", "password": "S3cret!23"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "candidate@example.com"


def test_register_duplicate_email_is_rejected(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "S3cret!23"}
    assert client.post("/api/auth/register", json=payload).status_code == 201

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "short@example.com", "password": "123"}
    )
    assert response.status_code == 422


def test_login_with_wrong_password_is_rejected(client: TestClient) -> None:
    client.post("/api/auth/register", json={"email": "wrong@example.com", "password": "S3cret!23"})

    response = client.post(
        "/api/auth/login", json={"email": "wrong@example.com", "password": "not-the-password"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "S3cret!23"}
    )
    assert response.status_code == 401


def test_me_without_token_is_rejected(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_password_reset_flow(client: TestClient) -> None:
    client.post(
        "/api/auth/register", json={"email": "reset@example.com", "password": "OldPassw0rd!"}
    )

    request_response = client.post(
        "/api/auth/password-reset/request", json={"email": "reset@example.com"}
    )
    assert request_response.status_code == 200
    reset_token = request_response.json()["reset_token"]
    assert reset_token

    confirm_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewPassw0rd!"},
    )
    assert confirm_response.status_code == 200

    old_login = client.post(
        "/api/auth/login", json={"email": "reset@example.com", "password": "OldPassw0rd!"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login", json={"email": "reset@example.com", "password": "NewPassw0rd!"}
    )
    assert new_login.status_code == 200


def test_password_reset_for_unknown_email_does_not_leak_existence(client: TestClient) -> None:
    response = client.post("/api/auth/password-reset/request", json={"email": "ghost@example.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["reset_token"] is None
    assert body["detail"]


def test_password_reset_confirm_with_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "not-a-jwt", "new_password": "NewPassw0rd!"},
    )
    assert response.status_code == 400


def test_password_reset_confirm_with_expired_token_is_rejected(client: TestClient) -> None:
    client.post(
        "/api/auth/register", json={"email": "expired@example.com", "password": "OldPassw0rd!"}
    )
    login = client.post(
        "/api/auth/login", json={"email": "expired@example.com", "password": "OldPassw0rd!"}
    )
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    ).json()

    # Built directly (not via the 15-minute-lived endpoint) so the test doesn't need to wait.
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": me["id"],
            "type": PASSWORD_RESET_TOKEN_TYPE,
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    response = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": expired_token, "new_password": "NewPassw0rd!"},
    )

    assert response.status_code == 400
    # The old password still works: the expired token changed nothing.
    assert (
        client.post(
            "/api/auth/login", json={"email": "expired@example.com", "password": "OldPassw0rd!"}
        ).status_code
        == 200
    )
