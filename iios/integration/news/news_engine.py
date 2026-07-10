"""iios/integration/news/news_engine.py

Top-level facade and singleton for the News & Alternative Data Framework.

Public API:
    get_news_engine(auto_start=False) -> NewsEngine
    reset_news_engine() -> None
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.integration.news.alternative.alternative_data_engine  import AlternativeDataEngine
from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.core.news_event    import NewsEvent
from iios.integration.news.news_constants     import (
    NewsEngineStatus,
    NEWS_ENGINE_VERSION,
    NEWS_ENGINE_SYSTEM_ID,
)
from iios.integration.news.news_exceptions    import (
    NewsEngineAlreadyRunningError,
    NewsEngineNotRunningError,
)
from iios.integration.news.news_factory  import NewsFactory
from iios.integration.news.news_manager  import NewsManager
from iios.integration.news.news_registry import NewsRegistry
from iios.integration.news.providers.base_news_provider import BaseNewsProvider
from iios.integration.news.providers.paper_news_provider import PaperNewsProvider

logger = logging.getLogger(__name__)


class NewsEngine:
    """
    Top-level facade for the News & Alternative Data Framework.

    Responsibilities:
    - Owns all sub-components (created via NewsFactory)
    - Exposes simplified public API for registration, fetching and search
    - Manages lifecycle (start / stop)
    - Implements singleton pattern via module-level helpers
    """

    def __init__(self) -> None:
        self._factory  = NewsFactory()
        self._status   = NewsEngineStatus.STOPPED
        self._started_at: float | None = None
        self._lock     = threading.RLock()

        # Build component graph
        self._registry    = self._factory.create_registry()
        self._cache       = self._factory.create_cache()
        self._normalizer  = self._factory.create_normalizer()
        self._classifier  = self._factory.create_classification_engine()
        self._publisher   = self._factory.create_publisher()
        self._alt_engine  = self._factory.create_alternative_engine()
        self._monitor     = self._factory.create_monitor()
        self._manager     = NewsManager(
            registry   = self._registry,
            normalizer = self._normalizer,
            classifier = self._classifier,
            cache      = self._cache,
            publisher  = self._publisher,
            monitor    = self._monitor,
            alt_engine = self._alt_engine,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        with self._lock:
            if self._status == NewsEngineStatus.RUNNING:
                raise NewsEngineAlreadyRunningError("NewsEngine is already running.")
            self._status = NewsEngineStatus.INITIALIZING

        self._monitor.start()
        self._started_at = time.time()
        self._status     = NewsEngineStatus.RUNNING
        logger.info(
            "[NewsEngine] v%s started (system_id=%s).",
            NEWS_ENGINE_VERSION, NEWS_ENGINE_SYSTEM_ID,
        )

    async def stop(self) -> None:
        with self._lock:
            if self._status not in (NewsEngineStatus.RUNNING, NewsEngineStatus.INITIALIZING):
                return
            self._status = NewsEngineStatus.STOPPING

        self._monitor.stop()
        self._status = NewsEngineStatus.STOPPED
        logger.info("[NewsEngine] Stopped.")

    def _assert_running(self) -> None:
        if self._status != NewsEngineStatus.RUNNING:
            raise NewsEngineNotRunningError(
                f"NewsEngine is not running (status={self._status.value})."
            )

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: BaseNewsProvider) -> None:
        self._assert_running()
        self._manager.register_provider(provider)

    async def connect_provider(self, provider_id: str) -> None:
        self._assert_running()
        await self._manager.connect_provider(provider_id)

    async def disconnect_provider(self, provider_id: str) -> None:
        await self._manager.disconnect_provider(provider_id)

    # ── Data access ───────────────────────────────────────────────────────────

    async def fetch_articles(
        self,
        query:       str  = "",
        limit:       int  = 20,
        provider_id: str  = "",
        use_cache:   bool = True,
    ) -> list[NewsArticle]:
        self._assert_running()
        return await self._manager.fetch_articles(
            query=query, limit=limit, provider_id=provider_id, use_cache=use_cache
        )

    async def fetch_events(self, provider_id: str = "") -> list[NewsEvent]:
        self._assert_running()
        return await self._manager.fetch_events(provider_id=provider_id)

    async def search_news(self, query: str, limit: int = 10) -> list[NewsArticle]:
        self._assert_running()
        return await self._manager.search_news(query=query, limit=limit)

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def status(self) -> NewsEngineStatus:
        return self._status

    def is_running(self) -> bool:
        return self._status == NewsEngineStatus.RUNNING

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def registry(self) -> NewsRegistry:
        return self._registry

    def alt_engine(self) -> AlternativeDataEngine:
        return self._alt_engine

    def stats(self) -> dict[str, Any]:
        return {
            "version":    NEWS_ENGINE_VERSION,
            "status":     self._status.value,
            "uptime_sec": round(self.uptime_sec(), 2),
            "manager":    self._manager.stats(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance:      NewsEngine | None = None
_instance_lock: threading.Lock    = threading.Lock()


def get_news_engine(auto_start: bool = False) -> NewsEngine:
    """
    Return the module-level NewsEngine singleton.

    If ``auto_start`` is True the engine will be started (via asyncio.run)
    if it is not already running.
    """
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = NewsEngine()
        if auto_start and not _instance.is_running():
            asyncio.run(_instance.start())
        return _instance


def reset_news_engine() -> None:
    """Destroy the singleton. The next call to get_news_engine creates a fresh one."""
    global _instance
    with _instance_lock:
        if _instance is not None and _instance.is_running():
            try:
                asyncio.run(_instance.stop())
            except Exception:
                pass
        _instance = None
