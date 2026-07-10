"""iios/integration/registry/capability_registry.py

Routes queries to providers based on capability matching.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.integration.integration_constants import DataCategory, DataFrequency
from iios.integration.providers.provider_registry import ProviderRegistry
from iios.integration.providers.base_provider import BaseProvider


class CapabilityRegistry:
    """
    Answers the question: 'Which active providers can serve this request?'

    Used by IntegrationManager for routing before calling providers.
    """

    def __init__(self, provider_registry: ProviderRegistry) -> None:
        self._registry = provider_registry
        self._lock     = threading.RLock()

    def route(
        self,
        category:     str,
        frequency:    str | None = None,
        symbol_space: str | None = None,
        active_only:  bool = True,
    ) -> list[BaseProvider]:
        """
        Return ordered list of providers capable of serving this request.

        Providers are sorted by priority (ascending = highest priority first).
        """
        candidates = self._registry.providers_for_category(
            category, frequency, active_only=active_only
        )
        if symbol_space:
            candidates = [
                p for p in candidates
                if p.capabilities.supports_symbol_space(symbol_space)
            ]
        return candidates

    def best_provider(
        self,
        category:     str,
        frequency:    str | None = None,
        symbol_space: str | None = None,
    ) -> BaseProvider | None:
        providers = self.route(category, frequency, symbol_space)
        return providers[0] if providers else None

    def has_coverage(
        self,
        category: str,
        frequency: str | None = None,
    ) -> bool:
        return len(self.route(category, frequency)) > 0

    def statistics(self) -> dict[str, Any]:
        return self._registry.statistics()
