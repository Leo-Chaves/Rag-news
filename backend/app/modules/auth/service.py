from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_google_token
from app.modules.auth.schemas import TokenResponse
from app.modules.users.schemas import GoogleUserUpsertDTO
from app.modules.users.service import UserService


class AuthService:
    """Orquestra a validação do token Google e a emissão da sessão JWT."""

    @staticmethod
    def authenticate_with_google(db: Session, raw_token: str) -> TokenResponse:
        google_info = verify_google_token(raw_token)
        upsert_dto = GoogleUserUpsertDTO(
            google_sub=str(google_info["sub"]),
            email=str(google_info["email"]),
            name=google_info.get("name"),
            picture_url=google_info.get("picture"),
        )
        user = UserService.get_or_create_google_user(db, upsert_dto)
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
