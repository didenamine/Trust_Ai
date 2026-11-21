from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestOut,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])

_RESET_REQUESTED_MESSAGE = (
    "Si un compte existe avec cet e-mail, un lien de réinitialisation a été envoyé."
)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    try:
        return auth_service.register_user(
            db, email=payload.email, password=payload.password, full_name=payload.full_name
        )
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail"
        ) from exc


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    try:
        user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "E-mail ou mot de passe incorrect"
        ) from exc

    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """US02: update personal information (only the fields sent are changed)."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        return auth_service.update_account(db, current_user, updates=updates)
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail"
        ) from exc


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """US02: change the password; the current one must be provided."""
    try:
        auth_service.change_password(
            db,
            current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe actuel incorrect") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """US02: delete the account and all of its owned data."""
    auth_service.delete_account(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/request", response_model=PasswordResetRequestOut)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> PasswordResetRequestOut:
    token = auth_service.create_password_reset(db, email=payload.email)

    # Pas encore de serveur de mail (US01) : le jeton est renvoyé hors production
    # pour que le flux reste testable de bout en bout.
    if get_settings().environment == "production":
        return PasswordResetRequestOut(detail=_RESET_REQUESTED_MESSAGE)
    return PasswordResetRequestOut(detail=_RESET_REQUESTED_MESSAGE, reset_token=token)


@router.post("/password-reset/confirm", response_model=UserOut)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> User:
    try:
        return auth_service.reset_password(
            db, token=payload.token, new_password=payload.new_password
        )
    except auth_service.InvalidResetTokenError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Jeton de réinitialisation invalide ou expiré"
        ) from exc
