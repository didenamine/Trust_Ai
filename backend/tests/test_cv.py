"""US03 - Import du CV."""

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services import cv_service
from app.services.storage import LocalFileStorage, get_storage

MAX_MB = 1
MAX_BYTES = MAX_MB * 1024 * 1024

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def make_docx(entries: tuple[str, ...] = ("word/document.xml",)) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        for name in entries:
            archive.writestr(name, "<xml/>")
    return buffer.getvalue()


DOCX_BYTES = make_docx()


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(upload_dir: Path) -> Iterator[TestClient]:
    """In-memory SQLite database, temporary upload folder and a 1 Mo size limit."""
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
    app.dependency_overrides[get_storage] = lambda: LocalFileStorage(upload_dir)
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_size_mb=MAX_MB)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def auth_headers(client: TestClient, email: str = "candidat@example.com") -> dict[str, str]:
    password = "S3cret!23"
    client.post("/api/auth/register", json={"email": email, "password": password})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload(client: TestClient, headers: dict[str, str], filename: str, content: bytes):
    return client.post("/api/cv", headers=headers, files={"file": (filename, content)})


def stored_files(upload_dir: Path) -> list[Path]:
    return [p for p in upload_dir.rglob("*") if p.is_file()] if upload_dir.exists() else []


# --- Import -----------------------------------------------------------------


def test_upload_pdf_stores_file_in_candidate_space(client: TestClient, upload_dir: Path) -> None:
    headers = auth_headers(client)
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]

    response = upload(client, headers, "Mon CV.pdf", PDF_BYTES)

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "Mon CV.pdf"
    assert body["content_type"] == cv_service.PDF_CONTENT_TYPE
    assert body["size_bytes"] == len(PDF_BYTES)

    files = stored_files(upload_dir)
    assert len(files) == 1
    assert files[0].parent.name == user_id  # rattaché à l'espace du candidat
    assert files[0].name != "Mon CV.pdf"  # never stored under the user's file name
    assert files[0].read_bytes() == PDF_BYTES


def test_upload_docx(client: TestClient) -> None:
    response = upload(client, auth_headers(client), "cv.DOCX", DOCX_BYTES)

    assert response.status_code == 201
    assert response.json()["content_type"] == cv_service.DOCX_CONTENT_TYPE


def test_new_upload_replaces_previous_cv(client: TestClient, upload_dir: Path) -> None:
    headers = auth_headers(client)
    upload(client, headers, "ancien.pdf", PDF_BYTES)

    response = upload(client, headers, "nouveau.docx", DOCX_BYTES)

    assert response.status_code == 201
    assert client.get("/api/cv/me", headers=headers).json()["original_filename"] == "nouveau.docx"
    files = stored_files(upload_dir)
    assert len(files) == 1
    assert files[0].read_bytes() == DOCX_BYTES


def test_upload_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/cv", files={"file": ("cv.pdf", PDF_BYTES)})

    assert response.status_code == 401


# --- Vérification du format et de la taille ----------------------------------


@pytest.mark.parametrize("filename", ["cv.txt", "cv.doc", "cv.png", "cv"])
def test_rejects_other_extensions(client: TestClient, upload_dir: Path, filename: str) -> None:
    response = upload(client, auth_headers(client), filename, PDF_BYTES)

    assert response.status_code == 415
    assert stored_files(upload_dir) == []


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("cv.pdf", b"just some text renamed to .pdf"),
        ("cv.docx", b"not a zip at all"),
        ("cv.docx", make_docx(("xl/workbook.xml",))),  # an .xlsx renamed to .docx
        ("cv.pdf", DOCX_BYTES),  # extension and content don't match
    ],
)
def test_rejects_content_that_does_not_match_extension(
    client: TestClient, upload_dir: Path, filename: str, content: bytes
) -> None:
    response = upload(client, auth_headers(client), filename, content)

    assert response.status_code == 415
    assert stored_files(upload_dir) == []


def test_rejects_file_over_max_size(client: TestClient, upload_dir: Path) -> None:
    too_big = PDF_BYTES + b"0" * MAX_BYTES

    response = upload(client, auth_headers(client), "cv.pdf", too_big)

    assert response.status_code == 413
    assert f"{MAX_MB} Mo" in response.json()["detail"]
    assert stored_files(upload_dir) == []


def test_accepts_file_exactly_at_max_size(client: TestClient) -> None:
    at_limit = PDF_BYTES + b"0" * (MAX_BYTES - len(PDF_BYTES))

    response = upload(client, auth_headers(client), "cv.pdf", at_limit)

    assert response.status_code == 201


def test_rejects_empty_file(client: TestClient) -> None:
    response = upload(client, auth_headers(client), "cv.pdf", b"")

    assert response.status_code == 400


def test_failed_upload_keeps_previous_cv(client: TestClient, upload_dir: Path) -> None:
    headers = auth_headers(client)
    upload(client, headers, "bon.pdf", PDF_BYTES)

    upload(client, headers, "mauvais.txt", b"hello")

    assert client.get("/api/cv/me", headers=headers).json()["original_filename"] == "bon.pdf"
    assert len(stored_files(upload_dir)) == 1


# --- Consultation, téléchargement, suppression -------------------------------


def test_get_my_cv_returns_404_when_none(client: TestClient) -> None:
    response = client.get("/api/cv/me", headers=auth_headers(client))

    assert response.status_code == 404


def test_download_returns_original_file(client: TestClient) -> None:
    headers = auth_headers(client)
    upload(client, headers, "Mon CV é.pdf", PDF_BYTES)

    response = client.get("/api/cv/me/file", headers=headers)

    assert response.status_code == 200
    assert response.content == PDF_BYTES
    assert response.headers["content-type"] == cv_service.PDF_CONTENT_TYPE
    assert "filename*=UTF-8''Mon%20CV%20%C3%A9.pdf" in response.headers["content-disposition"]


def test_delete_removes_record_and_file(client: TestClient, upload_dir: Path) -> None:
    headers = auth_headers(client)
    upload(client, headers, "cv.pdf", PDF_BYTES)

    assert client.delete("/api/cv/me", headers=headers).status_code == 204
    assert client.get("/api/cv/me", headers=headers).status_code == 404
    assert stored_files(upload_dir) == []
    assert client.delete("/api/cv/me", headers=headers).status_code == 404


def test_candidates_only_see_their_own_cv(client: TestClient) -> None:
    alice = auth_headers(client, "alice@example.com")
    bob = auth_headers(client, "bob@example.com")
    upload(client, alice, "alice.pdf", PDF_BYTES)

    assert client.get("/api/cv/me", headers=bob).status_code == 404
    assert client.get("/api/cv/me/file", headers=bob).status_code == 404
    assert client.delete("/api/cv/me", headers=bob).status_code == 404
    assert client.get("/api/cv/me", headers=alice).status_code == 200


# --- Storage -----------------------------------------------------------------


def test_local_storage_refuses_keys_outside_root(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path / "uploads")

    with pytest.raises(ValueError):
        storage.save("../escape.pdf", PDF_BYTES)


def test_clean_filename_strips_client_paths() -> None:
    assert cv_service._clean_filename("C:\\Users\\me\\Desktop\\cv.pdf") == "cv.pdf"
    assert cv_service._clean_filename("/home/me/cv.docx") == "cv.docx"
    long_name = "a" * 300 + ".pdf"
    assert len(cv_service._clean_filename(long_name)) == 255
    assert cv_service._clean_filename(long_name).endswith(".pdf")
