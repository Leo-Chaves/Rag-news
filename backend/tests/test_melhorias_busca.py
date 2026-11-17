"""
Testes do filtro de relevância, data, promos e das correções de segurança.
Nada aqui acessa rede, banco ou LLM: tudo é substituído por dublês.
Rodar: cd backend && python -m pytest tests -q
"""
from datetime import datetime, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.core import config
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.modules.news import parsers
from app.modules.news.repository import NewsRepository
from app.modules.rag_chat.graph import nodes
from app.modules.rag_chat.graph.workflow import grafo_rag

# 17/11/2026 15:00 UTC = 12:00 em Brasília
AGORA = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)
HOJE = "Tue, 17 Nov 2026 12:00:00 GMT"
ONTEM = "Mon, 16 Nov 2026 12:00:00 GMT"
ANTEONTEM = "Sun, 15 Nov 2026 12:00:00 GMT"
# 01:00 UTC do dia 17 ainda é 22:00 do dia 16 em Brasília
ONTEM_EM_BRASILIA = "Tue, 17 Nov 2026 01:00:00 GMT"


def doc(titulo: str, published: str = ANTEONTEM, **meta) -> Document:
    return Document(
        page_content=f"Título: {titulo}",
        metadata={"title": titulo, "source": f"https://x/{titulo}", "published": published, **meta},
    )


class FakeVectorStore:
    def __init__(self, resultados):
        self.resultados = resultados
        self.chamadas: list[dict] = []

    def similarity_search_with_relevance_scores(self, query, k, filter=None):
        self.chamadas.append({"query": query, "k": k, "filter": filter})
        return list(self.resultados)[:k]


@pytest.fixture(autouse=True)
def agora_fixo(monkeypatch):
    monkeypatch.setattr(nodes, "_agora", lambda: AGORA)


@pytest.fixture
def vs(monkeypatch):
    def instalar(resultados):
        fake = FakeVectorStore(resultados)
        monkeypatch.setattr(nodes, "get_vector_store", lambda: fake)
        return fake

    return instalar


@pytest.fixture
def llm(monkeypatch):
    chamadas: list[dict] = []

    def fake(prompt, variaveis, temperature=0.3):
        chamadas.append({"prompt": prompt, "variaveis": variaveis})
        return "resposta do modelo"

    monkeypatch.setattr(nodes, "generate_chat_completion", fake)
    return chamadas


def recuperar_e_filtrar(pergunta, scope="global", top_k=5, user_id="u1"):
    estado = {"pergunta": pergunta, "top_k": top_k, "scope": scope, "user_id": user_id}
    estado.update(nodes.no_recuperar(estado))
    estado.update(nodes.no_filtrar(estado))
    return estado


def titulos(estado):
    return [d.metadata["title"] for d in estado["documentos_recuperados"]]


# --------------------------------------------------------------------------
# Filtro de relevância e promos
# --------------------------------------------------------------------------

def test_busca_tres_vezes_top_k_candidatos(vs):
    fake = vs([(doc("a"), 0.9)])
    recuperar_e_filtrar("inteligência artificial", top_k=5)
    assert fake.chamadas[0]["k"] == 15


def test_descarta_noticia_fraca(vs):
    vs([(doc("ia forte"), 0.80), (doc("ia media"), 0.65), (doc("quiz futebol"), 0.50)])
    estado = recuperar_e_filtrar("inteligência artificial")
    # corte = 0.80 * 0.75 = 0.60
    assert titulos(estado) == ["ia forte", "ia media"]
    assert estado["score_maximo"] == pytest.approx(0.80)


def test_respeita_top_k(vs):
    vs([(doc(f"n{i}"), 0.9 - i * 0.01) for i in range(10)])
    assert len(titulos(recuperar_e_filtrar("tecnologia", top_k=3))) == 3


def test_remove_promocionais(vs):
    vs([(doc("Download now"), 0.95), (doc("Find out more here "), 0.94), (doc("notícia"), 0.70)])
    estado = recuperar_e_filtrar("tecnologia")
    assert titulos(estado) == ["notícia"]


def test_promocional_nao_conta_como_evidencia(vs, llm):
    vs([(doc("Download now"), 0.95)])
    resultado = grafo_rag.invoke({"pergunta": "tecnologia", "top_k": 5, "scope": "global", "user_id": "u1"})
    assert resultado["documentos_recuperados"] == []
    assert llm == []


def test_promo_nao_puxa_o_corte(vs):
    # Se o promo (0.95) contasse no melhor score, o corte seria 0.71 e a notícia sairia.
    vs([(doc("Download now"), 0.95), (doc("notícia"), 0.65)])
    assert titulos(recuperar_e_filtrar("tecnologia")) == ["notícia"]


