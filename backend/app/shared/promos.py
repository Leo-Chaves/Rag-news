# Itens fixos dos feeds da BBC que só divulgam o app/site, sem notícia. Ficam
# meses no feed e, por serem genéricos, aparecem no topo de buscas genéricas.
PROMO_TITLES = frozenset({"download now", "find out more here"})


def is_promotional_title(title: object) -> bool:
    return str(title or "").strip().lower() in PROMO_TITLES
