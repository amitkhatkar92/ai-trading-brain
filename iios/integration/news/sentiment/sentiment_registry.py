"""iios/integration/news/sentiment/sentiment_registry.py

Registry of pluggable SentimentProvider implementations.
"""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from iios.integration.news.core.news_article import NewsArticle
from iios.integration.news.news_constants    import SentimentScope
from iios.integration.news.sentiment.sentiment_result import SentimentResult

logger = logging.getLogger(__name__)


class BaseSentimentProvider(ABC):
    """
    Abstract base for all sentiment analysis plug-ins.

    Implementations may use lexicon-based scoring, ML models, or external APIs.
    The framework never calls NLP libraries directly.
    """

    @property
    @abstractmethod
    def analyzer_id(self) -> str:
        """Unique stable identifier."""

    @property
    @abstractmethod
    def supported_scopes(self) -> list[SentimentScope]:
        """Which SentimentScopes this analyzer supports."""

    @abstractmethod
    def analyze_article(self, article: NewsArticle) -> SentimentResult:
        """Run sentiment analysis on a full article."""

    def analyze_text(self, text: str, subject_id: str = "") -> SentimentResult:
        """
        Convenience: analyze raw text.
        Default implementation creates a minimal article and delegates.
        """
        art = NewsArticle(title=text, summary=text, body=text)
        result = self.analyze_article(art)
        result.subject_id = subject_id
        return result


class SentimentRegistry:
    """
    Manages all registered sentiment providers.
    """

    def __init__(self) -> None:
        self._lock:      threading.RLock = threading.RLock()
        self._providers: dict[str, BaseSentimentProvider] = {}

    def register(self, provider: BaseSentimentProvider) -> None:
        with self._lock:
            self._providers[provider.analyzer_id] = provider
            logger.info("[SentimentRegistry] Registered '%s'.", provider.analyzer_id)

    def unregister(self, analyzer_id: str) -> None:
        with self._lock:
            self._providers.pop(analyzer_id, None)

    def get(self, analyzer_id: str) -> BaseSentimentProvider | None:
        with self._lock:
            return self._providers.get(analyzer_id)

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._providers.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._providers)

    def find_for_scope(self, scope: SentimentScope) -> list[BaseSentimentProvider]:
        with self._lock:
            return [p for p in self._providers.values() if scope in p.supported_scopes]
