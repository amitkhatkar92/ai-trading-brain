"""iios/investment/strategy/integration/strategy_intelligence_aggregator.py
Public facade combining AggregationEngine and AggregationHistory.
Provides clean interfaces consumed by the integration engine.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import IntelligenceSource
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
    make_update,
)
from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_history import AggregationHistory


class StrategyIntelligenceAggregator:
    """
    Single aggregation facade.

    Responsibilities:
    - Accept IntelligenceUpdates from any registered source
    - Maintain per-strategy StrategyAggregationState
    - Maintain a rolling history of all updates
    - Expose query interfaces for downstream consumers
    """

    def __init__(self, max_history: int = 50_000) -> None:
        self._engine  = AggregationEngine()
        self._history = AggregationHistory(max_history)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def submit(self, update: IntelligenceUpdate) -> StrategyAggregationState:
        """Submit one intelligence update and return the resulting state."""
        state = self._engine.apply(update)
        self._history.record(update)
        return state

    def submit_all(self, updates: List[IntelligenceUpdate]) -> None:
        for u in updates:
            self.submit(u)

    # ── State query ───────────────────────────────────────────────────────────

    def state(self, strategy_id: str) -> Optional[StrategyAggregationState]:
        return self._engine.get_state(strategy_id)

    def all_states(self) -> Dict[str, StrategyAggregationState]:
        return self._engine.all_states()

    def known_strategies(self) -> List[str]:
        return self._engine.known_strategies()

    def latest(
        self,
        strategy_id: str,
        source: IntelligenceSource,
    ) -> Optional[IntelligenceUpdate]:
        state = self._engine.get_state(strategy_id)
        if not state:
            return None
        return state.get_latest(source)

    def all_latest(self, strategy_id: str) -> Dict[IntelligenceSource, IntelligenceUpdate]:
        state = self._engine.get_state(strategy_id)
        if not state:
            return {}
        return state.all_latest()

    # ── Quality metrics ───────────────────────────────────────────────────────

    def completeness(self, strategy_id: str) -> float:
        return self._engine.completeness(strategy_id)

    def average_confidence(self, strategy_id: str) -> float:
        return self._engine.average_confidence(strategy_id)

    def freshness_score(self, strategy_id: str) -> float:
        return self._engine.freshness_score(strategy_id)

    def stale_sources(self, strategy_id: str) -> List[IntelligenceSource]:
        return self._engine.stale_sources(strategy_id)

    # ── History query ─────────────────────────────────────────────────────────

    def history_for(self, strategy_id: str) -> List[IntelligenceUpdate]:
        return self._history.for_strategy(strategy_id)

    def history_for_source(self, source: IntelligenceSource) -> List[IntelligenceUpdate]:
        return self._history.for_source(source)

    def recent_updates(self, n: int = 100) -> List[IntelligenceUpdate]:
        return self._history.recent(n)

    def updates_since(self, ts: datetime) -> List[IntelligenceUpdate]:
        return self._history.since(ts)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        eng = self._engine.stats()
        return {
            **eng,
            "history_size":     self._history.current_size(),
            "total_recorded":   self._history.total_recorded(),
        }
