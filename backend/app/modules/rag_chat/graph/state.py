from typing import TypedDict


class EstadoRAG(TypedDict, total=False):
    """Estado compartilhado entre os nós do grafo LangGraph."""

    pergunta: str
    top_k: int
    scope: str
    user_id: str | None
    custom_source_id: str | None
    candidatos: list  # [(Document, score)] vindos da busca, antes do filtro
    temporal: bool  # pergunta fala de período recente (bônus de recência)
    data_alvo: str | None  # "hoje"/"ontem" em ISO (AAAA-MM-DD), horário de Brasília
    documentos_recuperados: list
    score_maximo: float
    contexto: str
    resposta: str

