"""iios/integration/news/news_registry.py

Thread-safe registry of BaseNewsProvider instances.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.news.news_constants import (
    DEFAULT_MAX_PROVIDERS,
    NewsCategory,
    NewsLanguage,
    NewsRegion,
)
from iios.integration.news.news_exceptions import (
    NewsProviderAlreadyRegisteredError,
    NewsProviderNotFoundError,
    NewsRegistryError,
)
from iios.integration.news.providers.base_news_provider import BaseNewsProvider

logger = logging.getLogger(__name__)


class NewsRegistry:
    """
    Thread-safe store for BaseNewsProvider instances.

    Prevents duplicate registration and enforces capacity limits.
    """

    def __init__(self, max_providers: int = DEFAULT_MAX_PROVIDERS) -> None:
        self._max   = max_providers
        self._lock  = threading.RLock()
        self._store: dict[str, BaseNewsProvider] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, provider: BaseNewsProvider) -> None:
        with self._lock:
            pid = provider.provider_id
            if pid in self._store:
                raise NewsProviderAlreadyRegisteredError(f"Provider '{pid}' already registered.")
            if len(self._store) >= self._max:
                raise NewsRegistryError(f"Registry full ({self._max} providers).")
            self._store[pid] = provider
            logger.info("[NewsRegistry] Registered provider '%s'.", pid)

    def unregister(self, provider_id: str) -> None:
        with self._lock:
            if provider_id not in self._store:
                raise NewsProviderNotFoundError(f"Provider '{provider_id}' not found.")
            del self._store[provider_id]
            logger.info("[NewsRegistry] Unregistered provider '%s'.", provider_id)

    def get(self, provider_id: str) -> BaseNewsProvider:
        with self._lock:
            p = self._store.get(provider_id)
            if p is None:
                raise NewsProviderNotFoundError(f"Provider '{provider_id}' not found.")
            return p

    def has(self, provider_id: str) -> bool:
        with self._lock:
            return provider_id in self._store

    # ── Discovery ─────────────────────────────────────────────────────────────

    def all_providers(self) -> list[BaseNewsProvider]:
        with self._lock:
            return list(self._store.values())

    def find_connected(self) -> list[BaseNewsProvider]:
        with self._lock:
            return [p for p in self._store.values() if p.is_connected()]

    def find_by_category(self, category: NewsCategory) -> list[BaseNewsProvider]:
        with self._lock:
            return [
                p for p in self._store.values()
                if p.capabilities.supports_category(category)
            ]

    def find_by_language(self, language: NewsLanguage) -> list[BaseNewsProvider]:
        with self._lock:
            return [
                p for p in self._store.values()
                if p.capabilities.supports_language(language)
            ]

    def find_by_region(self, region: NewsRegion) -> list[BaseNewsProvider]:
        with self._lock:
            return [
                p for p in self._store.values()
                if p.capabilities.supports_region(region)
            ]

    def find_streaming(self) -> list[BaseNewsProvider]:
        with self._lock:
            return [p for p in self._store.values() if p.capabilities.supports_streaming]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":     len(self._store),
                "connected": sum(1 for p in self._store.values() if p.is_connected()),
                "capacity":  self._max,
            }
