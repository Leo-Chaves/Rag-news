"""
Testes da feature de login/perfil/temas.
Rodam sem Supabase, Groq ou banco reais: LLM, vector store, JWKS e
preferências são substituídos por versões falsas.

    cd backend
    pip install -r requirements-dev.txt
    pytest -q
"""
import os, sys, time, json, io
from pathlib import Path
os.environ["SUPABASE_URL"] = "https://proj.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "anon"
os.environ["DB_HOST"] = "fake"; os.environ["DB_PASSWORD"] = "x"
os.environ["GROQ_API_KEY"] = "x"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt, pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import main, auth, topics

# ── stubs ────────────────────────────────────────────────────────────────
main._embeddings = object()
main.DATABASE_URL = "postgresql+psycopg://u:p@h/db"
main.ChatGroq = lambda **kw: FakeListChatModel(responses=["resposta"] * 100)

def D(cat, src, s):
    return (Document(page_content=f"{cat} news", metadata={"category": cat, "source": src, "title": cat}), s)

class FakeVS:
    calls = []
    queries = []
    results = []
    def similarity_search_with_relevance_scores(self, q, k):
        self.calls.append(k)
        self.queries.append(q)
        return self.results[:k]
main._vector_store = FakeVS()

DB = {}
main.get_user_topics = lambda c, uid: DB.get(uid, [])
def _set(c, uid, t): DB[uid] = t; return t
main.set_user_topics = _set

KEY = ec.generate_private_key(ec.SECP256R1())
class FakeJWKS:
    def get_signing_key_from_jwt(self, tok):
        return type("K", (), {"key": KEY.public_key()})()
auth._jwks_client = FakeJWKS()

def token(sub="user-1", **over):
    claims = {"sub": sub, "email": "a@b.c", "aud": "authenticated",
              "iss": "https://proj.supabase.co/auth/v1", "exp": int(time.time()) + 3600}
    claims.update(over)
    return jwt.encode(claims, KEY, algorithm="ES256", headers={"kid": "k1"})

H = lambda t: {"Authorization": f"Bearer {t}"}
client = TestClient(main.app)

# ── topics ───────────────────────────────────────────────────────────────
def test_expand_and_normalize():
    assert topics.expand_topics(["esportes"]) == {"esportes", "futebol", "tenis", "formula1", "basquete"}
    assert topics.normalize_topics(["futebol", "esportes", "politica", "politica"]) == ["politica", "esportes"]
    with pytest.raises(ValueError):
        topics.normalize_topics(["xpto"])

def test_feeds_specific_before_generic():
    cats = [c for _, c in topics.RSS_FEEDS]
    assert cats.index("futebol") < cats.index("esportes") and cats[-1] == "geral"

def test_topics_route():
    r = client.get("/topics").json()
    assert r["auth_enabled"] and any(t["slug"] == "futebol" and t["parent"] == "esportes" for t in r["topics"])

# ── auth ─────────────────────────────────────────────────────────────────
def test_prefs_require_login():
    assert client.get("/me/preferences").status_code == 401

@pytest.mark.parametrize("bad", [
    {"exp": int(time.time()) - 3600},
    {"aud": "anon"},
    {"iss": "https://other.supabase.co/auth/v1"},
])
def test_bad_tokens(bad):
    assert client.get("/me/preferences", headers=H(token(**bad))).status_code == 401

def test_wrong_signature():
    other = ec.generate_private_key(ec.SECP256R1())
    t = jwt.encode({"sub": "x", "aud": "authenticated", "iss": "https://proj.supabase.co/auth/v1",
                    "exp": int(time.time()) + 60}, other, algorithm="ES256")
    assert client.get("/me/preferences", headers=H(t)).status_code == 401

def test_alg_none_rejected():
    t = jwt.encode({"sub": "x"}, None, algorithm="none")
    assert client.get("/me/preferences", headers=H(t)).status_code == 401

def test_garbage_token():
    assert client.get("/me/preferences", headers=H("abc")).status_code == 401

def test_legacy_hs256(monkeypatch):
    t = jwt.encode({"sub": "legacy", "exp": int(time.time()) + 600}, "secret", algorithm="HS256")
    seen = {}
    class Resp(io.BytesIO):
        def __enter__(s): return s
        def __exit__(s, *a): pass
    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url; seen["apikey"] = req.headers.get("Apikey")
        return Resp(json.dumps({"id": "legacy", "email": "l@x"}).encode())
    monkeypatch.setattr(auth.urllib.request, "urlopen", fake_urlopen)
    r = client.get("/me/preferences", headers=H(t))
    assert r.status_code == 200 and seen["url"].endswith("/auth/v1/user") and seen["apikey"] == "anon"

