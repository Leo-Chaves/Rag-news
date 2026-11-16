from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.auth.service import AuthService
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserService
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Cadastra uma nova conta com e-mail e senha e retorna o JWT de sessão."""
    return AuthService.register(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Autentica o usuário por e-mail e senha e retorna o JWT de sessão."""
    return AuthService.login(db, payload)


@router.get("/me", response_model=UserRead)
def get_authenticated_user(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Valida o token JWT atual e retorna os dados do usuário autenticado."""
    return UserService.get_by_id(db, current_user.id)
