import pytest
from fastapi.testclient import TestClient

OFFER_TEXT = (
    "Développeur Python backend (H/F). Vous concevez des API REST avec FastAPI, "
    "vous maîtrisez PostgreSQL et Docker. 3 ans d'expérience minimum."
)


def _auth_headers(client: TestClient, email: str = "candidate@example.com") -> dict[str, str]:
    client.post("/api/auth/register", json={"email": email, "password": "S3cret!23"})
    response = client.post("/api/auth/login", json={"email": email, "password": "S3cret!23"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_offer_from_text(db_client: TestClient) -> None:
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json={"text": OFFER_TEXT}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "text"
    assert body["source_url"] is None
    assert body["content"] == OFFER_TEXT
    assert body["id"] and body["created_at"]


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "   "}, {"text": "trop court"}])
def test_create_offer_rejects_missing_or_too_short_text(db_client: TestClient, payload) -> None:
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json=payload, headers=headers)

    assert response.status_code == 422


def test_create_offer_requires_authentication(db_client: TestClient) -> None:
    response = db_client.post("/api/offers", json={"text": OFFER_TEXT})
    assert response.status_code == 401


def test_list_offers_returns_only_my_offers(db_client: TestClient) -> None:
    mine = _auth_headers(db_client, "me@example.com")
    other = _auth_headers(db_client, "other@example.com")
    db_client.post("/api/offers", json={"text": OFFER_TEXT}, headers=mine)
    db_client.post("/api/offers", json={"text": OFFER_TEXT + " (autre)"}, headers=other)

    response = db_client.get("/api/offers", headers=mine)

    assert response.status_code == 200
    offers = response.json()
    assert len(offers) == 1
    assert offers[0]["content"] == OFFER_TEXT


def test_list_offers_requires_authentication(db_client: TestClient) -> None:
    assert db_client.get("/api/offers").status_code == 401
