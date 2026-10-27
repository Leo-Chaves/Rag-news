"""
Taxonomia de temas e mapeamento feed RSS -> tema.

Cada notícia ingerida recebe `category` (slug do tema) na metadata do PGVector.
Os temas são hierárquicos: escolher "esportes" inclui "futebol", "tenis" etc.
"""
from typing import Dict, Iterable, List, Optional, Set, TypedDict


class Topic(TypedDict):
    slug: str
    name: str
    parent: Optional[str]


# Ordem importa só para exibição no frontend (pais seguidos dos filhos).
TOPICS: List[Topic] = [
    {"slug": "mundo", "name": "Mundo", "parent": None},
    {"slug": "politica", "name": "Política", "parent": None},
    {"slug": "negocios", "name": "Negócios e Economia", "parent": None},
    {"slug": "tecnologia", "name": "Tecnologia", "parent": None},
    {"slug": "ciencia", "name": "Ciência e Meio Ambiente", "parent": None},
    {"slug": "saude", "name": "Saúde", "parent": None},
    {"slug": "cultura", "name": "Cultura e Entretenimento", "parent": None},
    {"slug": "esportes", "name": "Esportes", "parent": None},
    {"slug": "futebol", "name": "Futebol", "parent": "esportes"},
    {"slug": "tenis", "name": "Tênis", "parent": "esportes"},
    {"slug": "formula1", "name": "Fórmula 1", "parent": "esportes"},
    {"slug": "basquete", "name": "Basquete", "parent": "esportes"},
]

TOPICS_BY_SLUG: Dict[str, Topic] = {t["slug"]: t for t in TOPICS}

# Categoria para o feed geral (manchetes). Não é selecionável como preferência.
CATEGORIA_GERAL = "geral"

BBC = "https://feeds.bbci.co.uk"

# (url, categoria). Feeds ESPECÍFICOS vêm antes dos genéricos: se a mesma
# notícia aparece em dois feeds, a primeira ocorrência define a categoria
# (ex.: uma matéria de futebol que também está em "sport/rss.xml" fica como
# "futebol", não "esportes"; uma manchete que também está em "world" fica "mundo").
RSS_FEEDS: List[tuple[str, str]] = [
    (f"{BBC}/sport/football/rss.xml", "futebol"),
    (f"{BBC}/sport/tennis/rss.xml", "tenis"),
    (f"{BBC}/sport/formula1/rss.xml", "formula1"),
    (f"{BBC}/sport/basketball/rss.xml", "basquete"),
    (f"{BBC}/sport/rss.xml", "esportes"),
    (f"{BBC}/news/politics/rss.xml", "politica"),
    (f"{BBC}/news/technology/rss.xml", "tecnologia"),
    (f"{BBC}/news/business/rss.xml", "negocios"),
    (f"{BBC}/news/science_and_environment/rss.xml", "ciencia"),
    (f"{BBC}/news/health/rss.xml", "saude"),
    (f"{BBC}/news/entertainment_and_arts/rss.xml", "cultura"),
    (f"{BBC}/news/world/rss.xml", "mundo"),
    (f"{BBC}/news/rss.xml", CATEGORIA_GERAL),
]


def children_of(slug: str) -> List[str]:
    return [t["slug"] for t in TOPICS if t["parent"] == slug]


def expand_topics(slugs: Iterable[str]) -> Set[str]:
    """Inclui os subtemas: {"esportes"} -> {"esportes", "futebol", "tenis", ...}."""
    result: Set[str] = set()
    stack = [s for s in slugs if s in TOPICS_BY_SLUG]
    while stack:
        slug = stack.pop()
        if slug in result:
            continue
        result.add(slug)
        stack.extend(children_of(slug))
    return result


def normalize_topics(slugs: Iterable[str]) -> List[str]:
    """
    Valida e normaliza a lista enviada pelo usuário.
    Levanta ValueError com os slugs desconhecidos. Remove duplicatas e
    filhos redundantes (se "esportes" está marcado, "futebol" é implícito).
    """
    slugs = list(dict.fromkeys(slugs))  # dedup preservando ordem
    unknown = [s for s in slugs if s not in TOPICS_BY_SLUG]
    if unknown:
        raise ValueError(f"Temas desconhecidos: {', '.join(unknown)}")
    chosen = set(slugs)

    def has_selected_ancestor(slug: str) -> bool:
        parent = TOPICS_BY_SLUG[slug]["parent"]
        while parent:
            if parent in chosen:
                return True
            parent = TOPICS_BY_SLUG[parent]["parent"]
        return False

    order = {t["slug"]: i for i, t in enumerate(TOPICS)}
    return sorted((s for s in slugs if not has_selected_ancestor(s)), key=order.get)
