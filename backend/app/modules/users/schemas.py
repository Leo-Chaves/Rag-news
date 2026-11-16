from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    """Representação de saída pública do usuário."""

    id: UUID
    email: str
    name: str | None = None
    picture_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateDTO(BaseModel):
    """Contrato de entrada usado pelo módulo auth para criar um novo usuário."""

    email: str
    password_hash: str
    name: str | None = None


class UserUpdate(BaseModel):
    """Campos editáveis do perfil do usuário."""

    name: str | None = None
    picture_url: str | None = None
