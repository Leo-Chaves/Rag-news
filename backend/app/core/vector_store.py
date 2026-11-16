import logging

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector as PGVectorStore

from app.core.config import settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

_embeddings: OpenAIEmbeddings | None = None
_vector_store: PGVectorStore | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """Retorna a instância singleton de embeddings via OpenRouter."""
    global _embeddings
    if _embeddings is None:
        if not settings.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada no .env. Obtenha sua chave em https://openrouter.ai/keys"
            )
        logger.info("Inicializando embeddings via OpenRouter (%s)...", settings.OPENROUTER_EMBEDDING_MODEL)
        _embeddings = OpenAIEmbeddings(
            model=settings.OPENROUTER_EMBEDDING_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            check_embedding_ctx_length=False,
        )
    return _embeddings


def get_vector_store() -> PGVectorStore:
    """Retorna a instância singleton do PGVectorStore."""
    global _vector_store
    if _vector_store is None:
        if not settings.DATABASE_URL:
            raise ConfigurationError(
                "Banco não configurado. Defina DB_HOST e DB_PASSWORD no .env."
            )
        _vector_store = PGVectorStore(
            embeddings=get_embeddings(),
            collection_name=settings.COLLECTION_NAME,
            connection=settings.DATABASE_URL,
            use_jsonb=True,
        )
    return _vector_store


def reset_vector_store_state() -> None:
    """Limpa o cache em memória de embeddings e vector store após reset do banco."""
    global _embeddings, _vector_store
    _embeddings = None
    _vector_store = None

