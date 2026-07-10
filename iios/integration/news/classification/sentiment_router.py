"""iios/integration/news/classification/sentiment_router.py

Routes articles to registered sentiment analyzers.

The router does NOT implement any sentiment analysis — it only dispatches
articles to plugged-in SentimentProvider implementations.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from iios.integration.news.core.news_article import NewsArticle

logger = logging.getLogger(__name__)

# Sentiment provider callback type: (NewsArticle) → (score: float, label: str)
SentimentCallback = Callable[[NewsArticle], tuple[float, str]]


class SentimentRouter:
    """
    Routes a NewsArticle to zero or more pluggable sentiment analyzers.

    Each analyzer is registered with a name and called in registration order.
    The final sentiment_score on the article is the weighted average of all
    analyzer scores.
    """

    def __init__(self) -> None:
        self._lock      = threading.RLock()
        self._analyzers: list[tuple[str, float, SentimentCallback]] = []
        # (name, weight, callback)
        self._stats: dict[str, int] = {"routed": 0, "errors": 0}

    def register(
        self,
        name:     str,
        callback: SentimentCallback,
        weight:   float = 1.0,
    ) -> None:
        with self._lock:
            self._analyzers.append((name, weight, callback))
            logger.debug("[SentimentRouter] Registered analyzer '%s'.", name)

    def unregister(self, name: str) -> None:
        with self._lock:
            self._analyzers = [(n, w, cb) for n, w, cb in self._analyzers if n != name]

    def route(self, article: NewsArticle) -> NewsArticle:
        """
        Pass the article through all registered analyzers and update
        article.sentiment_score / article.sentiment with the weighted result.
        """
        with self._lock:
            analyzers = list(self._analyzers)

        if not analyzers:
            return article

        total_weight = 0.0
        weighted_score = 0.0

        for name, weight, callback in analyzers:
            try:
                score, _label = callback(article)
                weighted_score += score * weight
                total_weight   += weight
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("[SentimentRouter] Analyzer '%s' failed: %s", name, exc)

        if total_weight > 0:
            article.sentiment_score = weighted_score / total_weight

        self._stats["routed"] += 1
        return article

    def analyzer_count(self) -> int:
        with self._lock:
            return len(self._analyzers)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
