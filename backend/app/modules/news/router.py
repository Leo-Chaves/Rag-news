from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.news.schemas import (
    CustomSourceCreate,
    CustomSourceRead,
    FeedArticleItem,
    GlobalIngestResponse,
    SavedNewsCreate,
    SavedNewsRead,
    SyncSourceResponse,
)
from app.modules.news.service import NewsService
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/feed", response_model=list[FeedArticleItem])
def list_global_feed(
    limit: int = Query(default=60, ge=1, le=150),
    _current_user: CurrentUserDTO = Depends(get_current_user),
) -> list[FeedArticleItem]:
    """Lista artigos recentes dos feeds RSS globais (Brasil PT-BR, Tech e BBC)."""
    return NewsService.fetch_global_feed_items(limit=limit)


@router.post("/ingest", response_model=GlobalIngestResponse)
def ingest_global_feed(
    _current_user: CurrentUserDTO = Depends(get_current_user),
) -> GlobalIngestResponse:
    """Executa ingestão dos feeds globais da BBC no PGVector."""
    return NewsService.ingest_global_bbc_feeds()


@router.get("/saved", response_model=list[SavedNewsRead])
def list_saved_news(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedNewsRead]:
    """Lista todas as notícias salvas pelo usuário autenticado."""
    return NewsService.list_saved_news(db, current_user)


@router.post("/saved", response_model=SavedNewsRead, status_code=status.HTTP_201_CREATED)
def save_news(
    payload: SavedNewsCreate,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedNewsRead:
    """Salva uma notícia na conta do usuário e indexa seus embeddings com isolamento."""
    return NewsService.save_news(db, current_user, payload)


@router.delete("/saved/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_news(
    news_id: UUID,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove uma notícia salva e seus respectivos chunks vetoriais."""
    NewsService.delete_saved_news(db, current_user, news_id)


@router.get("/sources", response_model=list[CustomSourceRead])
def list_custom_sources(
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CustomSourceRead]:
    """Lista as fontes personalizadas cadastradas pelo usuário."""
    return NewsService.list_custom_sources(db, current_user)


@router.post("/sources", response_model=CustomSourceRead, status_code=status.HTTP_201_CREATED)
def create_custom_source(
    payload: CustomSourceCreate,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CustomSourceRead:
    """Cadastra uma nova fonte personalizada (RSS, artigo direto ou tópico)."""
    return NewsService.create_custom_source(db, current_user, payload)


@router.post("/sources/{source_id}/sync", response_model=SyncSourceResponse)
def sync_custom_source(
    source_id: UUID,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncSourceResponse:
    """Ingere e indexa os conteúdos de uma fonte personalizada no acervo do usuário."""
    return NewsService.sync_custom_source(db, current_user, source_id)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_source(
    source_id: UUID,
    current_user: CurrentUserDTO = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove uma fonte personalizada e todos os vetores associados a ela."""
    NewsService.delete_custom_source(db, current_user, source_id)

