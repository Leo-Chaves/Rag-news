import re

from pydantic import BaseModel, field_validator

from app.modules.users.schemas import UserRead

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_and_validate_email(value: str) -> str:
    clean = (value or "").strip().lower()
    if not _EMAIL_REGEX.match(clean):
        raise ValueError("Informe um e-mail válido.")
    return clean


class RegisterRequest(BaseModel):
    """Payload para cadastro de novo usuário com e-mail e senha."""

    name: str | None = None
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_and_validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value or len(value) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres.")
        if len(value) > 128:
            raise ValueError("A senha deve ter no máximo 128 caracteres.")
        return value


class LoginRequest(BaseModel):
    """Payload para login com e-mail e senha."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_and_validate_email(value)


class TokenResponse(BaseModel):
    """Resposta padrão de sessão autenticada com JWT."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
