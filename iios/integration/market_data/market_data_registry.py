"""iios/integration/market_data/market_data_registry.py

Registry for all market data providers.
Thread-safe, ordered by priority.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.market_data.market_data_constants import (
    DEFAULT_MAX_PROVIDERS,
    MarketDataType,
    Exchange,
    InstrumentType,
)
from iios.integration.market_data.market_data_exceptions import (
    MarketDataProviderAlreadyRegisteredError,
    MarketDataProviderNotFoundError,
    MarketDataRegistryError,
)
from iios.integration.market_data.providers.base_market_data_provider import BaseMarketDataProvider

logger = logging.getLogger(__name__)


class MarketDataRegistry:
    """
    Maintains the set of all registered market data providers.

    Supports:
    - Registration / deregistration
    - Lookup by ID
    - Capability-based filtering (find providers for a symbol/data-type)
    """

    def __init__(self, max_providers: int = DEFAULT_MAX_PROVIDERS) -> None:
        self._max    = max_providers
        self._lock   = threading.RLock()
        # Ordered: earlier registrations have higher priority by default
        self._providers: dict[str, BaseMarketDataProvider] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, provider: BaseMarketDataProvider) -> None:
        with self._lock:
            pid = provider.provider_id
            if pid in self._providers:
                raise MarketDataProviderAlreadyRegisteredError(
                    f"Provider '{pid}' is already registered."
                )
            if len(self._providers) >= self._max:
                raise MarketDataRegistryError(
                    f"Registry capacity ({self._max}) reached."
                )
            self._providers[pid] = provider
            logger.info("[MarketDataRegistry] Registered provider '%s'.", pid)

    def unregister(self, provider_id: str) -> None:
        with self._lock:
            if provider_id not in self._providers:
                raise MarketDataProviderNotFoundError(
                    f"Provider '{provider_id}' not found in registry."
                )
            del self._providers[provider_id]
            logger.info("[MarketDataRegistry] Unregistered provider '%s'.", provider_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, provider_id: str) -> BaseMarketDataProvider:
        with self._lock:
            prov = self._providers.get(provider_id)
            if prov is None:
                raise MarketDataProviderNotFoundError(
                    f"Provider '{provider_id}' not found."
                )
            return prov

    def get_all(self) -> list[BaseMarketDataProvider]:
        with self._lock:
            return list(self._providers.values())

    def find_for_data_type(self, data_type: MarketDataType) -> list[BaseMarketDataProvider]:
        with self._lock:
            return [
                p for p in self._providers.values()
                if p.capabilities.supports(data_type)
            ]

    def find_for_exchange(self, exchange: Exchange) -> list[BaseMarketDataProvider]:
        with self._lock:
            return [
                p for p in self._providers.values()
                if p.capabilities.supports_exchange(exchange)
            ]

    def find_for_instrument(self, instrument: InstrumentType) -> list[BaseMarketDataProvider]:
        with self._lock:
            return [
                p for p in self._providers.values()
                if p.capabilities.supports_instrument(instrument)
            ]

    def find_connected(self) -> list[BaseMarketDataProvider]:
        with self._lock:
            return [p for p in self._providers.values() if p.is_connected()]

    def find_streaming(self) -> list[BaseMarketDataProvider]:
        with self._lock:
            return [
                p for p in self._providers.values()
                if p.capabilities.supports_streaming and p.is_connected()
            ]

    def contains(self, provider_id: str) -> bool:
        with self._lock:
            return provider_id in self._providers

    def count(self) -> int:
        with self._lock:
            return len(self._providers)

    def provider_ids(self) -> list[str]:
        with self._lock:
            return list(self._providers.keys())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":     len(self._providers),
                "max":       self._max,
                "connected": sum(1 for p in self._providers.values() if p.is_connected()),
                "ids":       list(self._providers.keys()),
            }
