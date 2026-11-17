import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import ForbiddenError, register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.news.repository import NewsRepository
from app.modules.news.router import router as news_router
from app.modules.news.schemas import GlobalIngestResponse
from app.modules.news.service import NewsService
from app.modules.rag_chat.router import router as rag_chat_router
from app.modules.users.router import router as users_router
from app.shared.contracts import CurrentUserDTO
from app.shared.dependencies import get_current_user

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
    def ingest_legacy(
        _current_user: CurrentUserDTO = Depends(get_current_user),
    ) -> GlobalIngestResponse:
        """Endpoint legado (exige login, como /news/ingest) que delega a ingestão global."""
        return NewsService.ingest_global_bbc_feeds()

    @application.post("/reset", tags=["Admin"])
    def reset_database(x_admin_key: str | None = Header(default=None)):
        """
        Apaga as tabelas vetoriais do PGVector (todas as notícias, inclusive as
        salvas pelos usuários). Exige o cabeçalho X-Admin-Key igual a ADMIN_API_KEY;
        sem ADMIN_API_KEY configurada, a rota fica desligada.
        """
        if not settings.ADMIN_API_KEY:
            raise ForbiddenError("Rota desativada: defina ADMIN_API_KEY no .env para usá-la.")
        if not x_admin_key or not hmac.compare_digest(
            x_admin_key.encode("utf-8"), settings.ADMIN_API_KEY.encode("utf-8")
        ):
            raise ForbiddenError("Chave de administrador inválida.")
        NewsRepository.reset_pgvector_tables()
        return {
            "message": (
                "Tabelas de embeddings resetadas com sucesso no Supabase. "
                "Execute /ingest para re-indexar as notícias com o novo modelo."
            )
        }

    return application


app = create_app()

