import logging
import os
import urllib.parse
from pathlib import Path
from typing import List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_DEFAULT_DEV_JWT_SECRET = "dev-insecure-jwt-secret-change-in-production"


def _load_dotenv_safe() -> None:
    """
    Carrega o .env detectando automaticamente o encoding pelo BOM.
    O VS Code pode salvar arquivos como UTF-16 LE/BE, o que quebra
    o python-dotenv padrão (UTF-8).
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        load_dotenv()
        return

    raw = env_path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        enc = "utf-16"
    elif raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    else:
        enc = "utf-8"

    load_dotenv(dotenv_path=env_path, encoding=enc)


def _build_database_url() -> str:
    """
    Constrói a DATABASE_URL a partir de variáveis individuais,
    garantindo URL-encoding correto da senha para o psycopg3.
    """
    explicit_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_url:
        return explicit_url

    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "postgres")

    if not host or not password:
        return ""

    encoded_password = urllib.parse.quote(password, safe="")
    return f"postgresql+psycopg://{user}:{encoded_password}@{host}:{port}/{name}?sslmode=require"


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Variável %s='%s' inválida; usando padrão %d.", name, raw, default)
        return default


_load_dotenv_safe()


class Settings:
    """Configurações centrais da aplicação carregadas do ambiente."""

    APP_TITLE: str = "RAG News API"
    APP_DESCRIPTION: str = "API de RAG para notícias (Monólito Modular) com OpenRouter, PGVector e Google OAuth"
    APP_VERSION: str = "3.0.0"

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    OPENROUTER_EMBEDDING_MODEL: str = os.getenv(
        "OPENROUTER_EMBEDDING_MODEL",
        "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    )
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "rag_news")

    FALLBACK_FREE_MODELS: List[str] = [
        "nvidia/nemotron-3.5-super-vl:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "openrouter/free",
    ]

    BBC_RSS_URLS: List[str] = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ]

    DATABASE_URL: str = _build_database_url()

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"
    JWT_EXPIRE_MINUTES: int = _parse_int_env("JWT_EXPIRE_MINUTES", 1440)

    def __init__(self) -> None:
        raw_secret = os.getenv("JWT_SECRET_KEY", "").strip()
        if not raw_secret:
            logger.warning(
                "JWT_SECRET_KEY não configurada no .env; usando chave padrão insegura apenas para desenvolvimento."
            )
            self.JWT_SECRET_KEY = _DEFAULT_DEV_JWT_SECRET
        else:
            self.JWT_SECRET_KEY = raw_secret

    @property
    def psycopg_conn_str(self) -> str:
        """Retorna a connection string compatível com psycopg.connect."""
        return self.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


settings = Settings()
