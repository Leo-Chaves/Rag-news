from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.schemas import AuthConfigResponse, GoogleAuthRequest, TokenResponse
from app.modules.auth.service import AuthService
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserService
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/config", response_model=AuthConfigResponse)
def get_auth_config() -> AuthConfigResponse:
    """Retorna o Google Client ID público configurado no backend."""
    return AuthConfigResponse(google_client_id=settings.GOOGLE_CLIENT_ID)


@router.post("/google", response_model=TokenResponse)
def google_login(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Autentica ou registra o usuário exclusivamente via Google OAuth 2.0 e retorna um JWT."""
    return AuthService.authenticate_with_google(db, payload.resolved_token)


@router.get("/me", response_model=UserRead)
def get_authenticated_user(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Valida o token JWT atual e retorna os dados do usuário autenticado."""
    return UserService.get_by_id(db, current_user.id)

