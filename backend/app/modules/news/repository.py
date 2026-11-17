import logging
from datetime import datetime
from uuid import UUID

import psycopg
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConfigurationError, ExternalServiceError
from app.core.vector_store import reset_vector_store_state
from app.modules.news.models import CustomSource, SavedNews

logger = logging.getLogger(__name__)

_ALLOWED_METADATA_KEYS = {"saved_news_id", "custom_source_id"}


class NewsRepository:
    """Persistência relacional (SavedNews, CustomSource) e operações diretas no PGVector."""

    # -----------------------------------------------------------------------
    # SavedNews
    # -----------------------------------------------------------------------

    @staticmethod
    def get_saved_by_id_and_user(db: Session, news_id: UUID, user_id: UUID) -> SavedNews | None:
        return db.scalar(
            select(SavedNews).where(SavedNews.id == news_id, SavedNews.user_id == user_id)
        )

    @staticmethod
    def get_saved_by_url_and_user(db: Session, url: str, user_id: UUID) -> SavedNews | None:
        return db.scalar(
            select(SavedNews).where(SavedNews.url == url, SavedNews.user_id == user_id)
        )

    @staticmethod
    def list_saved_by_user(db: Session, user_id: UUID) -> list[SavedNews]:
        return list(
            db.scalars(
                select(SavedNews)
                .where(SavedNews.user_id == user_id)
                .order_by(SavedNews.saved_at.desc())
            ).all()
        )

    @staticmethod
    def create_saved(db: Session, *, commit: bool = True, **fields: object) -> SavedNews:
        item = SavedNews(**fields)
        db.add(item)
        if commit:
            db.commit()
            db.refresh(item)
        else:
            db.flush()
        return item

    @staticmethod
    def delete_saved(db: Session, saved_news: SavedNews) -> None:
        db.delete(saved_news)
        db.commit()

    # -----------------------------------------------------------------------
    # CustomSource
    # -----------------------------------------------------------------------

    @staticmethod
    def get_source_by_id_and_user(db: Session, source_id: UUID, user_id: UUID) -> CustomSource | None:
        return db.scalar(
            select(CustomSource).where(
                CustomSource.id == source_id,
                CustomSource.user_id == user_id,
            )
        )

    @staticmethod
    def find_duplicate_source(
        db: Session,
        *,
        user_id: UUID,
        source_type: str,
        url: str | None,
        topic_keywords: str | None,
    ) -> CustomSource | None:
        stmt = select(CustomSource).where(
            CustomSource.user_id == user_id,
            CustomSource.source_type == source_type,
        )
        if source_type in ("rss_feed", "article_url"):
            stmt = stmt.where(CustomSource.url == url)
        else:
            stmt = stmt.where(CustomSource.topic_keywords == topic_keywords)
        return db.scalar(stmt)

    @staticmethod
    def list_sources_by_user(db: Session, user_id: UUID) -> list[CustomSource]:
        return list(
            db.scalars(
                select(CustomSource)
                .where(CustomSource.user_id == user_id)
                .order_by(CustomSource.created_at.desc())
            ).all()
        )

    @staticmethod
    def create_source(db: Session, **fields: object) -> CustomSource:
        source = CustomSource(**fields)
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def update_source_last_synced(
        db: Session, source: CustomSource, synced_at: datetime
    ) -> CustomSource:
        source.last_synced_at = synced_at
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def delete_source(db: Session, source: CustomSource) -> None:
        db.delete(source)
        db.commit()

    # -----------------------------------------------------------------------
    # PGVector / psycopg
    # -----------------------------------------------------------------------

    @staticmethod
    def get_existing_sources(
        scope: str = "global",
        user_id: str | None = None,
        custom_source_id: str | None = None,
    ) -> set[str]:
        """Consulta links já ingeridos na coleção PGVector para deduplicação por escopo."""
        if not settings.DATABASE_URL:
            return set()

        try:
            with psycopg.connect(settings.psycopg_conn_str) as conn:
                with conn.cursor() as cur:
                    if scope == "global":
                        cur.execute(
                            """
                            SELECT DISTINCT e.cmetadata->>'source'
                            FROM langchain_pg_embedding e
                            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                            WHERE c.name = %s
                              AND e.cmetadata->>'source' IS NOT NULL
                              AND (e.cmetadata->>'scope' = 'global' OR e.cmetadata->>'scope' IS NULL)
                            """,
                            (settings.COLLECTION_NAME,),
                        )
                    elif custom_source_id is not None:
                        cur.execute(
                            """
                            SELECT DISTINCT e.cmetadata->>'source'
                            FROM langchain_pg_embedding e
                            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                            WHERE c.name = %s
                              AND e.cmetadata->>'source' IS NOT NULL
                              AND e.cmetadata->>'scope' = %s
                              AND e.cmetadata->>'user_id' = %s
                              AND e.cmetadata->>'custom_source_id' = %s
                            """,
                            (settings.COLLECTION_NAME, scope, user_id, custom_source_id),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT DISTINCT e.cmetadata->>'source'
                            FROM langchain_pg_embedding e
                            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                            WHERE c.name = %s
                              AND e.cmetadata->>'source' IS NOT NULL
                              AND e.cmetadata->>'scope' = %s
                              AND e.cmetadata->>'user_id' = %s
                            """,
                            (settings.COLLECTION_NAME, scope, user_id),
                        )
                    return {row[0] for row in cur.fetchall() if row[0]}
        except psycopg.errors.UndefinedTable:
            # Primeira ingestão: o PGVector ainda não criou as tabelas.
            logger.info("Tabelas do PGVector ainda não existem; nada a deduplicar.")
            return set()
        except Exception as exc:
            # Devolver set() aqui faria a ingestão regravar todas as notícias
            # (duplicando o acervo e gastando a cota de embeddings). Melhor abortar.
            logger.error("Falha ao consultar fontes existentes para deduplicação: %s", exc)
            raise ExternalServiceError(
                "Não foi possível verificar as notícias já indexadas; ingestão cancelada "
                "para evitar duplicatas. Tente novamente."
            ) from exc

    @staticmethod
    def delete_embeddings_by_metadata(
        user_id: str, metadata_key: str, metadata_value: str
    ) -> int:
        """Remove chunks vetoriais pertencentes a uma notícia ou fonte do usuário."""
        if metadata_key not in _ALLOWED_METADATA_KEYS:
            raise ValueError(f"Chave de metadado não permitida para exclusão: {metadata_key}")

        if not settings.DATABASE_URL:
            return 0

        try:
            with psycopg.connect(settings.psycopg_conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM langchain_pg_embedding e
                        USING langchain_pg_collection c
                        WHERE e.collection_id = c.uuid
                          AND c.name = %s
                          AND e.cmetadata->>'user_id' = %s
                          AND e.cmetadata->>%s = %s
                        """,
                        (settings.COLLECTION_NAME, user_id, metadata_key, metadata_value),
                    )
                    deleted = cur.rowcount or 0
                    conn.commit()
                    return deleted
        except Exception as exc:
            logger.warning("Não foi possível remover embeddings (%s=%s): %s", metadata_key, metadata_value, exc)
            return 0

    @staticmethod
    def reset_pgvector_tables() -> None:
        """Remove tabelas do PGVector para permitir recriação após mudança de dimensão."""
        if not settings.DATABASE_URL:
            raise ConfigurationError("DATABASE_URL não configurada.")

        try:
            with psycopg.connect(settings.psycopg_conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("DROP TABLE IF EXISTS langchain_pg_embedding CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS langchain_pg_collection CASCADE;")
                    conn.commit()
            reset_vector_store_state()
            logger.info("Tabelas de embeddings resetadas com sucesso.")
        except Exception as exc:
            logger.error("Erro ao resetar tabelas: %s", exc)
            raise ExternalServiceError(f"Erro ao resetar banco: {exc}") from exc