def test_escopo_global_nao_vaza_documento_privado(vs):
    vs([(doc("privada", scope="saved", user_id="outro"), 0.9), (doc("publica"), 0.85)])
    assert titulos(recuperar_e_filtrar("tecnologia")) == ["publica"]


# --------------------------------------------------------------------------
# Recência e data exata
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pergunta",
    ["últimas notícias", "o que há de novo esta semana?", "novidades de IA", "latest news", "recent AI news"],
)
def test_detecta_pergunta_temporal(pergunta):
    assert nodes._pergunta_temporal(pergunta)


@pytest.mark.parametrize("pergunta", ["mudanças climáticas", "notícias da Ferrari", "inteligência artificial"])
def test_pergunta_sem_periodo(pergunta):
    assert not nodes._pergunta_temporal(pergunta)


def test_recencia_prioriza_a_mais_nova(vs):
    vs([(doc("antiga", ANTEONTEM), 0.80), (doc("nova", HOJE), 0.78)])
    assert titulos(recuperar_e_filtrar("últimas notícias de tecnologia")) == ["nova", "antiga"]


def test_sem_periodo_ordem_por_score(vs):
    vs([(doc("antiga", ANTEONTEM), 0.80), (doc("nova", HOJE), 0.78)])
    assert titulos(recuperar_e_filtrar("tecnologia")) == ["antiga", "nova"]


def test_recencia_nao_ressuscita_noticia_fraca(vs):
    vs([(doc("antiga relevante", ANTEONTEM), 0.90), (doc("nova fora do assunto", HOJE), 0.50)])
    assert titulos(recuperar_e_filtrar("últimas notícias de clima")) == ["antiga relevante"]


def test_hoje_mantem_so_noticias_do_dia_em_brasilia(vs):
    fake = vs([
        (doc("de anteontem", ANTEONTEM), 0.90),
        (doc("22h de ontem em Brasília", ONTEM_EM_BRASILIA), 0.88),
        (doc("de hoje", HOJE), 0.80),
    ])
    estado = recuperar_e_filtrar("o que aconteceu no futebol hoje?")
    assert titulos(estado) == ["de hoje"]
    assert estado["data_alvo"] == "2026-11-17"
    assert fake.chamadas[0]["k"] == 50  # busca mais candidatos com data exata


def test_ontem_mantem_so_noticias_de_ontem(vs):
    vs([(doc("hoje", HOJE), 0.9), (doc("ontem cedo", ONTEM), 0.8), (doc("ontem à noite", ONTEM_EM_BRASILIA), 0.8)])
    assert sorted(titulos(recuperar_e_filtrar("o que rolou ontem?"))) == ["ontem cedo", "ontem à noite"]


def test_corte_de_relevancia_usa_o_melhor_do_dia(vs):
    # Sem a data, o corte seria 0.95 * 0.75 = 0.71 e a notícia de hoje sairia.
    vs([(doc("antiga", ANTEONTEM), 0.95), (doc("de hoje", HOJE), 0.60)])
    assert titulos(recuperar_e_filtrar("notícias de hoje")) == ["de hoje"]


@pytest.mark.parametrize("pergunta", ["como está a economia hoje em dia?", "notícias de hoje e de ontem"])
def test_sem_data_exata(pergunta):
    assert nodes._data_alvo(pergunta, AGORA) is None


def test_data_exata_so_no_escopo_global(vs):
    # Notícias salvas costumam vir sem data; o filtro apagaria todas.
    vs([(doc("salva sem data", "", scope="saved", user_id="u1"), 0.9)])
    estado = recuperar_e_filtrar("o que salvei hoje?", scope="saved")
    assert estado["data_alvo"] is None
    assert titulos(estado) == ["salva sem data"]


def test_hoje_sem_noticias_do_dia_avisa(vs, llm):
    vs([(doc("antiga", ANTEONTEM), 0.9)])
    resultado = grafo_rag.invoke(
        {"pergunta": "o que aconteceu hoje?", "top_k": 5, "scope": "global", "user_id": "u1"}
    )
    assert "hoje (17/11/2026)" in resultado["resposta"]
    assert resultado["documentos_recuperados"] == []
    assert llm == []


def test_data_invalida_nao_quebra(vs):
    vs([(doc("sem data", "data esquisita"), 0.9), (doc("vazia", ""), 0.85)])
    assert titulos(recuperar_e_filtrar("últimas notícias")) == ["sem data", "vazia"]


def test_data_iso_e_aceita():
    assert nodes._data_publicacao(doc("x", "2026-11-16T10:00:00Z")) == datetime(
        2026, 11, 16, 10, 0, tzinfo=timezone.utc
    )


# --------------------------------------------------------------------------
# Contexto e prompt
# --------------------------------------------------------------------------

