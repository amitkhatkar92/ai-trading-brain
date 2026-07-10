"""iios/integration/providers/provider_registry.py

Thread-safe registry of all registered providers.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.integration.integration_constants import (
    DataCategory,
    DataFrequency,
    ProviderStatus,
    DEFAULT_MAX_PROVIDERS,
)
from iios.integration.integration_exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError,
    RegistryCapacityError,
)
from iios.integration.providers.base_provider import BaseProvider


class ProviderRegistry:
    """
    Stores and indexes all registered BaseProvider instances.

    Supports lookup by:
      - provider_id (exact)
      - category + frequency (routing)
      - status
    """

    def __init__(self, max_providers: int = DEFAULT_MAX_PROVIDERS) -> None:
        self._providers: dict[str, BaseProvider]        = {}
        self._by_category: dict[str, list[str]]         = {}  # category → [provider_id]
        self._max_providers = max_providers
        self._lock          = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, provider: BaseProvider) -> None:
        pid = provider.provider_id
        with self._lock:
            if pid in self._providers:
                raise ProviderAlreadyRegisteredError(
                    f"Provider '{pid}' is already registered"
                )
            if len(self._providers) >= self._max_providers:
                raise RegistryCapacityError(
                    f"Provider registry capacity ({self._max_providers}) exceeded"
                )
            self._providers[pid] = provider
            for cat in provider.capabilities.categories:
                self._by_category.setdefault(cat, [])
                if pid not in self._by_category[cat]:
                    self._by_category[cat].append(pid)

    def unregister(self, provider_id: str) -> None:
        with self._lock:
            if provider_id not in self._providers:
                raise ProviderNotFoundError(f"Provider '{provider_id}' not found")
            provider = self._providers.pop(provider_id)
            for cat in provider.capabilities.categories:
                if cat in self._by_category:
                    self._by_category[cat] = [
                        p for p in self._by_category[cat] if p != provider_id
                    ]

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, provider_id: str) -> BaseProvider:
        with self._lock:
            p = self._providers.get(provider_id)
        if p is None:
            raise ProviderNotFoundError(f"Provider '{provider_id}' not found")
        return p

    def has(self, provider_id: str) -> bool:
        with self._lock:
            return provider_id in self._providers

    def all_providers(self) -> list[BaseProvider]:
        with self._lock:
            return list(self._providers.values())

    def active_providers(self) -> list[BaseProvider]:
        with self._lock:
            return [p for p in self._providers.values() if p.is_active()]

    def providers_for_category(
        self,
        category: str,
        frequency: str | None = None,
        active_only: bool = True,
    ) -> list[BaseProvider]:
        """
        Return providers that handle *category*, sorted by priority (ascending).
        """
        with self._lock:
            ids = list(self._by_category.get(category, []))
            providers = [self._providers[i] for i in ids if i in self._providers]
        if frequency:
            providers = [p for p in providers if p.can_handle(category, frequency)]
        if active_only:
            providers = [p for p in providers if p.is_active()]
        return sorted(providers, key=lambda p: p.priority.value)

    def providers_by_ids(self, provider_ids: list[str]) -> list[BaseProvider]:
        result = []
        with self._lock:
            for pid in provider_ids:
                if pid in self._providers:
                    result.append(self._providers[pid])
        return result

    def provider_ids(self) -> list[str]:
        with self._lock:
            return list(self._providers.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._providers)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            active = sum(1 for p in self._providers.values() if p.is_active())
            return {
                "total":    len(self._providers),
                "active":   active,
                "inactive": len(self._providers) - active,
                "categories": {
                    cat: len(ids)
                    for cat, ids in self._by_category.items()
                },
            }
