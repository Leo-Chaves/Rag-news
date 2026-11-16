from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.shared.contracts import CurrentUserDTO

bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUserDTO | None:
    """
    Extrai e valida o usuário autenticado a partir do token Bearer JWT.
    Retorna None quando o cabeçalho Authorization não é enviado.
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
        email = str(payload["email"])
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload do token JWT inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentUserDTO(
        id=user_id,
        email=email,
        name=payload.get("name"),
        picture_url=payload.get("picture_url"),
    )


def get_current_user(
    user: CurrentUserDTO | None = Depends(get_optional_user),
) -> CurrentUserDTO:
    """Dependência obrigatória para rotas privadas; exige JWT válido."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória. Faça login via Google OAuth.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
