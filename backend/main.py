"""Entrypoint de compatibilidade para `uvicorn main:app` e Dockerfile."""

from app.main import app
from app.modules.rag_chat.graph.workflow import grafo_rag

__all__ = ["app", "grafo_rag"]
