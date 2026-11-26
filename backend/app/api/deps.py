"""Shared FastAPI dependencies."""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)

_INVALID_TOKEN = HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _INVALID_TOKEN from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise _INVALID_TOKEN

    try:
        user = get_user_by_id(db, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _INVALID_TOKEN from exc

    if user is None or not user.is_active:
        raise _INVALID_TOKEN

    return user
