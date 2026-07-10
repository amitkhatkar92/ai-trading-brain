"""iios/integration/market_data/market_data_manager.py

High-level coordinator.  Ties together registry, streaming,
validation, normalization, cache, and distribution.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from iios.integration.market_data.cache.market_data_cache              import MarketDataCache
from iios.integration.market_data.core.market_candle                   import MarketCandle
from iios.integration.market_data.core.market_event                    import MarketEvent
from iios.integration.market_data.core.market_quote                    import MarketQuote
from iios.integration.market_data.core.market_snapshot                 import MarketSnapshot
from iios.integration.market_data.distribution.market_event_publisher  import MarketEventPublisher
from iios.integration.market_data.historical.historical_data_manager   import HistoricalDataManager
from iios.integration.market_data.market_data_constants                import (
    CandleInterval,
    MarketDataType,
    MarketEventType,
    Exchange,
    InstrumentType,
)
from iios.integration.market_data.market_data_exceptions               import (
    NoProviderForSymbolError,
)
from iios.integration.market_data.market_data_registry                 import MarketDataRegistry
from iios.integration.market_data.monitoring.market_data_monitor       import MarketDataMonitor
from iios.integration.market_data.normalization.market_normalizer      import MarketNormalizer
from iios.integration.market_data.providers.base_market_data_provider  import BaseMarketDataProvider
from iios.integration.market_data.providers.market_data_session        import SubscriptionHandle
from iios.integration.market_data.streaming.stream_manager             import StreamManager
from iios.integration.market_data.validation.market_validator          import MarketValidator

logger = logging.getLogger(__name__)


class MarketDataManager:
    """
    Facade for all market data operations.

    The MarketDataEngine owns one MarketDataManager.
    External callers (strategy layer, analytics, etc.) interact only
    with this class — not directly with providers.
    """

    def __init__(
        self,
        registry:           MarketDataRegistry,
        stream_manager:     StreamManager,
        publisher:          MarketEventPublisher,
        normalizer:         MarketNormalizer,
        validator:          MarketValidator,
        cache:              MarketDataCache[Any],
        historical:         HistoricalDataManager,
        monitor:            MarketDataMonitor,
    ) -> None:
        self._registry    = registry
        self._streaming   = stream_manager
        self._publisher   = publisher
        self._normalizer  = normalizer
        self._validator   = validator
        self._cache       = cache
        self._historical  = historical
        self._monitor     = monitor
        self._stats: dict[str, int] = {
            "snapshots_fetched":  0,
            "historical_fetched": 0,
            "subscriptions_made": 0,
            "events_published":   0,
        }

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: BaseMarketDataProvider) -> None:
        self._registry.register(provider)
        self._monitor.register_provider(provider)
        self._historical.register_provider(provider)
        logger.info("[MarketDataManager] Provider '%s' registered.", provider.provider_id)

    def unregister_provider(self, provider_id: str) -> None:
        self._registry.unregister(provider_id)
        self._monitor.unregister_provider(provider_id)
        self._historical.unregister_provider(provider_id)

    async def connect_provider(self, provider_id: str) -> None:
        prov = self._registry.get(provider_id)
        await prov.connect()
        logger.info("[MarketDataManager] Connected '%s'.", provider_id)

    async def disconnect_provider(self, provider_id: str) -> None:
        prov = self._registry.get(provider_id)
        await prov.disconnect()

    # ── Snapshots ─────────────────────────────────────────────────────────────

    async def fetch_snapshot(
        self,
        symbols:     list[str],
        provider_id: str | None = None,
        use_cache:   bool = True,
    ) -> list[MarketSnapshot]:
        if use_cache:
            cached = []
            missing = []
            for sym in symbols:
                v = self._cache.get(f"snap:{sym}")
                if v is not None:
                    cached.append(v)
                else:
                    missing.append(sym)
            symbols = missing
            if not symbols:
                return cached
        else:
            cached = []

        prov = self._resolve_provider(provider_id, MarketDataType.SNAPSHOT)
        snaps = await prov.fetch_snapshot(symbols)
        result = []
        for snap in snaps:
            snap = self._normalizer.normalize_snapshot(snap)
            issues = self._validator.validate_snapshot(snap)
            if not issues:
                self._cache.put(f"snap:{snap.symbol}", snap, ttl_sec=10.0)
            result.append(snap)
            self._publish_event(snap, MarketEventType.SNAPSHOT_TAKEN, snap.symbol, prov.provider_id)

        self._stats["snapshots_fetched"] += len(result)
        return cached + result

    # ── Historical ────────────────────────────────────────────────────────────

    async def fetch_historical(
        self,
        symbol:      str,
        start:       float,
        end:         float,
        interval:    CandleInterval = CandleInterval.D1,
        provider_id: str | None = None,
        use_cache:   bool = True,
    ) -> list[MarketCandle]:
        cache_key = f"hist:{symbol}:{interval.value}:{int(start)}-{int(end)}"
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore[return-value]

        candles = await self._historical.fetch(symbol, start, end, interval, provider_id)
        normalized = [self._normalizer.normalize_candle(c) for c in candles]
        if use_cache:
            self._cache.put(cache_key, normalized, ttl_sec=300.0)
        self._stats["historical_fetched"] += len(normalized)
        return normalized

    # ── Subscriptions ─────────────────────────────────────────────────────────

    async def subscribe(
        self,
        symbols:     list[str],
        data_types:  list[MarketDataType],
        provider_id: str | None = None,
    ) -> SubscriptionHandle:
        prov = self._resolve_provider(
            provider_id,
            data_types[0] if data_types else MarketDataType.QUOTE,
        )
        handle = await prov.subscribe(symbols, [dt.value for dt in data_types])
        self._streaming.create_subscription(
            prov.provider_id, symbols, data_types, sub_id=handle.handle_id
        )
        self._stats["subscriptions_made"] += 1
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        prov = self._registry.get(handle.provider_id)
        await prov.unsubscribe(handle)
        self._streaming.remove_subscription(handle.handle_id)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "registry":   self._registry.stats(),
            "cache":      self._cache.stats(),
            "streaming":  self._streaming.stats(),
            "monitor":    self._monitor.stats(),
            "publisher":  self._publisher.stats(),
            "validator":  self._validator.stats(),
            "normalizer": self._normalizer.stats(),
        }

    def is_all_healthy(self) -> bool:
        return self._monitor.is_all_healthy()

    # ── Internals ──────────────────────────────────────────────────────────────

    def _resolve_provider(
        self, provider_id: str | None, data_type: MarketDataType
    ) -> BaseMarketDataProvider:
        if provider_id:
            return self._registry.get(provider_id)
        candidates = self._registry.find_for_data_type(data_type)
        connected  = [p for p in candidates if p.is_connected()]
        if connected:
            return connected[0]
        if candidates:
            return candidates[0]
        raise NoProviderForSymbolError(
            f"No provider registered for data type '{data_type.value}'."
        )

    def _publish_event(
        self, payload: Any, event_type: MarketEventType, symbol: str, source: str
    ) -> None:
        try:
            self._publisher.publish_payload(payload, event_type, symbol, source)
            self._stats["events_published"] += 1
        except Exception as exc:
            logger.warning("[MarketDataManager] Publish error: %s", exc)
