from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.users.schemas import UserCreateDTO, UserRead
from app.modules.users.service import UserService


class AuthService:
    """Orquestra cadastro, login por credenciais e emissão da sessão JWT."""

    @staticmethod
    def _issue_token_response(user: UserRead) -> TokenResponse:
        access_token, expires_in = create_access_token(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
        )
        return TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            user=user,
        )

    @staticmethod
    def register(db: Session, payload: RegisterRequest) -> TokenResponse:
        dto = UserCreateDTO(
            email=payload.email,
            password_hash=hash_password(payload.password),
            name=payload.name,
        )
        user = UserService.register_user(db, dto)
        return AuthService._issue_token_response(user)

    @staticmethod
    def login(db: Session, payload: LoginRequest) -> TokenResponse:
        user = UserService.verify_credentials(db, payload.email, payload.password)
        return AuthService._issue_token_response(user)
