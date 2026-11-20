import pytest
from fastapi.testclient import TestClient

from app.services import offer_fetcher

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
    assert offers[0]["description"] == OFFER_TEXT


def test_list_offers_requires_authentication(db_client: TestClient) -> None:
    assert db_client.get("/api/offers").status_code == 401


OFFER_URL = "https://jobs.example.com/offres/42"


def _failing_fetch(error: Exception):
    def fetch(url: str) -> str:
        raise error

    return fetch


def test_create_offer_from_url(db_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(offer_fetcher, "fetch_offer_text", lambda url: OFFER_TEXT)
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "url"
    assert body["source_url"] == OFFER_URL
    assert body["content"] == OFFER_TEXT


@pytest.mark.parametrize(
    "payload",
    [
        {"url": "pas-une-url"},
        {"url": "ftp://example.com/offre"},
        {"url": OFFER_URL, "text": OFFER_TEXT},
    ],
)
def test_create_offer_rejects_invalid_source(db_client: TestClient, payload) -> None:
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json=payload, headers=headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (offer_fetcher.UnsafeUrlError(), 422),
        (offer_fetcher.NoContentError("Aucun texte."), 422),
        (offer_fetcher.FetchFailedError("La page a répondu avec le code 404."), 502),
    ],
)
def test_url_fetch_errors_are_mapped_to_http_errors(
    db_client: TestClient, monkeypatch: pytest.MonkeyPatch, error: Exception, expected_status: int
) -> None:
    monkeypatch.setattr(offer_fetcher, "fetch_offer_text", _failing_fetch(error))
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=headers)

    assert response.status_code == expected_status
    assert db_client.get("/api/offers", headers=headers).json() == []


def _count_fetches(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def fetch(url: str) -> str:
        calls.append(url)
        return OFFER_TEXT

    monkeypatch.setattr(offer_fetcher, "fetch_offer_text", fetch)
    return calls


def test_same_url_is_saved_only_once(db_client: TestClient, monkeypatch) -> None:
    calls = _count_fetches(monkeypatch)
    headers = _auth_headers(db_client)

    first = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=headers)
    second = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(calls) == 1  # the page is not downloaded a second time
    assert len(db_client.get("/api/offers", headers=headers).json()) == 1


def test_url_variants_are_the_same_offer(db_client: TestClient, monkeypatch) -> None:
    calls = _count_fetches(monkeypatch)
    headers = _auth_headers(db_client)
    first = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=headers)

    second = db_client.post(
        "/api/offers",
        json={"url": "https://JOBS.example.com/offres/42/?utm_source=newsletter#postuler"},
        headers=headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(calls) == 1


def test_two_users_share_one_offer_for_the_same_url(db_client: TestClient, monkeypatch) -> None:
    calls = _count_fetches(monkeypatch)
    alice = _auth_headers(db_client, "alice@example.com")
    bob = _auth_headers(db_client, "bob@example.com")
    carol = _auth_headers(db_client, "carol@example.com")

    first = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=alice)
    second = db_client.post("/api/offers", json={"url": OFFER_URL}, headers=bob)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]  # one stored offer
    assert len(calls) == 1  # the page is downloaded only once
    assert len(db_client.get("/api/offers", headers=alice).json()) == 1
    assert len(db_client.get("/api/offers", headers=bob).json()) == 1
    assert db_client.get("/api/offers", headers=carol).json() == []


def test_create_offer_accepts_any_pasted_text(db_client: TestClient) -> None:
    pasted = (
        "Développeur Python\x00 backend\r\nVous concevez des API REST\x07 avec FastAPI.\r\n"
        '\tExpérience : 3 ans • "Télétravail" 🚀 — CDI / Stage (H/F) & plus…'
    )
    headers = _auth_headers(db_client)

    response = db_client.post("/api/offers", json={"text": pasted}, headers=headers)

    assert response.status_code == 201
    assert response.json()["content"] == (
        "Développeur Python backend\nVous concevez des API REST avec FastAPI.\n"
        '\tExpérience : 3 ans • "Télétravail" 🚀 — CDI / Stage (H/F) & plus…'
    )


def test_list_offers_returns_title_and_description(db_client: TestClient) -> None:
    text = (
        "Stage PFE Data Scientist\nBestlab · Tunis\n\n"
        "Analyse de données et développement de modèles prédictifs pour nos clients."
    )
    headers = _auth_headers(db_client)
    db_client.post("/api/offers", json={"text": text}, headers=headers)

    offers = db_client.get("/api/offers", headers=headers).json()

    assert len(offers) == 1
    assert offers[0]["title"] == "Stage PFE Data Scientist"
    assert offers[0]["description"].startswith("Bestlab · Tunis")
    assert offers[0]["source_type"] == "text"
    assert "content" not in offers[0]
