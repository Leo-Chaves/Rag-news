import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.exceptions import ConfigurationError, ExternalServiceError

logger = logging.getLogger(__name__)


def generate_chat_completion(
    prompt: ChatPromptTemplate,
    variables: dict[str, Any],
    temperature: float = 0.3,
) -> str:
    """
    Executa um ChatPromptTemplate via OpenRouter percorrendo a lista de
    modelos gratuitos com fallback automático.
    """
    if not settings.OPENROUTER_API_KEY:
        raise ConfigurationError(
            "OPENROUTER_API_KEY não configurada no .env. Obtenha sua chave em https://openrouter.ai/keys"
        )

    candidate_models = list(dict.fromkeys([settings.OPENROUTER_MODEL] + settings.FALLBACK_FREE_MODELS))
    last_error: Exception | None = None

    for model_name in candidate_models:
        try:
            llm = ChatOpenAI(
                model=model_name,
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                default_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "RAG News Faculdade",
                },
            )
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke(variables)
            if model_name != settings.OPENROUTER_MODEL:
                logger.info("Resposta gerada usando modelo fallback gratuito: %s", model_name)
            return answer
        except Exception as exc:
            logger.warning("Modelo '%s' indisponível (%s). Tentando próximo fallback...", model_name, exc)
            last_error = exc

    raise ExternalServiceError(f"Todos os modelos OpenRouter falharam: {last_error}")

