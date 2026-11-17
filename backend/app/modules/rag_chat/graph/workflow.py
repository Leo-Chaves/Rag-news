from langgraph.graph import END, START, StateGraph

from app.modules.rag_chat.graph.nodes import (
    decidir_evidencia,
    no_filtrar,
    no_gerar_resposta,
    no_montar_contexto,
    no_recuperar,
    no_sem_evidencia,
)
from app.modules.rag_chat.graph.state import EstadoRAG


def build_rag_graph():
    """
    Constrói e compila o grafo StateGraph do pipeline RAG:

    START → recuperar → filtrar → (evidência?) ─sim→ montar_contexto → gerar_resposta → END
                                               └não→ sem_evidencia → END
    """
    grafo = StateGraph(EstadoRAG)
    grafo.add_node("recuperar", no_recuperar)
    grafo.add_node("filtrar", no_filtrar)
    grafo.add_node("montar_contexto", no_montar_contexto)
    grafo.add_node("gerar_resposta", no_gerar_resposta)
    grafo.add_node("sem_evidencia", no_sem_evidencia)

    grafo.add_edge(START, "recuperar")
    grafo.add_edge("recuperar", "filtrar")
    grafo.add_conditional_edges(
        "filtrar",
        decidir_evidencia,
        {
            "com_evidencia": "montar_contexto",
            "sem_evidencia": "sem_evidencia",
        },
    )
    grafo.add_edge("montar_contexto", "gerar_resposta")
    grafo.add_edge("gerar_resposta", END)
    grafo.add_edge("sem_evidencia", END)

    return grafo.compile()


grafo_rag = build_rag_graph()
