import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.core.vector_store import get_vector_store
from app.modules.news.parsers import (
    chunk_single_document,
    extract_article_from_url,
    fetch_and_chunk_rss,
    fetch_rss_feed_entries,
)
from app.modules.news.repository import NewsRepository
from app.modules.news.schemas import (
    CustomSourceCreate,
    CustomSourceRead,
    FeedArticleItem,
    GlobalIngestResponse,
    SavedNewsCreate,
    SavedNewsRead,
    SyncSourceResponse,
)
from app.shared.contracts import CurrentUserDTO

logger = logging.getLogger(__name__)


class NewsService:
    """Regras de negócio de ingestão global, notícias salvas e fontes personalizadas."""

    @staticmethod
    def _ensure_ai_and_db_configured() -> None:
        if not settings.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada no .env. Obtenha sua chave em https://openrouter.ai/keys"
            )
        if not settings.DATABASE_URL:
            raise ConfigurationError("DATABASE_URL não configurada.")

    @staticmethod
    def fetch_global_feed_items(limit: int = 30) -> list[FeedArticleItem]:
        entries = fetch_rss_feed_entries(settings.BBC_RSS_URLS, limit=limit)
        return [FeedArticleItem(**item) for item in entries]

    @staticmethod
    def ingest_global_bbc_feeds() -> GlobalIngestResponse:
        NewsService._ensure_ai_and_db_configured()

        existing = NewsRepository.get_existing_sources(scope="global")
        logger.info("Fontes globais já existentes no banco: %d", len(existing))

        chunks, chunk_metadata, total_articles, skipped = fetch_and_chunk_rss(
            settings.BBC_RSS_URLS,
            existing_sources=existing,
            extra_metadata={"scope": "global"},
        )

        if not chunks:
            if skipped > 0:
                return GlobalIngestResponse(
                    message="Todas as notícias já estão atualizadas no banco.",
                    feeds_processados=len(settings.BBC_RSS_URLS),
                    articles_processed=0,
                    chunks_stored=0,
                    skipped=skipped,
                )
            raise ValidationError("Nenhum conteúdo válido encontrado nos feeds da BBC.")

        try:
            vs = get_vector_store()
            vs.add_texts(texts=chunks, metadatas=chunk_metadata)
        except ConfigurationError:
            raise
        except Exception as exc:
            logger.error("Erro durante add_texts no PGVector: %s", exc)
            raise ExternalServiceError(
                "Erro ao salvar vetores no PGVector. Se você mudou de modelo de embedding "
                f"recentemente, faça uma chamada POST para /reset antes de reingerir: {exc}"
            ) from exc

        return GlobalIngestResponse(
            message="Ingestão dos feeds da BBC concluída com sucesso.",
            feeds_processados=len(settings.BBC_RSS_URLS),
            articles_processed=total_articles,
            chunks_stored=len(chunks),
            skipped=skipped,
        )

    @staticmethod
    def save_news(db: Session, user: CurrentUserDTO, payload: SavedNewsCreate) -> SavedNewsRead:
        NewsService._ensure_ai_and_db_configured()

        clean_url = payload.url.strip()
        if not clean_url.startswith(("http://", "https://")):
            raise ValidationError("URL da notícia inválida; informe http:// ou https://.")

        existing = NewsRepository.get_saved_by_url_and_user(db, clean_url, user.id)
        if existing is not None:
            raise ConflictError("Esta notícia já está salva na sua conta.")

        if payload.custom_source_id is not None:
            source = NewsRepository.get_source_by_id_and_user(db, payload.custom_source_id, user.id)
            if source is None:
                raise NotFoundError("Fonte personalizada informada não encontrada.")

        title = (payload.title or "").strip()
        summary = (payload.summary or "").strip()
        content = (payload.content or "").strip()

        if not title or (not summary and not content):
            extracted = extract_article_from_url(clean_url)
            title = title or extracted["title"]
            summary = summary or extracted["summary"]
            content = content or extracted["content"]

        text_to_index = content or summary or title
        try:
            saved = NewsRepository.create_saved(
                db,
                commit=False,
                user_id=user.id,
                custom_source_id=payload.custom_source_id,
                title=title,
                summary=summary or None,
                content=content or summary or None,
                url=clean_url,
                published_at=payload.published_at,
                origin=payload.origin,
                is_indexed=False,
            )

            chunks, metadatas = chunk_single_document(
                title=saved.title,
                text=text_to_index,
                metadata={
                    "source": saved.url,
                    "title": saved.title,
                    "published": saved.published_at or "",
                    "scope": "saved",
                    "user_id": str(user.id),
                    "saved_news_id": str(saved.id),
                },
            )
            if chunks:
                vs = get_vector_store()
                vs.add_texts(texts=chunks, metadatas=metadatas)
                saved.is_indexed = True

            db.commit()
            db.refresh(saved)
            return SavedNewsRead.model_validate(saved)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list_saved_news(db: Session, user: CurrentUserDTO) -> list[SavedNewsRead]:
        items = NewsRepository.list_saved_by_user(db, user.id)
        return [SavedNewsRead.model_validate(item) for item in items]

    @staticmethod
    def delete_saved_news(db: Session, user: CurrentUserDTO, news_id: UUID) -> None:
        saved = NewsRepository.get_saved_by_id_and_user(db, news_id, user.id)
        if saved is None:
            raise NotFoundError("Notícia salva não encontrada.")

        NewsRepository.delete_embeddings_by_metadata(
            user_id=str(user.id),
            metadata_key="saved_news_id",
            metadata_value=str(saved.id),
        )
        NewsRepository.delete_saved(db, saved)

    @staticmethod
    def create_custom_source(
        db: Session, user: CurrentUserDTO, payload: CustomSourceCreate
    ) -> CustomSourceRead:
        duplicate = NewsRepository.find_duplicate_source(
            db,
            user_id=user.id,
            source_type=payload.source_type,
            url=payload.url,
            topic_keywords=payload.topic_keywords,
        )
        if duplicate is not None:
            raise ConflictError("Esta fonte personalizada já está cadastrada na sua conta.")

        source = NewsRepository.create_source(
            db,
            user_id=user.id,
            source_type=payload.source_type,
            name=payload.name.strip(),
            url=payload.url,
            topic_keywords=payload.topic_keywords,
        )
        return CustomSourceRead.model_validate(source)

    @staticmethod
    def list_custom_sources(db: Session, user: CurrentUserDTO) -> list[CustomSourceRead]:
        sources = NewsRepository.list_sources_by_user(db, user.id)
        return [CustomSourceRead.model_validate(src) for src in sources]

    @staticmethod
    def sync_custom_source(
        db: Session, user: CurrentUserDTO, source_id: UUID
    ) -> SyncSourceResponse:
        NewsService._ensure_ai_and_db_configured()

        source = NewsRepository.get_source_by_id_and_user(db, source_id, user.id)
        if source is None:
            raise NotFoundError("Fonte personalizada não encontrada.")

        existing = NewsRepository.get_existing_sources(
            scope="custom",
            user_id=str(user.id),
            custom_source_id=str(source.id),
        )

        base_meta = {
            "scope": "custom",
            "user_id": str(user.id),
            "custom_source_id": str(source.id),
        }

        if source.source_type == "rss_feed":
            chunks, chunk_metadata, total_articles, skipped = fetch_and_chunk_rss(
                [source.url or ""],
                existing_sources=existing,
                extra_metadata=base_meta,
            )
        elif source.source_type == "article_url":
            article_url = source.url or ""
            if article_url in existing:
                NewsRepository.update_source_last_synced(db, source, datetime.now(timezone.utc))
                return SyncSourceResponse(
                    source_id=source.id,
                    articles_processed=0,
                    chunks_stored=0,
                    skipped=1,
                    message="Artigo desta fonte já está indexado.",
                )

            extracted = extract_article_from_url(article_url)
            chunks, chunk_metadata = chunk_single_document(
                title=extracted["title"],
                text=extracted["content"],
                metadata={
                    "source": article_url,
                    "title": extracted["title"],
                    "published": "",
                    **base_meta,
                },
            )
            total_articles = 1 if chunks else 0
            skipped = 0
        else:
            user_rss_urls = [
                src.url
                for src in NewsRepository.list_sources_by_user(db, user.id)
                if src.is_active and src.source_type == "rss_feed" and src.url
            ]
            all_feed_urls = list(dict.fromkeys(user_rss_urls + settings.BBC_RSS_URLS))
            chunks, chunk_metadata, total_articles, skipped = fetch_and_chunk_rss(
                all_feed_urls,
                existing_sources=existing,
                extra_metadata={**base_meta, "topic": source.topic_keywords or ""},
                topic_keywords=source.topic_keywords,
            )

        if chunks:
            try:
                vs = get_vector_store()
                vs.add_texts(texts=chunks, metadatas=chunk_metadata)
            except ConfigurationError:
                raise
            except Exception as exc:
                raise ExternalServiceError(
                    f"Erro ao indexar vetores da fonte personalizada no PGVector: {exc}"
                ) from exc

        NewsRepository.update_source_last_synced(db, source, datetime.now(timezone.utc))

        message = (
            "Sincronização concluída com sucesso."
            if chunks
            else "Nenhum artigo novo encontrado para indexar nesta fonte."
        )
        return SyncSourceResponse(
            source_id=source.id,
            articles_processed=total_articles,
            chunks_stored=len(chunks),
            skipped=skipped,
            message=message,
        )

    @staticmethod
    def delete_custom_source(db: Session, user: CurrentUserDTO, source_id: UUID) -> None:
        source = NewsRepository.get_source_by_id_and_user(db, source_id, user.id)
        if source is None:
            raise NotFoundError("Fonte personalizada não encontrada.")

        NewsRepository.delete_embeddings_by_metadata(
            user_id=str(user.id),
            metadata_key="custom_source_id",
            metadata_value=str(source.id),
        )
        NewsRepository.delete_source(db, source)

