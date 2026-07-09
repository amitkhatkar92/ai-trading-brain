"""iios/investment/market/market_intelligence_engine.py
Top-level singleton authority for the Market Intelligence Layer.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from iios.investment.market.market_constants import (
    MARKET_ENGINE_SYSTEM_ID,
    MARKET_ENGINE_VERSION,
    MarketStatus,
)
from iios.investment.market.market_exceptions import (
    MarketEngineAlreadyRunningError,
    MarketEngineNotInitializedError,
)
from iios.investment.market.market_manager import MarketManager, get_market_manager
from iios.investment.market.market_registry import MarketRegistry, get_market_registry
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.market_state.market_state import MarketState
from iios.investment.market.models.market_intelligence import MarketIntelligence
from iios.investment.market.models.market_summary import MarketSummary
from iios.investment.market.regime.regime_classifier import RegimeClassifier


class MarketIntelligenceEngine:
    """
    Authoritative entry-point for all market intelligence operations.

    Lifecycle:
      initialize() → analyze() → shutdown()

    Downstream engines register this engine as a domain engine in
    InvestmentRegistry (IntelligenceType.MARKET) and call analyze()
    to retrieve structured MarketIntelligence objects.
    """

    VERSION   = MARKET_ENGINE_VERSION
    SYSTEM_ID = MARKET_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.Lock         = threading.Lock()
        self._running:  bool                   = False
        self._manager:  MarketManager  | None  = None
        self._registry: MarketRegistry | None  = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  MarketManager  | None = None,
        registry: MarketRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise MarketEngineAlreadyRunningError()
            self._manager  = manager  or get_market_manager()
            self._registry = registry or get_market_registry()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── registration ──────────────────────────────────────────────────────────

    def register_market(self, market_id: str, name: str = "") -> MarketState:
        self._assert_running()
        return self._manager.register_market(market_id, name)  # type: ignore[union-attr]

    def register_classifier(
        self,
        classifier: RegimeClassifier,
        *,
        overwrite: bool = False,
    ) -> None:
        self._assert_running()
        self._registry.register_classifier(classifier, overwrite=overwrite)  # type: ignore[union-attr]

    # ── analysis ──────────────────────────────────────────────────────────────

    def analyze(
        self,
        market_id:      str,
        prices:         dict[str, float] | None         = None,
        volumes:        dict[str, float] | None         = None,
        changes:        dict[str, float] | None         = None,
        spreads:        dict[str, float] | None         = None,
        advances:       int                             = 0,
        declines:       int                             = 0,
        unchanged:      int                             = 0,
        status:         MarketStatus                    = MarketStatus.UNKNOWN,
        price_history:  list[float]              | None = None,
        return_history: list[float]              | None = None,
        return_series:  dict[str, list[float]]  | None = None,
        request_id:     str                             = "",
        **kwargs: Any,
    ) -> MarketIntelligence:
        self._assert_running()
        return self._manager.analyze(  # type: ignore[union-attr]
            market_id      = market_id,
            prices         = prices,
            volumes        = volumes,
            changes        = changes,
            spreads        = spreads,
            advances       = advances,
            declines       = declines,
            unchanged      = unchanged,
            status         = status,
            price_history  = price_history,
            return_history = return_history,
            return_series  = return_series,
            request_id     = request_id,
            **kwargs,
        )

    async def analyze_async(
        self,
        market_id: str,
        **kwargs: Any,
    ) -> MarketIntelligence:
        self._assert_running()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._manager.analyze(market_id, **kwargs),  # type: ignore[union-attr]
        )

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest(self, market_id: str) -> MarketIntelligence:
        self._assert_running()
        return self._manager.get_latest(market_id)  # type: ignore[union-attr]

    def get_snapshot(self, market_id: str) -> MarketSnapshot:
        self._assert_running()
        return self._manager.get_snapshot(market_id)  # type: ignore[union-attr]

    def get_market_state(self, market_id: str) -> MarketState:
        self._assert_running()
        return self._manager.get_market_state(market_id)  # type: ignore[union-attr]

    def summary(self, market_id: str) -> MarketSummary:
        self._assert_running()
        return self._manager.summary(market_id)  # type: ignore[union-attr]

    def recent(self, n: int = 10) -> list[MarketIntelligence]:
        self._assert_running()
        return self._manager.recent(n)  # type: ignore[union-attr]

    # ── health / stats ────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        reg_stats = self._registry.statistics() if self._registry else {}
        return {
            "running":   self._running,
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
            "registry":  reg_stats,
        }

    def stats(self) -> dict[str, Any]:
        self._assert_running()
        s = self._manager.statistics()  # type: ignore[union-attr]
        s["version"]   = self.VERSION
        s["system_id"] = self.SYSTEM_ID
        return s

    # ── internals ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if not self._running:
            raise MarketEngineNotInitializedError()


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock               = threading.Lock()
_instance:       MarketIntelligenceEngine | None = None


def get_market_engine() -> MarketIntelligenceEngine:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = MarketIntelligenceEngine()
    return _instance


def reset_market_engine() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        if _instance is not None:
            try:
                _instance.shutdown()
            except Exception:  # noqa: BLE001
                pass
        _instance = None
