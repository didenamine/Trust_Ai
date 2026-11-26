"""Business logic for US01 (inscription, connexion, réinitialisation du mot de passe)."""

import uuid

import jwt
from sqlalchemy.orm import Session

from app.core.security import (
    PASSWORD_RESET_TOKEN_TYPE,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    """Raised when registering with an e-mail that already has an account."""


class InvalidCredentialsError(Exception):
    """Raised when login fails (unknown e-mail, wrong password, or inactive account)."""


class InvalidResetTokenError(Exception):
    """Raised when a password-reset token is missing, malformed, expired or already used."""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, *, email: str, password: str, full_name: str | None) -> User:
    email = _normalize_email(email)
    if db.query(User).filter(User.email == email).first() is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    email = _normalize_email(email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError(email)
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def update_account(db: Session, user: User, *, updates: dict) -> User:
    """US02: apply only the fields present in `updates` (see `UserUpdate`)."""
    if "email" in updates:
        new_email = _normalize_email(updates["email"])
        already_taken = (
            db.query(User).filter(User.email == new_email, User.id != user.id).first() is not None
        )
        if new_email != user.email and already_taken:
            raise EmailAlreadyRegisteredError(new_email)
        user.email = new_email
    if "full_name" in updates:
        user.full_name = updates["full_name"]

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, *, current_password: str, new_password: str) -> User:
    """US02: the candidate must know their current password to set a new one."""
    if not verify_password(current_password, user.hashed_password):
        raise InvalidCredentialsError(user.email)

    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_account(db: Session, user: User) -> None:
    """US02: delete the account. Owned data (CV, profile, saved offers, ATS results)
    cascades at the database level (see each model's `ForeignKey(..., ondelete="CASCADE")`)."""
    db.delete(user)
    db.commit()


def create_password_reset(db: Session, *, email: str) -> str | None:
    """Return a reset token if the e-mail matches an account, else None.

    The caller must respond the same way in both cases, so this does not leak
    which e-mails are registered.
    """
    user = db.query(User).filter(User.email == _normalize_email(email)).first()
    if user is None:
        return None
    return create_password_reset_token(str(user.id))


def reset_password(db: Session, *, token: str, new_password: str) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise InvalidResetTokenError() from exc

    if payload.get("type") != PASSWORD_RESET_TOKEN_TYPE:
        raise InvalidResetTokenError()

    try:
        user = get_user_by_id(db, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise InvalidResetTokenError() from exc

    if user is None:
        raise InvalidResetTokenError()

    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
