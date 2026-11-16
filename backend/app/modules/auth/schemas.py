from pydantic import BaseModel

from app.modules.users.schemas import UserRead


class GoogleAuthRequest(BaseModel):
    """
    Payload aceito pelo login Google OAuth 2.0.
    Aceita `credential` (Google Identity Services), `id_token` ou `token` (ID Token / Access Token).
    """

    token: str | None = None
    credential: str | None = None
    id_token: str | None = None

    @property
    def resolved_token(self) -> str:
        for candidate in (self.credential, self.id_token, self.token):
            if candidate and candidate.strip():
                return candidate.strip()
        return ""


class TokenResponse(BaseModel):
    """Resposta padrão de sessão autenticada com JWT."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class AuthConfigResponse(BaseModel):
    """Configurações públicas de autenticação para inicialização do cliente OAuth no frontend."""

    google_client_id: str

