"""iios/integration/market_data/market_data_engine.py

Top-level facade for the Market Data Provider Framework.

Module singleton — use get_market_data_engine() / reset_market_data_engine().
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.integration.market_data.cache.market_data_cache             import MarketDataCache
from iios.integration.market_data.core.market_candle                  import MarketCandle
from iios.integration.market_data.core.market_snapshot                import MarketSnapshot
from iios.integration.market_data.distribution.market_event_publisher import MarketEventPublisher
from iios.integration.market_data.historical.historical_data_manager  import HistoricalDataManager
from iios.integration.market_data.market_data_constants               import (
    CandleInterval,
    MarketDataEngineStatus,
    MarketDataType,
    MARKET_DATA_ENGINE_VERSION,
)
from iios.integration.market_data.market_data_exceptions              import (
    MarketDataEngineAlreadyRunningError,
    MarketDataEngineNotRunningError,
)
from iios.integration.market_data.market_data_factory                 import MarketDataFactory
from iios.integration.market_data.market_data_manager                 import MarketDataManager
from iios.integration.market_data.market_data_registry                import MarketDataRegistry
from iios.integration.market_data.monitoring.market_data_monitor      import MarketDataMonitor
from iios.integration.market_data.normalization.market_normalizer     import MarketNormalizer
from iios.integration.market_data.providers.base_market_data_provider import BaseMarketDataProvider
from iios.integration.market_data.providers.market_data_session       import SubscriptionHandle
from iios.integration.market_data.streaming.stream_manager            import StreamManager
from iios.integration.market_data.validation.market_validator         import MarketValidator

logger = logging.getLogger(__name__)


class MarketDataEngine:
    """
    Top-level entry point for the Market Data Provider Framework.

    Responsibilities:
    - Own and initialise all sub-components
    - Manage provider lifecycle (register, connect, disconnect)
    - Expose a clean public API to the rest of IIOS
    - Track engine-level statistics

    Lifecycle::

        engine = get_market_data_engine()
        await engine.start()
        engine.register_provider(PaperMarketProvider())
        await engine.connect_provider("paper_market")
        snaps = await engine.fetch_snapshot(["AAPL", "GOOG"])
        await engine.stop()
    """

    def __init__(self) -> None:
        self._status     = MarketDataEngineStatus.STOPPED
        self._started_at = 0.0
        self._lock       = threading.RLock()

        # Build component graph via factory
        self._registry   = MarketDataRegistry()
        self._stream_mgr = MarketDataFactory.create_stream_manager()
        self._publisher  = MarketDataFactory.create_publisher(self._stream_mgr)
        self._normalizer = MarketDataFactory.create_market_normalizer()
        self._validator  = MarketDataFactory.create_market_validator()
        self._cache      = MarketDataFactory.create_cache(name="market_data_engine")
        self._historical = MarketDataFactory.create_historical_manager()
        self._monitor    = MarketDataFactory.create_monitor()

        self._manager = MarketDataManager(
            registry       = self._registry,
            stream_manager = self._stream_mgr,
            publisher      = self._publisher,
            normalizer     = self._normalizer,
            validator      = self._validator,
            cache          = self._cache,
            historical     = self._historical,
            monitor        = self._monitor,
        )
        self._stats: dict[str, int | str] = {
            "version": MARKET_DATA_ENGINE_VERSION,
            "starts":  0,
            "stops":   0,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        with self._lock:
            if self._status == MarketDataEngineStatus.RUNNING:
                raise MarketDataEngineAlreadyRunningError(
                    "MarketDataEngine is already running."
                )
            self._status     = MarketDataEngineStatus.INITIALIZING
            self._started_at = time.time()

        await self._monitor.start()
        with self._lock:
            self._status = MarketDataEngineStatus.RUNNING
            self._stats["starts"] = int(self._stats.get("starts", 0)) + 1
        logger.info(
            "[MarketDataEngine] Started (v%s).", MARKET_DATA_ENGINE_VERSION
        )

    async def stop(self) -> None:
        with self._lock:
            if self._status not in (
                MarketDataEngineStatus.RUNNING, MarketDataEngineStatus.DEGRADED
            ):
                return
            self._status = MarketDataEngineStatus.STOPPING

        # Disconnect all connected providers
        for prov in self._registry.find_connected():
            try:
                await prov.disconnect()
            except Exception as exc:
                logger.warning("[MarketDataEngine] Error disconnecting %s: %s", prov.provider_id, exc)

        await self._monitor.stop()
        with self._lock:
            self._status = MarketDataEngineStatus.STOPPED
            self._stats["stops"] = int(self._stats.get("stops", 0)) + 1
        logger.info("[MarketDataEngine] Stopped.")

    def _assert_running(self) -> None:
        if self._status not in (MarketDataEngineStatus.RUNNING, MarketDataEngineStatus.DEGRADED):
            raise MarketDataEngineNotRunningError(
                "MarketDataEngine is not running. Call start() first."
            )

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: BaseMarketDataProvider) -> None:
        self._assert_running()
        self._manager.register_provider(provider)

    def unregister_provider(self, provider_id: str) -> None:
        self._assert_running()
        self._manager.unregister_provider(provider_id)

    async def connect_provider(self, provider_id: str) -> None:
        self._assert_running()
        await self._manager.connect_provider(provider_id)

    async def disconnect_provider(self, provider_id: str) -> None:
        self._assert_running()
        await self._manager.disconnect_provider(provider_id)

    # ── Data access ───────────────────────────────────────────────────────────

    async def fetch_snapshot(
        self,
        symbols:     list[str],
        provider_id: str | None = None,
        use_cache:   bool = True,
    ) -> list[MarketSnapshot]:
        self._assert_running()
        return await self._manager.fetch_snapshot(symbols, provider_id, use_cache)

    async def fetch_historical(
        self,
        symbol:      str,
        start:       float,
        end:         float,
        interval:    CandleInterval = CandleInterval.D1,
        provider_id: str | None = None,
        use_cache:   bool = True,
    ) -> list[MarketCandle]:
        self._assert_running()
        return await self._manager.fetch_historical(symbol, start, end, interval, provider_id, use_cache)

    async def subscribe(
        self,
        symbols:     list[str],
        data_types:  list[MarketDataType],
        provider_id: str | None = None,
    ) -> SubscriptionHandle:
        self._assert_running()
        return await self._manager.subscribe(symbols, data_types, provider_id)

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        self._assert_running()
        await self._manager.unsubscribe(handle)

    # ── Accessors ─────────────────────────────────────────────────────────────

    def manager(self) -> MarketDataManager:
        return self._manager

    def registry(self) -> MarketDataRegistry:
        return self._registry

    def stream_manager(self) -> StreamManager:
        return self._stream_mgr

    def publisher(self) -> MarketEventPublisher:
        return self._publisher

    def cache(self) -> MarketDataCache[Any]:
        return self._cache

    def monitor(self) -> MarketDataMonitor:
        return self._monitor

    # ── Status ────────────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self._status in (MarketDataEngineStatus.RUNNING, MarketDataEngineStatus.DEGRADED)

    def status(self) -> MarketDataEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.time() - self._started_at

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "status":     self._status.value,
            "uptime_sec": round(self.uptime_sec(), 1),
            "manager":    self._manager.stats(),
        }


# ── Module singleton ──────────────────────────────────────────────────────────

_instance:      MarketDataEngine | None = None
_instance_lock: threading.Lock          = threading.Lock()


def get_market_data_engine(auto_start: bool = False) -> MarketDataEngine:
    """Return the module-level singleton MarketDataEngine."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = MarketDataEngine()
    if auto_start and not _instance.is_running():
        asyncio.run(_instance.start())
    return _instance


def reset_market_data_engine() -> None:
    """Destroy the singleton — for testing only."""
    global _instance
    with _instance_lock:
        _instance = None
