import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None


class UserUpdate(BaseModel):
    """US02: partial update of the account's personal information.

    A field left out of the request body is left unchanged (see `exclude_unset`
    in the route); sending it explicitly as `null` clears it (full_name only).
    """

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestOut(BaseModel):
    """Always returns 200 with the same message, whether or not the e-mail exists.

    Hors périmètre US01 (vérification d'e-mail) : il n'y a pas encore de serveur de
    mail. En dehors de l'environnement de production, le jeton est donc renvoyé
    directement pour permettre de tester le flux sans boîte mail.
    """

    detail: str
    reset_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