def test_legacy_rejected(monkeypatch):
    import urllib.error
    t = jwt.encode({"sub": "z", "exp": int(time.time()) + 600}, "s2", algorithm="HS256")
    def boom(req, timeout): raise urllib.error.HTTPError(req.full_url, 401, "no", {}, None)
    monkeypatch.setattr(auth.urllib.request, "urlopen", boom)
    assert client.get("/me/preferences", headers=H(t)).status_code == 401

# ── preferences ──────────────────────────────────────────────────────────
def test_save_and_read_prefs():
    t = token()
    r = client.put("/me/preferences", headers=H(t), json={"topics": ["futebol", "esportes", "politica"]})
    assert r.status_code == 200 and r.json()["topics"] == ["politica", "esportes"]
    assert client.get("/me/preferences", headers=H(t)).json()["topics"] == ["politica", "esportes"]
    assert client.put("/me/preferences", headers=H(t), json={"topics": ["hack"]}).status_code == 422

def test_prefs_isolated_per_user():
    client.put("/me/preferences", headers=H(token("u-a")), json={"topics": ["saude"]})
    assert client.get("/me/preferences", headers=H(token("u-b"))).json()["topics"] == []

# ── chat ─────────────────────────────────────────────────────────────────
RESULTS = [D("politica", "p1", .40), D("mundo", "m1", .38), D("mundo", "m2", .37), D("negocios", "n1", .36),
           D("ciencia", "c1", .35), D("cultura", "x1", .34), D("futebol", "f1", .33), D("tenis", "t1", .32)]

def test_chat_anonymous_unchanged():
    FakeVS.results = RESULTS; FakeVS.calls.clear()
    r = client.post("/chat", json={"question": "q"}).json()
    assert FakeVS.calls == [5] and r["personalizado"] is False
    assert r["sources"] == ["p1", "m1", "m2", "n1", "c1"]

def test_chat_personalized_boosts_sports():
    DB["fan"] = ["esportes"]
    FakeVS.results = RESULTS; FakeVS.calls.clear()
    r = client.post("/chat", headers=H(token("fan")), json={"question": "q"}).json()
    assert FakeVS.calls == [15] and r["personalizado"] is True
    assert r["sources"][:2] == ["f1", "t1"] and "p1" in r["sources"]   # promove sem filtrar

def test_boost_does_not_bypass_evidence_threshold():
    DB["fan"] = ["esportes"]
    FakeVS.results = [D("futebol", "f1", .01)]
    r = client.post("/chat", headers=H(token("fan")), json={"question": "q"}).json()
    assert r["sources"] == [] and "Não encontrei" in r["answer"]

def test_chat_with_expired_token_is_401():
    assert client.post("/chat", headers=H(token(exp=1)), json={"question": "q"}).status_code == 401

def test_prefs_db_failure_does_not_break_chat(monkeypatch):
    def boom(c, u): raise RuntimeError("db down")
    monkeypatch.setattr(main, "get_user_topics", boom)
    FakeVS.results = RESULTS
    r = client.post("/chat", headers=H(token()), json={"question": "q"})
    assert r.status_code == 200 and r.json()["personalizado"] is False

# ── ingest ───────────────────────────────────────────────────────────────
def test_fetch_tags_category_and_dedups_across_feeds(monkeypatch):
    feeds = {"u_fut": [("A", "l1")], "u_sport": [("A", "l1"), ("B", "l2")], "u_old": [("C", "l3")]}
    class F(dict):
        __getattr__ = dict.get
    def parse(url):
        return F(bozo=False, entries=[F(title=t, summary="s", link=l, published="") for t, l in feeds[url]])
    monkeypatch.setattr(main.feedparser, "parse", parse)
    chunks, metas, n, skipped = main._fetch_and_chunk_rss(
        [("u_fut", "futebol"), ("u_sport", "esportes"), ("u_old", "geral")], existing_sources={"l3"})
    assert [(m["source"], m["category"]) for m in metas] == [("l1", "futebol"), ("l2", "esportes")]
    assert n == 2 and skipped == 2


# ── limites do Groq ─────────────────────────────────────────────────────────
def _llm_raising(exc):
    from langchain_core.runnables import RunnableLambda
    def boom(_): raise exc
    return lambda **kw: RunnableLambda(boom)

def _groq_error(cls, code):
    import httpx
    resp = httpx.Response(code, request=httpx.Request("POST", "https://api.groq.com/x"))
    return cls("erro", response=resp, body=None)

def test_chat_rate_limit_is_503_with_retry_after(monkeypatch):
    import groq
    FakeVS.results = RESULTS
    monkeypatch.setattr(main, "ChatGroq", _llm_raising(_groq_error(groq.RateLimitError, 429)))
    r = client.post("/chat", json={"question": "q"})
    assert r.status_code == 503 and r.headers["retry-after"] == "30" and "limite" in r.json()["detail"]

