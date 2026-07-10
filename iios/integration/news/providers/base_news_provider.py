"""iios/integration/news/providers/base_news_provider.py

Abstract base class for all news/alternative-data providers.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.core.news_event    import NewsEvent
from iios.integration.news.core.news_headline import NewsHeadline
from iios.integration.news.news_constants     import NewsProviderStatus
from iios.integration.news.news_exceptions    import NewsProviderNotConnectedError
from iios.integration.news.providers.news_session           import NewsSession
from iios.integration.news.providers.provider_capabilities  import NewsProviderCapabilities
from iios.integration.news.providers.provider_health        import NewsProviderHealth
from iios.integration.news.providers.provider_metadata      import NewsProviderMetadata

logger = logging.getLogger(__name__)


class BaseNewsProvider(ABC):
    """
    Abstract base for all news and alternative-data providers.

    Lifecycle
    ---------
    1. Instantiate
    2. ``await provider.connect()``
    3. Use: ``fetch_articles``, ``stream_news``, ``search_news``, etc.
    4. ``await provider.disconnect()``
    """

    def __init__(self) -> None:
        self._session:      NewsSession | None = None
        self._connected_at: float = 0.0
        self._stats: dict[str, int | float] = {
            "articles_fetched":  0,
            "events_fetched":    0,
            "errors":            0,
        }

    # ── Identity ───────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique, stable machine-readable identifier."""

    @property
    @abstractmethod
    def capabilities(self) -> NewsProviderCapabilities:
        """Static capability declaration."""

    @property
    @abstractmethod
    def metadata(self) -> NewsProviderMetadata:
        """Static descriptive info."""

    # ── Connection ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """Open connection/session with the provider."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close all streams and release resources."""

    # ── Fetch ──────────────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_articles(
        self,
        query:   str = "",
        limit:   int = 10,
        from_ts: float = 0.0,
        to_ts:   float = 0.0,
    ) -> list[NewsArticle]:
        """
        Fetch a batch of articles matching the query/time range.
        """

    @abstractmethod
    async def fetch_events(
        self,
        from_ts: float = 0.0,
        to_ts:   float = 0.0,
    ) -> list[NewsEvent]:
        """
        Fetch structured financial/corporate events.
        """

    @abstractmethod
    async def search_news(
        self,
        query:   str,
        limit:   int = 10,
    ) -> list[NewsArticle]:
        """
        Full-text / semantic search across the provider's news corpus.
        """

    # ── Streaming ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def stream_news(self) -> AsyncGenerator[NewsArticle, None]:
        """
        Yield real-time news articles as they are published.
        """
        if False:  # pragma: no cover
            yield NewsArticle()

    @abstractmethod
    async def stream_alerts(self) -> AsyncGenerator[NewsHeadline, None]:
        """
        Yield breaking-news headlines with minimal latency.
        """
        if False:  # pragma: no cover
            yield NewsHeadline()

    # ── Health ─────────────────────────────────────────────────────────────────

    @abstractmethod
    async def health_check(self) -> NewsProviderHealth:
        """Return a snapshot of this provider's health."""

    # ── Helpers ────────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._session is not None and self._session.is_connected()

    def _assert_connected(self) -> None:
        if not self.is_connected():
            raise NewsProviderNotConnectedError(
                f"Provider '{self.provider_id}' is not connected."
            )

    def _base_health(self) -> NewsProviderHealth:
        uptime = time.time() - self._connected_at if self._connected_at > 0 else 0.0
        return NewsProviderHealth(
            provider_id     = self.provider_id,
            is_connected    = self.is_connected(),
            is_streaming    = (
                self._session is not None
                and self._session.status == NewsProviderStatus.STREAMING
            ),
            last_article_at = self._session.last_active if self._session else 0.0,
            error_count     = int(self._stats.get("errors", 0)),
            uptime_sec      = uptime,
        )

    def _on_article_delivered(self) -> None:
        self._stats["articles_fetched"] = int(self._stats.get("articles_fetched", 0)) + 1
        if self._session:
            self._session.touch()

    def _on_error(self, error: Exception) -> None:
        self._stats["errors"] = int(self._stats.get("errors", 0)) + 1
        if self._session:
            self._session.record_error()
        logger.error("[%s] Error: %s", self.provider_id, error)

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": (
                self._session.status.value if self._session
                else NewsProviderStatus.DISCONNECTED.value
            ),
            **self._stats,
        }
