"""iios/integration/news/classification/tag_generator.py

Generates searchable tags for a news article from topics + entities.
"""
from __future__ import annotations

from typing import Any

from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.news_constants     import DEFAULT_MAX_TAGS


class TagGenerator:
    """
    Produces a deduplicated tag list for an article.

    Sources (priority order):
    1. Explicit tags already set on the article
    2. Company tickers
    3. Classified topics (NewsCategory values)
    4. Extracted countries / sectors
    5. Keywords derived from title words (> 4 chars)
    """

    def __init__(self, max_tags: int = DEFAULT_MAX_TAGS) -> None:
        self._max = max_tags
        self._stats: dict[str, int] = {"generated": 0}

    def generate(self, article: NewsArticle) -> list[str]:
        seen: set[str] = set()
        tags: list[str] = []

        def _add(tag: str) -> None:
            clean = tag.lower().strip()
            if clean and clean not in seen and len(tags) < self._max:
                seen.add(clean)
                tags.append(clean)

        # Existing tags
        for t in article.tags:
            _add(t)

        # Companies
        for c in article.companies:
            _add(c)

        # Categories
        for cat in article.categories:
            _add(cat.value)

        # Topics
        for topic in article.topics:
            _add(topic)

        # Keywords
        for kw in article.keywords:
            _add(kw)

        # Countries / sectors
        for c in article.countries:
            _add(c)
        for s in article.sectors:
            _add(s)

        # Title keywords (words > 4 chars, skip stop-words)
        _STOP = {"about", "after", "their", "which", "could", "would", "there",
                 "other", "these", "those", "where", "while", "since", "until"}
        for word in article.title.split():
            clean = word.strip(".,;:\"'()-").lower()
            if len(clean) > 4 and clean not in _STOP:
                _add(clean)

        self._stats["generated"] += 1
        article.tags = tags
        return tags

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
