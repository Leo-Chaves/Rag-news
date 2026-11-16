from typing import TypedDict


class EstadoRAG(TypedDict, total=False):
    """Estado compartilhado entre os nós do grafo LangGraph."""

    pergunta: str
    top_k: int
    scope: str
    user_id: str | None
    custom_source_id: str | None
    documentos_recuperados: list
    score_maximo: float
    contexto: str
    resposta: str
