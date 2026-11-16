from typing import Literal
from uuid import UUID

from pydantic import BaseModel

VectorScope = Literal["global", "saved", "custom", "personal_all"]


class CurrentUserDTO(BaseModel):
    """Representação pública do usuário autenticado compartilhada entre módulos."""

    id: UUID
    email: str
    name: str | None = None
    picture_url: str | None = None

