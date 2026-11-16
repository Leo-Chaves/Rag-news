from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.rag_chat.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSessionRead,
    ChatSessionWithMessagesRead,
)
from app.modules.rag_chat.service import RagChatService
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Recebe uma pergunta autenticada, executa o grafo RAG no escopo escolhido
    e registra o histórico da sessão do usuário.
    """
    return RagChatService.ask_question(db, body, current_user)


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSessionRead]:
    """Lista todas as sessões de chat do usuário autenticado."""
    return RagChatService.list_sessions(db, current_user)


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessagesRead)
def get_session(
    session_id: UUID,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionWithMessagesRead:
    """Retorna uma sessão específica com todas as suas mensagens."""
    return RagChatService.get_session_detail(db, current_user, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove uma sessão de chat e todas as suas mensagens."""
    RagChatService.delete_session(db, current_user, session_id)

