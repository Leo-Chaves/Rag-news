from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConfigurationError, NotFoundError, UnauthorizedError
from app.modules.rag_chat.graph.workflow import grafo_rag
from app.modules.rag_chat.repository import ChatRepository
from app.modules.rag_chat.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSessionRead,
    ChatSessionWithMessagesRead,
)
from app.shared.contracts import CurrentUserDTO


class RagChatService:
    """Orquestra execução do grafo RAG com isolamento por usuário e histórico."""

    @staticmethod
    def _ensure_configured() -> None:
        if not settings.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada no .env. Obtenha sua chave em https://openrouter.ai/keys"
            )
        if not settings.DATABASE_URL:
            raise ConfigurationError(
                "Banco não configurado. Defina DB_HOST e DB_PASSWORD no .env."
            )

    @staticmethod
    def ask_question(
        db: Session | None,
        payload: ChatRequest,
        current_user: CurrentUserDTO | None,
    ) -> ChatResponse:
        RagChatService._ensure_configured()

        if payload.scope != "global" and current_user is None:
            raise UnauthorizedError(
                "Autenticação via Google OAuth é obrigatória para consultar notícias salvas ou personalizadas."
            )

        if payload.session_id is not None and current_user is None:
            raise UnauthorizedError(
                "Autenticação obrigatória para continuar uma sessão de chat existente."
            )

        session = None
        if current_user is not None and db is not None and payload.session_id is not None:
            session = ChatRepository.get_session_by_id_and_user(
                db, payload.session_id, current_user.id
            )
            if session is None:
                raise NotFoundError("Sessão de chat não encontrada.")

        resultado = grafo_rag.invoke(
            {
                "pergunta": payload.question,
                "top_k": payload.top_k,
                "scope": payload.scope,
                "user_id": str(current_user.id) if current_user else None,
                "custom_source_id": str(payload.custom_source_id) if payload.custom_source_id else None,
            }
        )

        docs = resultado.get("documentos_recuperados", [])
        sources = list(
            dict.fromkeys(
                doc.metadata.get("source", "")
                for doc in docs
                if doc.metadata.get("source")
            )
        )
        answer = resultado["resposta"]

        session_id: UUID | None = None
        if current_user is not None and db is not None:
            if session is None:
                title = payload.question[:60]
                session = ChatRepository.create_session(
                    db,
                    user_id=current_user.id,
                    title=title,
                    default_scope=payload.scope,
                )
            ChatRepository.add_message(
                db,
                session=session,
                role="user",
                content=payload.question,
                sources=[],
            )
            ChatRepository.add_message(
                db,
                session=session,
                role="assistant",
                content=answer,
                sources=sources,
            )
            session_id = session.id

        return ChatResponse(
            answer=answer,
            sources=sources,
            scope=payload.scope,
            session_id=session_id,
        )

    @staticmethod
    def list_sessions(db: Session, current_user: CurrentUserDTO) -> list[ChatSessionRead]:
        sessions = ChatRepository.list_sessions_by_user(db, current_user.id)
        return [ChatSessionRead.model_validate(s) for s in sessions]

    @staticmethod
    def get_session_detail(
        db: Session, current_user: CurrentUserDTO, session_id: UUID
    ) -> ChatSessionWithMessagesRead:
        session = ChatRepository.get_session_by_id_and_user(
            db, session_id, current_user.id, include_messages=True
        )
        if session is None:
            raise NotFoundError("Sessão de chat não encontrada.")
        return ChatSessionWithMessagesRead.model_validate(session)

    @staticmethod
    def delete_session(
        db: Session, current_user: CurrentUserDTO, session_id: UUID
    ) -> None:
        session = ChatRepository.get_session_by_id_and_user(db, session_id, current_user.id)
        if session is None:
            raise NotFoundError("Sessão de chat não encontrada.")
        ChatRepository.delete_session(db, session)
