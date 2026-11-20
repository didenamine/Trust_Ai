from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.cv_document import CVDocument
from app.models.user import User
from app.schemas.cv import CVOut
from app.services import cv_service
from app.services.storage import FileStorage, get_storage

router = APIRouter(tags=["cv"])

_NO_CV = HTTPException(status.HTTP_404_NOT_FOUND, "Aucun CV importé")


@router.post("", response_model=CVOut, status_code=status.HTTP_201_CREATED)
def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> CVDocument:
    """Import the candidate's CV (PDF or DOCX). Replaces the previous one if any."""
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    # Read one byte past the limit: enough to know the file is too large
    # without loading an arbitrarily big upload into memory.
    content = file.file.read(max_bytes + 1)

    try:
        return cv_service.save_cv(
            db,
            storage,
            user_id=current_user.id,
            filename=file.filename or "",
            content=content,
            max_bytes=max_bytes,
        )
    except cv_service.EmptyCVError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le fichier est vide") from exc
    except cv_service.CVTooLargeError as exc:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Le fichier dépasse la taille maximale de {settings.max_upload_size_mb} Mo",
        ) from exc
    except cv_service.UnsupportedCVFormatError as exc:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Format non accepté : le fichier doit être un PDF ou un DOCX valide",
        ) from exc


@router.get("/me", response_model=CVOut)
def get_my_cv(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CVDocument:
    cv = cv_service.get_current_cv(db, current_user.id)
    if cv is None:
        raise _NO_CV
    return cv


@router.get("/me/file")
def download_my_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> Response:
    result = cv_service.read_current_cv(db, storage, current_user.id)
    if result is None:
        raise _NO_CV
    cv, content = result
    return Response(
        content=content,
        media_type=cv.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(cv.original_filename)}"
        },
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> Response:
    if not cv_service.delete_cv(db, storage, current_user.id):
        raise _NO_CV
    return Response(status_code=status.HTTP_204_NO_CONTENT)
