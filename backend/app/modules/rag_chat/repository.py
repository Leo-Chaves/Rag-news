from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.rag_chat.models import ChatMessage, ChatSession


class ChatRepository:
    """Persistência de sessões e mensagens de chat por usuário."""

    @staticmethod
    def get_session_by_id_and_user(
        db: Session,
        session_id: UUID,
        user_id: UUID,
        *,
        include_messages: bool = False,
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        if include_messages:
            stmt = stmt.options(selectinload(ChatSession.messages))
        return db.scalar(stmt)

    @staticmethod
    def list_sessions_by_user(db: Session, user_id: UUID) -> list[ChatSession]:
        return list(
            db.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc())
            ).all()
        )

    @staticmethod
    def create_session(
        db: Session,
        *,
        user_id: UUID,
        title: str,
        default_scope: str,
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            title=title,
            default_scope=default_scope,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def add_message(
        db: Session,
        *,
        session: ChatSession,
        role: str,
        content: str,
        sources: list[str] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session.id,
            role=role,
            content=content,
            sources=sources or [],
        )
        session.updated_at = datetime.now(timezone.utc)
        db.add(message)
        db.add(session)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def delete_session(db: Session, session: ChatSession) -> None:
        db.delete(session)
        db.commit()
