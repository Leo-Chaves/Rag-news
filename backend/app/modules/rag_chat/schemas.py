from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.contracts import VectorScope


class ChatRequest(BaseModel):
    """Requisição de pergunta ao pipeline RAG."""

    question: str
    scope: VectorScope = "global"
    session_id: UUID | None = None
    custom_source_id: UUID | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def validate_non_empty_question(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("A pergunta não pode estar vazia.")
        return clean


class ChatResponse(BaseModel):
    """Resposta gerada pelo pipeline RAG com fontes recuperadas."""

    answer: str
    sources: list[str] = []
    scope: VectorScope = "global"
    session_id: UUID | None = None


class ChatMessageRead(BaseModel):
    """Representação de leitura de uma mensagem do histórico."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionRead(BaseModel):
    """Resumo de uma sessão de chat do usuário."""

    id: UUID
    user_id: UUID
    title: str
    default_scope: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionWithMessagesRead(ChatSessionRead):
    """Sessão de chat com a lista completa de mensagens."""

    messages: list[ChatMessageRead] = []
