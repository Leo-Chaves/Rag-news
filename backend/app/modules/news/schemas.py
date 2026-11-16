from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

NewsOrigin = Literal["global_feed", "custom_source", "external_url"]
CustomSourceType = Literal["rss_feed", "article_url", "topic"]


class FeedArticleItem(BaseModel):
    """Item de notícia retornado do feed global."""

    title: str
    summary: str
    url: str
    published_at: str = ""
    feed_url: str


class SavedNewsCreate(BaseModel):
    """Payload para salvar uma notícia na conta do usuário."""

    url: str
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    published_at: str | None = None
    origin: NewsOrigin = "global_feed"
    custom_source_id: UUID | None = None


class SavedNewsRead(BaseModel):
    """Representação de saída de uma notícia salva."""

    id: UUID
    user_id: UUID
    custom_source_id: UUID | None = None
    title: str
    summary: str | None = None
    content: str | None = None
    url: str
    published_at: str | None = None
    origin: str
    is_indexed: bool
    saved_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomSourceCreate(BaseModel):
    """Payload para cadastrar fonte personalizada do usuário."""

    name: str
    source_type: CustomSourceType
    url: str | None = None
    topic_keywords: str | None = None

    @model_validator(mode="after")
    def validate_source_fields(self) -> "CustomSourceCreate":
        if self.source_type in ("rss_feed", "article_url"):
            clean_url = (self.url or "").strip()
            if not clean_url or not clean_url.startswith(("http://", "https://")):
                raise ValueError("Fontes 'rss_feed' e 'article_url' exigem uma URL http(s) válida.")
            self.url = clean_url
        elif self.source_type == "topic":
            clean_keywords = (self.topic_keywords or "").strip()
            if not clean_keywords:
                raise ValueError("Fontes do tipo 'topic' exigem 'topic_keywords' preenchido.")
            self.topic_keywords = clean_keywords
        return self


class CustomSourceRead(BaseModel):
    """Representação de saída de uma fonte personalizada."""

    id: UUID
    user_id: UUID
    source_type: str
    name: str
    url: str | None = None
    topic_keywords: str | None = None
    is_active: bool
    last_synced_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncSourceResponse(BaseModel):
    """Resultado da sincronização e vetorização de uma fonte personalizada."""

    source_id: UUID
    articles_processed: int
    chunks_stored: int
    skipped: int
    message: str


class GlobalIngestResponse(BaseModel):
    """Resposta compatível com o endpoint legado POST /ingest."""

    message: str
    feeds_processados: int
    articles_processed: int
    chunks_stored: int
    skipped: int
