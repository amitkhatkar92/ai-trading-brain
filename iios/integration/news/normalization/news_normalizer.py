"""iios/integration/news/normalization/news_normalizer.py

Normalizes incoming news articles before they enter the pipeline:
- Deduplication by content hash
- Title / body truncation to configured limits
- Whitespace normalization
- Language detection fallback
- Symbol / company name harmonization
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from typing import Any

from iios.integration.news.core.news_article import NewsArticle
from iios.integration.news.news_constants    import (
    NewsLanguage,
    MIN_ARTICLE_TITLE_LEN,
    MIN_ARTICLE_BODY_LEN,
    DEFAULT_MAX_ARTICLE_BODY_CHARS,
)

logger = logging.getLogger(__name__)


class NewsNormalizer:
    """
    Normalizes NewsArticle objects.

    Stateful: maintains a deduplication cache keyed by content hash.
    """

    def __init__(
        self,
        max_title_len: int = 500,
        max_body_len:  int = DEFAULT_MAX_ARTICLE_BODY_CHARS,
        dedup_ttl_sec: int = 3_600,    # how long to remember a seen hash
        symbol_map:    dict[str, str] | None = None,
    ) -> None:
        self._max_title = max_title_len
        self._max_body  = max_body_len
        self._dedup_ttl = dedup_ttl_sec
        self._symbol_map: dict[str, str] = symbol_map or {}

        self._lock      = threading.RLock()
        self._seen:     dict[str, float] = {}   # hash → first_seen ts
        self._stats: dict[str, int] = {
            "normalized": 0,
            "duplicates": 0,
            "truncated":  0,
            "rejected":   0,
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def normalize(self, article: NewsArticle) -> NewsArticle | None:
        """
        Normalize and return the article, or None if it is a duplicate / invalid.
        """
        # Basic validation
        if len(article.title.strip()) < MIN_ARTICLE_TITLE_LEN:
            self._stats["rejected"] += 1
            return None
        if len(article.body.strip()) < MIN_ARTICLE_BODY_LEN and len(article.summary.strip()) < MIN_ARTICLE_BODY_LEN:
            self._stats["rejected"] += 1
            return None

        # Whitespace normalization
        article.title   = self._clean_ws(article.title)
        article.body    = self._clean_ws(article.body)
        article.summary = self._clean_ws(article.summary)

        # Truncation
        if len(article.title) > self._max_title:
            article.title = article.title[: self._max_title - 1] + "…"
            self._stats["truncated"] += 1
        if len(article.body) > self._max_body:
            article.body = article.body[: self._max_body - 1] + "…"
            self._stats["truncated"] += 1

        # Company / symbol normalization
        article.companies = [self._symbol_map.get(c.upper(), c.upper()) for c in article.companies]

        # Language fallback
        if article.language == NewsLanguage.UNKNOWN or article.language is None:
            article.language = NewsLanguage.EN  # default to English

        # Deduplication
        h = self._content_hash(article)
        with self._lock:
            self._expire_cache()
            if h in self._seen:
                self._stats["duplicates"] += 1
                return None
            self._seen[h] = time.time()

        self._stats["normalized"] += 1
        return article

    def normalize_batch(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        result = []
        for a in articles:
            n = self.normalize(a)
            if n is not None:
                result.append(n)
        return result

    def register_symbol(self, raw: str, canonical: str) -> None:
        """Register a symbol alias for normalization."""
        self._symbol_map[raw.upper()] = canonical.upper()

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_ws(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _content_hash(article: NewsArticle) -> str:
        key = f"{article.title}||{article.source_id}||{article.published_at}"
        return hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()

    def _expire_cache(self) -> None:
        """Remove cache entries older than TTL. Must be called under lock."""
        now     = time.time()
        expired = [h for h, ts in self._seen.items() if now - ts > self._dedup_ttl]
        for h in expired:
            del self._seen[h]
