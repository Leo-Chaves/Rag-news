import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.news.repository import NewsRepository
from app.modules.news.router import router as news_router
from app.modules.news.schemas import GlobalIngestResponse
from app.modules.news.service import NewsService
from app.modules.rag_chat.router import router as rag_chat_router
from app.modules.users.router import router as users_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Inicialização de logs e criação idempotente de tabelas no boot."""
    logger.info("=== %s iniciando (Monólito Modular) ===", settings.APP_TITLE)
    logger.info("Chat Model: %s", settings.OPENROUTER_MODEL)
    logger.info("Embedding Model: %s", settings.OPENROUTER_EMBEDDING_MODEL)
    if not settings.OPENROUTER_API_KEY:
        logger.warning("ATENÇÃO: OPENROUTER_API_KEY não foi informada no .env!")

    try:
        init_db()
    except Exception as exc:
        logger.warning("Falha ao inicializar banco relacional no boot: %s", exc)

    yield


def create_app() -> FastAPI:
    """Factory principal da aplicação FastAPI."""
    application = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "*"],
    )

    register_exception_handlers(application)

    # Routers dos módulos de domínio
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(news_router)
    application.include_router(rag_chat_router)

    # Rotas raiz para retrocompatibilidade com o frontend/deploy atual
    @application.get("/", tags=["Health"])
    def health_check():
        return {
            "status": "ok",
            "message": "RAG News API is running with OpenRouter",
            "chat_model": settings.OPENROUTER_MODEL,
            "embedding_model": settings.OPENROUTER_EMBEDDING_MODEL,
            "architecture": "modular_monolith",
        }

    @application.post("/ingest", response_model=GlobalIngestResponse, tags=["Ingestion"])
    def ingest_legacy() -> GlobalIngestResponse:
        """Endpoint legado que delega a ingestão global da BBC para o módulo news."""
        return NewsService.ingest_global_bbc_feeds()

    @application.post("/reset", tags=["Admin"])
    def reset_database():
        """Endpoint legado que reseta as tabelas vetoriais do PGVector."""
        NewsRepository.reset_pgvector_tables()
        return {
            "message": (
                "Tabelas de embeddings resetadas com sucesso no Supabase. "
                "Execute /ingest para re-indexar as notícias com o novo modelo."
            )
        }

    return application


app = create_app()

