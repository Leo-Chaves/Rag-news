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
    def get_by_google_sub(db: Session, google_sub: str) -> User | None:
        return db.scalar(select(User).where(User.google_sub == google_sub))

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    @staticmethod
    def create(
        db: Session,
        *,
        google_sub: str,
        email: str,
        name: str | None = None,
        picture_url: str | None = None,
    ) -> User:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            picture_url=picture_url,
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
