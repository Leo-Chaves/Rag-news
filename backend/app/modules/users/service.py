from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import GoogleUserUpsertDTO, UserRead, UserUpdate


class UserService:
    """Regras de negócio e fachada pública do módulo de usuários."""

    @staticmethod
    def get_or_create_google_user(db: Session, dto: GoogleUserUpsertDTO) -> UserRead:
        user = UserRepository.get_by_google_sub(db, dto.google_sub)
        if user is None:
            user = UserRepository.get_by_email(db, dto.email)

        if user is not None:
            if not user.is_active:
                raise ForbiddenError("Conta de usuário desativada.")

            updates: dict[str, object] = {}
            if user.google_sub != dto.google_sub:
                updates["google_sub"] = dto.google_sub
            if dto.name is not None and user.name != dto.name:
                updates["name"] = dto.name
            if dto.picture_url is not None and user.picture_url != dto.picture_url:
                updates["picture_url"] = dto.picture_url

            if updates:
                user = UserRepository.update(db, user, **updates)
            return UserRead.model_validate(user)

        created = UserRepository.create(
            db,
            google_sub=dto.google_sub,
            email=dto.email,
            name=dto.name,
            picture_url=dto.picture_url,
        )
        return UserRead.model_validate(created)

    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> UserRead:
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        if not user.is_active:
            raise ForbiddenError("Conta de usuário desativada.")
        return UserRead.model_validate(user)

    @staticmethod
    def update_user(db: Session, user_id: UUID, dto: UserUpdate) -> UserRead:
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")

        changes = dto.model_dump(exclude_unset=True)
        if changes:
            user = UserRepository.update(db, user, **changes)
        return UserRead.model_validate(user)
