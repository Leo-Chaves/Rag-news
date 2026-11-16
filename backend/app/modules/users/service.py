from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import verify_password
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreateDTO, UserRead, UserUpdate


class UserService:
    """Regras de negócio e fachada pública do módulo de usuários."""

    @staticmethod
    def register_user(db: Session, dto: UserCreateDTO) -> UserRead:
        normalized_email = dto.email.strip().lower()
        existing = UserRepository.get_by_email(db, normalized_email)
        if existing is not None:
            raise ConflictError("Já existe uma conta cadastrada com este e-mail.")

        created = UserRepository.create(
            db,
            email=normalized_email,
            password_hash=dto.password_hash,
            name=dto.name.strip() if dto.name else None,
        )
        return UserRead.model_validate(created)

    @staticmethod
    def verify_credentials(db: Session, email: str, plain_password: str) -> UserRead:
        normalized_email = (email or "").strip().lower()
        user = UserRepository.get_by_email(db, normalized_email)
        if user is None or not verify_password(plain_password, user.password_hash):
            raise UnauthorizedError("E-mail ou senha inválidos.")
        if not user.is_active:
            raise ForbiddenError("Conta de usuário desativada.")
        return UserRead.model_validate(user)

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
