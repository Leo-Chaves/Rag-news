import html as html_lib
import logging
import re
from html.parser import HTMLParser
from typing import Any

import feedparser
import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.exceptions import ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class _SimpleHTMLTextExtractor(HTMLParser):
    """Fallback nativo para extrair título e texto de HTML sem dependências externas."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.meta_description: str = ""
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        elif tag_lower == "title":
            self._in_title = True
        elif tag_lower == "meta":
            attr_map = {k.lower(): (v or "") for k, v in attrs}
            if attr_map.get("name", "").lower() == "description" and not self.meta_description:
                self.meta_description = attr_map.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag_lower == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        cleaned = data.strip()
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        else:
            self.text_parts.append(cleaned)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_html(raw: str) -> str:
    """Remove tags HTML residuais comuns em descrições de feeds RSS (ex.: G1)."""
    if not raw:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return _normalize_whitespace(html_lib.unescape(without_tags))


def _normalize_feed_defs(feeds: list[dict[str, str]] | list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in feeds:
        if isinstance(item, str):
            normalized.append({"url": item, "source_name": "Feed", "category": "Geral"})
        else:
            normalized.append(
                {
                    "url": item["url"],
                    "source_name": item.get("source_name", "Feed"),
                    "category": item.get("category", "Geral"),
                }
            )
    return normalized


def _matches_topic(title: str, summary: str, topic_keywords: str | None) -> bool:
    if not topic_keywords:
        return True
    terms = [term.strip().lower() for term in topic_keywords.split(",") if term.strip()]
    if not terms:
        return True
    haystack = f"{title} {summary}".lower()
    return any(term in haystack for term in terms)


def fetch_rss_feed_entries(
    feeds: list[dict[str, str]] | list[str],
    limit: int = 60,
    per_feed_limit: int = 8,
) -> list[dict[str, str]]:
    """
    Lê feeds RSS e retorna lista balanceada (round-robin entre portais) e deduplicada.
    """
    feed_defs = _normalize_feed_defs(feeds)
    buckets: list[list[dict[str, str]]] = []
    seen_links: set[str] = set()

    for feed_def in feed_defs:
        feed_url = feed_def["url"]
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.warning("Falha ao ler feed '%s': %s", feed_url, exc)
            continue

        if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
            continue

        bucket: list[dict[str, str]] = []
        for entry in parsed.entries:
            link = str(entry.get("link", "")).strip() or feed_url
            if link in seen_links:
                continue
            seen_links.add(link)

            title = _strip_html(str(entry.get("title", "")))
            summary = _strip_html(str(entry.get("summary", "") or entry.get("description", "")))
            published = str(entry.get("published", "")).strip()

            bucket.append(
                {
                    "title": title or link,
                    "summary": summary[:450],
                    "url": link,
                    "published_at": published,
                    "feed_url": feed_url,
                    "source_name": feed_def["source_name"],
                    "category": feed_def["category"],
                }
            )
            if len(bucket) >= per_feed_limit:
                break

        if bucket:
            buckets.append(bucket)

    # Intercala os artigos entre os feeds para evitar que um único portal domine o topo
    items: list[dict[str, str]] = []
    idx = 0
    while len(items) < limit:
        added_in_round = False
        for bucket in buckets:
            if idx < len(bucket):
                items.append(bucket[idx])
                added_in_round = True
                if len(items) >= limit:
                    break
        if not added_in_round:
            break
        idx += 1

    return items


def fetch_and_chunk_rss(
    feeds: list[dict[str, str]] | list[str],
    existing_sources: set[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
    topic_keywords: str | None = None,
    max_per_feed: int | None = None,
) -> tuple[list[str], list[dict[str, Any]], int, int]:
    """
    Busca artigos de feeds RSS, aplica deduplicação, filtro opcional por tópico
    e limite por feed, retornando (chunks, metadatas, total_artigos, skipped).
    """
    if existing_sources is None:
        existing_sources = set()

    feed_defs = _normalize_feed_defs(feeds)
    all_docs: list[str] = []
    metadata_list: list[dict[str, Any]] = []
    skipped = 0
    seen_in_batch: set[str] = set()

    for feed_def in feed_defs:
        url = feed_def["url"]
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            logger.warning("Falha ao processar feed '%s': %s", url, exc)
            continue

        if getattr(feed, "bozo", False) and not getattr(feed, "entries", None):
            continue

        processed_from_feed = 0
        for entry in feed.entries:
            if max_per_feed is not None and processed_from_feed >= max_per_feed:
                break

            title = _strip_html(str(entry.get("title", "")))
            summary = _strip_html(str(entry.get("summary", "") or entry.get("description", "")))
            link = str(entry.get("link", url)).strip() or url
            published = str(entry.get("published", "")).strip()

            if not _matches_topic(title, summary, topic_keywords):
                continue

            if link in existing_sources or link in seen_in_batch:
                skipped += 1
                continue

            seen_in_batch.add(link)
            content = f"Título: {title}\n\nResumo: {summary}"
            if content.strip():
                meta: dict[str, Any] = {
                    "source": link,
                    "title": title,
                    "published": published,
                    "source_name": feed_def["source_name"],
                    "category": feed_def["category"],
                }
                if extra_metadata:
                    meta.update(extra_metadata)
                all_docs.append(content)
                metadata_list.append(meta)
                processed_from_feed += 1

    if skipped:
        logger.info("Deduplicação: %d artigos já existentes foram ignorados.", skipped)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks: list[str] = []
    chunk_metadata: list[dict[str, Any]] = []

    for doc, meta in zip(all_docs, metadata_list):
        parts = splitter.split_text(doc)
        chunks.extend(parts)
        chunk_metadata.extend([dict(meta) for _ in parts])

    return chunks, chunk_metadata, len(all_docs), skipped


def extract_article_from_url(url: str) -> dict[str, str]:
    """Faz download de uma página HTML e extrai título, resumo e conteúdo textual."""
    clean_url = (url or "").strip()
    if not clean_url.startswith(("http://", "https://")):
        raise ValidationError("URL inválida; informe um endereço http:// ou https://.")

    try:
        response = httpx.get(
            clean_url,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Não foi possível acessar a URL '{clean_url}': {exc}") from exc

    html = response.text

    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = _normalize_whitespace(soup.title.string) if soup.title and soup.title.string else clean_url
        meta_desc = soup.find("meta", attrs={"name": "description"})
        summary = _normalize_whitespace(str(meta_desc.get("content", ""))) if meta_desc else ""

        paragraphs = [
            _normalize_whitespace(p.get_text(" ", strip=True))
            for p in soup.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if len(p) > 25]
        body_text = "\n\n".join(paragraphs) if paragraphs else _normalize_whitespace(soup.get_text(" ", strip=True))
    except ImportError:
        parser = _SimpleHTMLTextExtractor()
        parser.feed(html)
        title = _normalize_whitespace(" ".join(parser.title_parts)) or clean_url
        summary = _normalize_whitespace(parser.meta_description)
        body_text = _normalize_whitespace(" ".join(parser.text_parts))

    if not summary and body_text:
        summary = body_text[:300].strip()

    if not body_text.strip():
        raise ValidationError("Não foi possível extrair conteúdo textual da URL informada.")

    return {
        "title": title,
        "summary": summary,
        "content": body_text[:15000],
    }


def chunk_single_document(
    title: str,
    text: str,
    metadata: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Divide um único artigo em chunks com metadados prontos para indexação vetorial."""
    clean_text = (text or "").strip()
    if not clean_text:
        return [], []

    document = f"Título: {title}\n\n{clean_text}" if title else clean_text
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    parts = splitter.split_text(document)
    return parts, [dict(metadata) for _ in parts]

