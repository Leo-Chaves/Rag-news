from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users.schemas import UserRead, UserUpdate
from app.modules.users.service import UserService
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def get_my_profile(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Retorna o perfil completo do usuário autenticado."""
    return UserService.get_by_id(db, current_user.id)


@router.patch("/me", response_model=UserRead)
def update_my_profile(
    payload: UserUpdate,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Atualiza informações de perfil do usuário autenticado."""
    return UserService.update_user(db, current_user.id, payload)
