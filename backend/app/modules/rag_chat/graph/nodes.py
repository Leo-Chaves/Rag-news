from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import generate_chat_completion
from app.core.vector_store import get_vector_store
from app.modules.rag_chat.graph.state import EstadoRAG

_NO_EVIDENCE_MESSAGES: dict[str, str] = {
    "global": "Não encontrei informações suficientes nas notícias de hoje para responder a isso.",
    "saved": "Não encontrei informações suficientes nas suas notícias salvas para responder a isso.",
    "custom": "Não encontrei informações suficientes nas suas fontes personalizadas para responder a isso.",
    "personal_all": "Não encontrei informações suficientes no seu acervo pessoal para responder a isso.",
}


def _no_evidence_message(scope: str) -> str:
    return _NO_EVIDENCE_MESSAGES.get(scope, _NO_EVIDENCE_MESSAGES["global"])


def _build_metadata_filter(estado: EstadoRAG) -> dict[str, Any]:
    scope = estado.get("scope", "global")
    user_id = estado.get("user_id")
    custom_source_id = estado.get("custom_source_id")

    if scope == "saved":
        return {"user_id": str(user_id), "scope": "saved"}

    if scope == "custom":
        flt: dict[str, Any] = {"user_id": str(user_id), "scope": "custom"}
        if custom_source_id:
            flt["custom_source_id"] = str(custom_source_id)
        return flt

    if scope == "personal_all":
        return {"user_id": str(user_id), "scope": {"$in": ["saved", "custom"]}}

    # Escopo global: aceita registros novos (scope='global') e antigos sem 'scope'
    return {"$or": [{"scope": "global"}, {"scope": {"$exists": False}}]}


def no_recuperar(estado: EstadoRAG) -> dict[str, Any]:
    """Recupera chunks relevantes aplicando isolamento por escopo e user_id."""
    scope = estado.get("scope", "global")
    user_id = estado.get("user_id")
    top_k = estado.get("top_k", 5)

    if scope != "global" and not user_id:
        return {"documentos_recuperados": [], "score_maximo": 0.0}

    vs = get_vector_store()
    metadata_filter = _build_metadata_filter(estado)
    docs_scores = vs.similarity_search_with_relevance_scores(
        estado["pergunta"],
        k=top_k,
        filter=metadata_filter,
    )

    # Defesa em profundidade: garante que documentos privados não vazem no escopo global
    if scope == "global":
        docs_scores = [
            (doc, score)
            for doc, score in docs_scores
            if doc.metadata.get("scope", "global") == "global"
        ]

    if docs_scores:
        score_max = max(score for _doc, score in docs_scores)
        docs = [doc for doc, _score in docs_scores]
    else:
        score_max = 0.0
        docs = []

    return {"documentos_recuperados": docs, "score_maximo": score_max}


def no_montar_contexto(estado: EstadoRAG) -> dict[str, str]:
    """Formata os documentos recuperados em blocos de contexto para o prompt."""
    docs = estado.get("documentos_recuperados", [])
    partes = []
    for i, doc in enumerate(docs, 1):
        titulo = doc.metadata.get("title", f"Fonte {i}")
        partes.append(f"[{titulo}]\n{doc.page_content}")
    return {"contexto": "\n\n".join(partes)}


def no_gerar_resposta(estado: EstadoRAG) -> dict[str, str]:
    """Invoca o LLM OpenRouter (com fallback) restringindo ao contexto recuperado."""
    scope = estado.get("scope", "global")
    fallback_msg = _no_evidence_message(scope)

    prompt = ChatPromptTemplate.from_template(
        "Você é o Assistente RAG News, uma Inteligência Artificial especializada em análise de notícias, "
        "desenvolvido como um projeto universitário de IA Generativa.\n\n"
        "Sua missão é ler as fontes jornalísticas e entregar respostas precisas.\n"
        "Regras Absolutas:\n"
        "1. Baseie sua resposta EXCLUSIVAMENTE no contexto fornecido.\n"
        "2. Se a informação não estiver no contexto, diga claramente: '{fallback_msg}' Jamais invente dados.\n"
        "3. Responda em Português do Brasil (PT-BR). Se a notícia for sobre um assunto leve e descontraído "
        "(ex: curiosidades, entretenimento), sinta-se à vontade para fazer uma piada rápida e inteligente no "
        "final da resposta. Se for um assunto sério (tragédias, política pesada), mantenha a postura profissional e neutra.\n\n"
        "Contexto:\n{contexto}\n\nPergunta: {pergunta}\n\nResposta:"
    )

    resposta = generate_chat_completion(
        prompt,
        {
            "contexto": estado.get("contexto", ""),
            "pergunta": estado["pergunta"],
            "fallback_msg": fallback_msg,
        },
    )
    return {"resposta": resposta}


def no_sem_evidencia(estado: EstadoRAG) -> dict[str, Any]:
    """Retorna resposta padrão quando nenhum chunk atinge o threshold mínimo."""
    scope = estado.get("scope", "global")
    return {
        "resposta": _no_evidence_message(scope),
        "documentos_recuperados": [],
    }


def decidir_evidencia(estado: EstadoRAG) -> Literal["com_evidencia", "sem_evidencia"]:
    """Decide se há evidência suficiente (>= 0.10) para gerar resposta."""
    if estado.get("score_maximo", -1.0) >= 0.10 and estado.get("documentos_recuperados"):
        return "com_evidencia"
    return "sem_evidencia"