def test_contexto_tem_data_em_brasilia():
    estado = {"documentos_recuperados": [doc("noite", ONTEM_EM_BRASILIA, source_name="BBC News")]}
    contexto = nodes.no_montar_contexto(estado)["contexto"]
    assert "[BBC News | publicada em 16/11/2026 | noite]" in contexto


def test_prompt_recebe_data_de_hoje(vs, llm):
    vs([(doc("notícia", HOJE), 0.9)])
    resultado = grafo_rag.invoke({"pergunta": "tecnologia", "top_k": 5, "scope": "global", "user_id": "u1"})
    assert resultado["resposta"] == "resposta do modelo"
    variaveis = llm[0]["variaveis"]
    assert variaveis["hoje"] == "17/11/2026"
    mensagens = llm[0]["prompt"].format_messages(**variaveis)
    assert "Data de hoje (horário de Brasília): 17/11/2026" in mensagens[0].content


# --------------------------------------------------------------------------
# Ingestão
# --------------------------------------------------------------------------

class FakeFeed:
    bozo = False

    def __init__(self, entries):
        self.entries = entries


def test_ingestao_ignora_promocionais(monkeypatch):
    entries = [
        {"title": "Download now", "summary": "app", "link": "https://bbc/app"},
        {"title": "Notícia real", "summary": "texto", "link": "https://bbc/1", "published": HOJE},
    ]
    monkeypatch.setattr(parsers.feedparser, "parse", lambda url: FakeFeed(entries))
    _chunks, metas, total, _skipped = parsers.fetch_and_chunk_rss(["https://feed"])
    assert total == 1
    assert {m["title"] for m in metas} == {"Notícia real"}

    itens = parsers.fetch_rss_feed_entries(["https://feed"])
    assert [i["title"] for i in itens] == ["Notícia real"]


def _conexao_que_falha(erro):
    def connect(*_a, **_k):
        raise erro

    return connect


def test_deduplicacao_tabela_inexistente_retorna_vazio(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    monkeypatch.setattr(psycopg, "connect", _conexao_que_falha(psycopg.errors.UndefinedTable("x")))
    assert NewsRepository.get_existing_sources() == set()


def test_deduplicacao_com_erro_aborta_em_vez_de_regravar(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    monkeypatch.setattr(psycopg, "connect", _conexao_que_falha(psycopg.OperationalError("timeout")))
    with pytest.raises(ExternalServiceError):
        NewsRepository.get_existing_sources()


# --------------------------------------------------------------------------
# Segurança: segredo do JWT, /reset e /ingest
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "valor",
    ["", "gere-uma-chave-secreta-forte-aqui", "dev-insecure-jwt-secret-change-in-production", "curta"],
)
def test_segredo_jwt_inseguro_vira_aleatorio(monkeypatch, valor):
    monkeypatch.setenv("JWT_SECRET_KEY", valor)
    a, b = config._resolve_jwt_secret(), config._resolve_jwt_secret()
    assert a != valor and len(a) >= 32
    assert a != b  # aleatório, não um valor fixo que alguém possa conhecer


def test_segredo_jwt_forte_e_mantido(monkeypatch):
    forte = "x" * 40
    monkeypatch.setenv("JWT_SECRET_KEY", forte)
    assert config._resolve_jwt_secret() == forte


@pytest.fixture
def client(monkeypatch):
    from app.main import app

    chamadas: list[str] = []
    monkeypatch.setattr(NewsRepository, "reset_pgvector_tables", staticmethod(lambda: chamadas.append("reset")))
    c = TestClient(app)  # sem "with": não roda o lifespan (que conecta no banco)
    c.resets = chamadas
    return c


def test_reset_desligado_sem_admin_key(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
    r = client.post("/reset", headers={"X-Admin-Key": ""})
    assert r.status_code == 403
    assert client.resets == []


@pytest.mark.parametrize("headers", [{}, {"X-Admin-Key": "errada"}])
def test_reset_recusa_chave_ausente_ou_errada(client, monkeypatch, headers):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "chave-admin-de-teste")
    assert client.post("/reset", headers=headers).status_code == 403
    assert client.resets == []


def test_reset_com_chave_certa(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "chave-admin-de-teste")
    r = client.post("/reset", headers={"X-Admin-Key": "chave-admin-de-teste"})
    assert r.status_code == 200
    assert client.resets == ["reset"]


def test_ingest_legado_exige_login(client, monkeypatch):
    from app.modules.news.service import NewsService

    chamadas: list[str] = []
    monkeypatch.setattr(NewsService, "ingest_global_bbc_feeds", staticmethod(lambda: chamadas.append("x")))
    assert client.post("/ingest").status_code == 401
    assert chamadas == []
