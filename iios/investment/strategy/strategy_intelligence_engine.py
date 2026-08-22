"""iios/investment/strategy/strategy_intelligence_engine.py
Top-level facade for the Strategy Intelligence Engine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from iios.investment.strategy.strategy_constants import (
    STRATEGY_ENGINE_SYSTEM_ID,
    STRATEGY_ENGINE_VERSION,
    StrategyCategory,
    StrategyStatus,
)
from iios.investment.strategy.strategy_exceptions import (
    StrategyEngineAlreadyRunningError,
    StrategyEngineNotInitializedError,
)
from iios.investment.strategy.strategy_intelligence import StrategyIntelligence
from iios.investment.strategy.strategy_manager import (
    StrategyManager,
    StrategyManagerStatistics,
    get_strategy_manager,
    reset_strategy_manager,
)
from iios.investment.strategy.strategy_registry import (
    StrategyRegistry,
    get_strategy_registry,
    reset_strategy_registry,
)
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_record import PerformanceRecord
from iios.investment.strategy.performance.performance_tracker import StrategyStatistics


class StrategyIntelligenceEngine:
    """
    Public facade for the Strategy Intelligence Engine.

    All external consumers of strategy intelligence MUST go through this
    facade.  It delegates to StrategyManager for heavy lifting and provides
    a stable API for the IIOS decision and portfolio layers.
    """

    VERSION   = STRATEGY_ENGINE_VERSION
    SYSTEM_ID = STRATEGY_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.RLock           = threading.RLock()
        self._running:  bool                      = False
        self._manager:  StrategyManager | None    = None
        self._registry: StrategyRegistry | None   = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  StrategyManager  | None = None,
        registry: StrategyRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise StrategyEngineAlreadyRunningError()
            self._registry = registry or get_strategy_registry()
            self._manager  = manager  or get_strategy_manager()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running  = False
            self._manager  = None
            self._registry = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── strategy management ───────────────────────────────────────────────────

    def register_strategy(
        self,
        definition: StrategyDefinition,
        metadata:   dict[str, Any] | None = None,
    ) -> StrategyProfile:
        self._require_running()
        return self._manager.register_strategy(definition, metadata)

    def get_profile(self, strategy_id: str) -> StrategyProfile:
        self._require_running()
        return self._manager.get_profile(strategy_id)

    # ── analysis ─────────────────────────────────────────────────────────────

    def analyze(
        self,
        strategy_id:    str,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]          | None = None,
        request_id:     str                     = "",
        **metadata: Any,
    ) -> StrategyIntelligence:
        self._require_running()
        return self._manager.analyze(
            strategy_id    = strategy_id,
            records        = records,
            market_context = market_context,
            request_id     = request_id,
            **metadata,
        )

    async def analyze_async(
        self,
        strategy_id:    str,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]          | None = None,
        request_id:     str                     = "",
        **metadata: Any,
    ) -> StrategyIntelligence:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.analyze(
                strategy_id, records, market_context, request_id, **metadata
            ),
        )

    # ── evaluation & selection ────────────────────────────────────────────────

    def evaluate(
        self,
        strategy_id:    str,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]          | None = None,
    ) -> StrategyScore:
        self._require_running()
        return self._manager.evaluate(strategy_id, records, market_context)

    def select(
        self,
        market_context: dict[str, Any] | None = None,
        n:              int             = 5,
        min_score:      float           = 40.0,
    ) -> list[StrategyScore]:
        self._require_running()
        return self._manager.select(market_context, n, min_score)

    # ── adaptation ────────────────────────────────────────────────────────────

    def adapt(
        self,
        strategy_id:    str,
        market_context: dict[str, Any] | None = None,
        apply:          bool            = False,
    ) -> AdaptationResult:
        self._require_running()
        return self._manager.adapt(strategy_id, market_context, apply)

    # ── lifecycle transitions ─────────────────────────────────────────────────

    def transition(
        self,
        strategy_id: str,
        to_status:   StrategyStatus,
        reason:      str = "",
    ) -> bool:
        self._require_running()
        return self._manager.transition(strategy_id, to_status, reason)

    # ── performance records ───────────────────────────────────────────────────

    def add_performance_record(
        self,
        strategy_id: str,
        record:      PerformanceRecord,
    ) -> None:
        self._require_running()
        self._manager.add_performance_record(strategy_id, record)

    def get_performance_stats(self, strategy_id: str) -> StrategyStatistics:
        self._require_running()
        return self._manager.get_performance_stats(strategy_id)

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest(self, strategy_id: str) -> StrategyIntelligence:
        self._require_running()
        return self._manager.get_latest_intelligence(strategy_id)

    def recent(self, n: int = 10) -> list[StrategyIntelligence]:
        self._require_running()
        return self._manager.recent(n)

    def all_strategy_ids(self) -> list[str]:
        self._require_running()
        return self._manager.all_strategy_ids()

    # ── meta ──────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        return {
            "status":    "running" if self._running else "stopped",
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
        }

    def stats(self) -> dict[str, Any]:
        self._require_running()
        return self._manager.statistics()

    def stats_object(self) -> StrategyManagerStatistics:
        self._require_running()
        return self._manager.stats_object()

    # ── internal ─────────────────────────────────────────────────────────────

    def _require_running(self) -> None:
        if not self._running or self._manager is None:
            raise StrategyEngineNotInitializedError(
                "StrategyIntelligenceEngine is not initialized. Call initialize() first."
            )


# ── module-level singleton ────────────────────────────────────────────────────

_engine_lock:     threading.Lock                       = threading.Lock()
_engine_instance: StrategyIntelligenceEngine | None    = None


def get_strategy_engine() -> StrategyIntelligenceEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = StrategyIntelligenceEngine()
        return _engine_instance


def reset_strategy_engine() -> None:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None:
            _engine_instance.shutdown()
        _engine_instance = None