def test_chat_groq_error_is_502(monkeypatch):
    import groq
    FakeVS.results = RESULTS
    monkeypatch.setattr(main, "ChatGroq", _llm_raising(_groq_error(groq.InternalServerError, 500)))
    assert client.post("/chat", json={"question": "q"}).status_code == 502

def test_answer_llm_has_max_tokens(monkeypatch):
    seen = {}
    def fake(**kw):
        seen.update(kw); return FakeListChatModel(responses=["ok"] * 10)
    monkeypatch.setattr(main, "ChatGroq", fake)
    FakeVS.results = RESULTS
    assert client.post("/chat", json={"question": "q"}).status_code == 200
    assert seen["max_tokens"] == main.GROQ_MAX_TOKENS <= 1000


# ── tradução da pergunta para a busca ──────────────────────────────────────
def _llms(traducao, resposta="resposta final", seen=None):
    """ChatGroq falso: o modelo de tradução devolve `traducao` (ou levanta)."""
    from langchain_core.runnables import RunnableLambda
    def factory(**kw):
        if seen is not None: seen.append(kw)
        if kw["model_name"] == main.TRANSLATE_MODEL:
            if isinstance(traducao, Exception):
                def boom(_): raise traducao
                return RunnableLambda(boom)
            return FakeListChatModel(responses=[traducao])
        return FakeListChatModel(responses=[resposta])
    return factory

def test_search_uses_translated_query_answer_uses_original(monkeypatch):
    seen = []
    monkeypatch.setattr(main, "ChatGroq", _llms('"technology news"\nextra', seen=seen))
    FakeVS.results = RESULTS; FakeVS.queries.clear()
    r = client.post("/chat", json={"question": "quais as notícias de tecnologia?"}).json()
    assert FakeVS.queries == ["technology news"]          # aspas e linhas extras removidas
    assert r["answer"] == "resposta final"
    tr = next(kw for kw in seen if kw["model_name"] == main.TRANSLATE_MODEL)
    assert tr["max_tokens"] <= 256 and tr["max_retries"] == 0

def test_translation_failure_falls_back_to_original(monkeypatch):
    monkeypatch.setattr(main, "ChatGroq", _llms(RuntimeError("groq fora")))
    FakeVS.results = RESULTS; FakeVS.queries.clear()
    r = client.post("/chat", json={"question": "pergunta original"})
    assert r.status_code == 200 and FakeVS.queries == ["pergunta original"]

def test_empty_translation_falls_back_to_original(monkeypatch):
    monkeypatch.setattr(main, "ChatGroq", _llms("   "))
    FakeVS.results = RESULTS; FakeVS.queries.clear()
    client.post("/chat", json={"question": "pergunta original"})
    assert FakeVS.queries == ["pergunta original"]

def test_translation_can_be_disabled(monkeypatch):
    seen = []
    monkeypatch.setattr(main, "TRANSLATE_MODEL", "")
    monkeypatch.setattr(main, "ChatGroq", _llms("nunca usado", seen=seen))
    FakeVS.results = RESULTS; FakeVS.queries.clear()
    client.post("/chat", json={"question": "pergunta original"})
    assert FakeVS.queries == ["pergunta original"] and len(seen) == 1   # só o LLM da resposta


# ── deduplicação contra o banco ─────────────────────────────────────────────
def _fake_connect(on_execute):
    class Cur:
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def execute(s, sql, params=None): on_execute(sql)
        def fetchall(s): return [("l1",), ("l2",)]
    class Conn:
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def cursor(s): return Cur()
    return lambda *a, **k: Conn()

def test_existing_sources_query_is_unambiguous(monkeypatch):
    seen = []
    monkeypatch.setattr(main.psycopg, "connect", _fake_connect(seen.append))
    assert main._get_existing_sources() == {"l1", "l2"}
    import re
    # toda referência a cmetadata precisa do alias da tabela de embeddings
    assert not re.search(r"(?<!e\.)\bcmetadata\b", seen[0])

def test_existing_sources_first_ingest_returns_empty(monkeypatch):
    def boom(sql): raise main.psycopg.errors.UndefinedTable("no table")
    monkeypatch.setattr(main.psycopg, "connect", _fake_connect(boom))
    assert main._get_existing_sources() == set()

def test_ingest_aborts_when_dedup_query_fails(monkeypatch):
    def boom(sql): raise main.psycopg.OperationalError("db down")
    monkeypatch.setattr(main.psycopg, "connect", _fake_connect(boom))
    monkeypatch.setattr(main.feedparser, "parse", lambda url: pytest.fail("não deveria ler feeds"))
    assert client.post("/ingest").status_code == 503
