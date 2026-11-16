import logging
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Classe base para todos os modelos relacionais SQLAlchemy."""


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Retorna a engine SQLAlchemy (criada sob demanda)."""
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise ConfigurationError(
                "Banco não configurado. Defina DB_HOST e DB_PASSWORD (ou DATABASE_URL) no .env."
            )
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session_local() -> sessionmaker[Session]:
    """Retorna a factory de sessões SQLAlchemy."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI para prover uma sessão de banco por requisição."""
    session_factory = get_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Inicializa as tabelas relacionais e garante o índice GIN no cmetadata
    da tabela vetorial do PGVector, caso ela já exista.
    """
    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URL não configurada; criação automática de tabelas ignorada.")
        return

    # Importa todos os modelos para registrá-los no metadata antes de create_all
    import app.modules.news.models  # noqa: F401
    import app.modules.rag_chat.models  # noqa: F401
    import app.modules.users.models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Migração idempotente caso a tabela users tenha sido criada na versão anterior (Google OAuth)
    try:
        with engine.begin() as conn:
            users_exists = conn.execute(
                text("SELECT to_regclass('users') IS NOT NULL;")
            ).scalar()
            if users_exists:
                conn.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL DEFAULT '';"
                    )
                )
                conn.execute(
                    text("ALTER TABLE users DROP COLUMN IF EXISTS google_sub;")
                )
    except Exception as exc:
        logger.warning("Não foi possível verificar/migrar colunas da tabela users: %s", exc)

    try:
        with engine.begin() as conn:
            table_exists = conn.execute(
                text("SELECT to_regclass('langchain_pg_embedding') IS NOT NULL;")
            ).scalar()
            if table_exists:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_cmetadata_gin "
                        "ON langchain_pg_embedding USING GIN (cmetadata);"
                    )
                )
    except Exception as exc:
        logger.warning("Não foi possível garantir índice GIN em langchain_pg_embedding: %s", exc)

