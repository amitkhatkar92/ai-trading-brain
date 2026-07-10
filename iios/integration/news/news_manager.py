"""iios/integration/news/news_manager.py

High-level coordinator for the news pipeline.

Coordinates:
 - NewsRegistry  (provider store)
 - NewsNormalizer (dedup / clean)
 - ClassificationEngine (topics / entities / tags)
 - NewsDataCache (article caching)
 - NewsEventPublisher (fan-out)
 - NewsMonitor (background health polling)
 - AlternativeDataEngine (alt data)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from iios.integration.news.alternative.alternative_data_engine  import AlternativeDataEngine
from iios.integration.news.cache                                import NewsDataCache
from iios.integration.news.classification.classification_engine import ClassificationEngine
from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.core.news_event    import NewsEvent
from iios.integration.news.distribution.news_event_publisher import NewsEventPublisher
from iios.integration.news.monitoring.news_monitor           import NewsMonitor
from iios.integration.news.news_context   import NewsContext
from iios.integration.news.news_exceptions import (
    NoNewsProviderAvailableError,
    NewsProviderNotFoundError,
)
from iios.integration.news.news_registry  import NewsRegistry
from iios.integration.news.normalization.news_normalizer import NewsNormalizer
from iios.integration.news.providers.base_news_provider  import BaseNewsProvider

logger = logging.getLogger(__name__)


class NewsManager:
    """
    High-level coordinator for all news data operations.
    """

    def __init__(
        self,
        registry:       NewsRegistry,
        normalizer:     NewsNormalizer,
        classifier:     ClassificationEngine,
        cache:          NewsDataCache,
        publisher:      NewsEventPublisher,
        monitor:        NewsMonitor,
        alt_engine:     AlternativeDataEngine,
    ) -> None:
        self._registry   = registry
        self._normalizer = normalizer
        self._classifier = classifier
        self._cache      = cache
        self._publisher  = publisher
        self._monitor    = monitor
        self._alt        = alt_engine
        self._stats: dict[str, int] = {
            "fetched":     0,
            "published":   0,
            "cache_hits":  0,
        }

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: BaseNewsProvider) -> None:
        self._registry.register(provider)
        self._monitor.register(provider)
        logger.info("[NewsManager] Provider '%s' registered.", provider.provider_id)

    async def connect_provider(self, provider_id: str) -> None:
        provider = self._registry.get(provider_id)
        await provider.connect()
        logger.info("[NewsManager] Provider '%s' connected.", provider_id)

    async def disconnect_provider(self, provider_id: str) -> None:
        provider = self._registry.get(provider_id)
        await provider.disconnect()

    # ── Article fetch ─────────────────────────────────────────────────────────

    async def fetch_articles(
        self,
        query:       str   = "",
        limit:       int   = 20,
        provider_id: str   = "",
        use_cache:   bool  = True,
    ) -> list[NewsArticle]:
        cache_key = f"fetch:{provider_id}:{query}:{limit}"
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                return cached

        providers = (
            [self._registry.get(provider_id)]
            if provider_id
            else self._registry.find_connected()
        )
        if not providers:
            raise NoNewsProviderAvailableError("No connected providers available.")

        all_articles: list[NewsArticle] = []
        for prov in providers:
            with NewsContext.scope(prov.provider_id, query, "fetch_articles"):
                try:
                    articles = await prov.fetch_articles(query=query, limit=limit)
                    all_articles.extend(articles)
                except Exception as exc:
                    logger.warning("[NewsManager] fetch_articles error from '%s': %s", prov.provider_id, exc)

        # Normalize → classify → publish
        normalized = self._normalizer.normalize_batch(all_articles)
        classified = self._classifier.classify_batch(normalized)

        for art in classified:
            self._publisher.publish(art)

        self._stats["fetched"]    += len(classified)
        self._stats["published"]  += len(classified)

        if use_cache and classified:
            self._cache.set(cache_key, classified)

        return classified

    # ── Event fetch ───────────────────────────────────────────────────────────

    async def fetch_events(
        self,
        provider_id: str = "",
    ) -> list[NewsEvent]:
        providers = (
            [self._registry.get(provider_id)]
            if provider_id
            else self._registry.find_connected()
        )
        if not providers:
            raise NoNewsProviderAvailableError("No connected providers available.")

        results: list[NewsEvent] = []
        for prov in providers:
            try:
                events = await prov.fetch_events()
                results.extend(events)
            except Exception as exc:
                logger.warning("[NewsManager] fetch_events error from '%s': %s", prov.provider_id, exc)
        return results

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_news(self, query: str, limit: int = 10) -> list[NewsArticle]:
        providers = self._registry.find_connected()
        if not providers:
            raise NoNewsProviderAvailableError("No connected providers available.")

        results: list[NewsArticle] = []
        for prov in providers:
            try:
                arts = await prov.search_news(query=query, limit=limit)
                results.extend(arts)
            except Exception as exc:
                logger.warning("[NewsManager] search_news error from '%s': %s", prov.provider_id, exc)
        return results

    # ── Misc ──────────────────────────────────────────────────────────────────

    def registry(self) -> NewsRegistry:
        return self._registry

    def cache(self) -> NewsDataCache:
        return self._cache

    def publisher(self) -> NewsEventPublisher:
        return self._publisher

    def alt_engine(self) -> AlternativeDataEngine:
        return self._alt

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "registry":   self._registry.stats(),
            "cache":      self._cache.stats(),
            "classifier": self._classifier.stats(),
            "normalizer": self._normalizer.stats(),
            "publisher":  self._publisher.stats(),
            "monitor":    self._monitor.stats(),
        }
