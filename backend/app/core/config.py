import logging
import os
import secrets
import urllib.parse
from pathlib import Path
from typing import List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Valores que já foram publicados no repositório: quem os conhece forja tokens.
_PUBLIC_JWT_SECRETS = {
    "dev-insecure-jwt-secret-change-in-production",
    "gere-uma-chave-secreta-forte-aqui",
}
_MIN_JWT_SECRET_LENGTH = 32


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

    sslmode = os.getenv("DB_SSLMODE", "").strip()
    if not sslmode:
        sslmode = "disable" if host in ("127.0.0.1", "localhost", "db", "postgres") else "require"

    encoded_password = urllib.parse.quote(password, safe="")
    return f"postgresql+psycopg://{user}:{encoded_password}@{host}:{port}/{name}?sslmode={sslmode}"


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Variável %s='%s' inválida; usando padrão %d.", name, raw, default)
        return default


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Variável %s='%s' inválida; usando padrão %s.", name, raw, default)
        return default


def _resolve_jwt_secret() -> str:
    """
    Usa JWT_SECRET_KEY do ambiente. Se estiver vazia, for um valor já publicado
    no repositório ou for curta demais, gera uma chave aleatória por processo:
    ninguém consegue forjar tokens, mas os logins caem a cada reinício.
    """
    raw = os.getenv("JWT_SECRET_KEY", "").strip()
    if raw and raw not in _PUBLIC_JWT_SECRETS and len(raw) >= _MIN_JWT_SECRET_LENGTH:
        return raw

    motivo = (
        "não configurada" if not raw
        else "é um valor de exemplo público" if raw in _PUBLIC_JWT_SECRETS
        else f"tem menos de {_MIN_JWT_SECRET_LENGTH} caracteres"
    )
    logger.warning(
        "JWT_SECRET_KEY %s; usando chave aleatória temporária (logins expiram a cada "
        "reinício). Gere uma com: python -c \"import secrets; print(secrets.token_urlsafe(48))\"",
        motivo,
    )
    return secrets.token_urlsafe(48)


_load_dotenv_safe()


class Settings:
    """Configurações centrais da aplicação carregadas do ambiente."""

    APP_TITLE: str = "RAG News API"
    APP_DESCRIPTION: str = "API de RAG para notícias (Monólito Modular) com OpenRouter, PGVector e JWT"
    APP_VERSION: str = "3.0.0"

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    OPENROUTER_EMBEDDING_MODEL: str = os.getenv(
        "OPENROUTER_EMBEDDING_MODEL",
        "nvidia/nemotron-3.5-embed-1b:free",
    )
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "rag_news")

    FALLBACK_FREE_MODELS: List[str] = [
        "nvidia/nemotron-3.5-super-vl:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "openrouter/free",
    ]

    GLOBAL_RSS_FEEDS: List[dict[str, str]] = [
        # Brasil (PT-BR)
        {
            "source_name": "G1",
            "category": "Brasil (PT-BR)",
            "url": "https://g1.globo.com/rss/g1/",
        },
        {
            "source_name": "G1 Tech",
            "category": "Tech & Inovação",
            "url": "https://g1.globo.com/rss/g1/tecnologia/",
        },
        {
            "source_name": "BBC Brasil",
            "category": "Brasil (PT-BR)",
            "url": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        },
        {
            "source_name": "Agência Brasil",
            "category": "Brasil (PT-BR)",
            "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
        },
        # Tech & Inovação (EN)
        {
            "source_name": "TechCrunch",
            "category": "Tech & Inovação",
            "url": "https://techcrunch.com/feed/",
        },
        {
            "source_name": "Ars Technica",
            "category": "Tech & Inovação",
            "url": "https://feeds.arstechnica.com/arstechnica/index",
        },
        {
            "source_name": "The Verge",
            "category": "Tech & Inovação",
            "url": "https://www.theverge.com/rss/index.xml",
        },
        # BBC Internacional (EN)
        {
            "source_name": "BBC News",
            "category": "BBC Internacional",
            "url": "http://feeds.bbci.co.uk/news/rss.xml",
        },
        {
            "source_name": "BBC World",
            "category": "BBC Internacional",
            "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        },
        {
            "source_name": "BBC Tech",
            "category": "Tech & Inovação",
            "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        },
        {
            "source_name": "BBC Business",
            "category": "BBC Internacional",
            "url": "http://feeds.bbci.co.uk/news/business/rss.xml",
        },
        {
            "source_name": "BBC Science",
            "category": "BBC Internacional",
            "url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        },
    ]

    BBC_RSS_URLS: List[str] = [feed["url"] for feed in GLOBAL_RSS_FEEDS]
    MAX_ARTICLES_PER_FEED: int = _parse_int_env("MAX_ARTICLES_PER_FEED", 12)

    DATABASE_URL: str = _build_database_url()

    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"
    JWT_EXPIRE_MINUTES: int = _parse_int_env("JWT_EXPIRE_MINUTES", 1440)

    # Chave exigida no cabeçalho X-Admin-Key do POST /reset. Vazia = rota desligada.
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "").strip()

    # --- Busca do chat (nó "filtrar") ---
    # Só vai para o contexto a notícia com score >= esta fração do melhor.
    RELEVANCE_MIN_RATIO: float = _parse_float_env("RELEVANCE_MIN_RATIO", 0.75)
    # Perguntas sobre período recente: bônus RECENCY_BOOST x 0.5^(idade/meia-vida).
    RECENCY_BOOST: float = _parse_float_env("RECENCY_BOOST", 0.1)
    RECENCY_HALF_LIFE_DAYS: float = _parse_float_env("RECENCY_HALF_LIFE_DAYS", 1.0)

    def __init__(self) -> None:
        self.JWT_SECRET_KEY = _resolve_jwt_secret()

    @property
    def psycopg_conn_str(self) -> str:
        """Retorna a connection string compatível com psycopg.connect."""
        return self.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


settings = Settings()

