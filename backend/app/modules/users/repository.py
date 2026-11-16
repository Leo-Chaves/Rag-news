from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


class UserRepository:
    """Camada de acesso a dados da entidade User."""

    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> User | None:
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    @staticmethod
    def create(
        db: Session,
        *,
        email: str,
        password_hash: str,
        name: str | None = None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(db: Session, user: User, **fields: object) -> User:
        for attr, value in fields.items():
            if hasattr(user, attr):
                setattr(user, attr, value)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
