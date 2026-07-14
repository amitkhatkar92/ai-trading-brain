"""iios/investment/strategy/integration/aggregation_engine.py
Core aggregation logic: processes IntelligenceUpdates into StrategyAggregationState.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    STALENESS_WARNING_SECONDS,
    STALENESS_CRITICAL_SECONDS,
)
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
)


class AggregationEngine:
    """
    Manages StrategyAggregationState for all known strategies.
    Thread-safe: multiple writers can submit updates concurrently.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock = threading.RLock()
        self._states:   Dict[str, StrategyAggregationState] = {}
        self._total_updates:  int = 0
        self._total_strategies: int = 0

    def apply(self, update: IntelligenceUpdate) -> StrategyAggregationState:
        """Apply an IntelligenceUpdate; create state if strategy is new."""
        with self._lock:
            if update.strategy_id not in self._states:
                self._states[update.strategy_id] = StrategyAggregationState(update.strategy_id)
                self._total_strategies += 1
            state = self._states[update.strategy_id]
            self._total_updates += 1

        state.apply(update)
        return state

    def get_state(self, strategy_id: str) -> Optional[StrategyAggregationState]:
        with self._lock:
            return self._states.get(strategy_id)

    def all_states(self) -> Dict[str, StrategyAggregationState]:
        with self._lock:
            return dict(self._states)

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._states.keys())

    def stale_sources(
        self,
        strategy_id: str,
        warn_seconds: float = STALENESS_WARNING_SECONDS,
    ) -> List[IntelligenceSource]:
        """Return sources whose latest update is older than warn_seconds."""
        state = self.get_state(strategy_id)
        if not state:
            return []
        now    = datetime.now(timezone.utc)
        result = []
        for src, upd in state.all_latest().items():
            age = (now - upd.timestamp).total_seconds()
            if age > warn_seconds:
                result.append(src)
        return result

    def completeness(self, strategy_id: str) -> float:
        """
        Weighted completeness score (0–1).
        REQUIRED sources count more than OPTIONAL.
        """
        state = self.get_state(strategy_id)
        if not state:
            return 0.0
        present = set(state.present_sources())
        all_srcs = list(IntelligenceSource)
        total_weight = sum(s.importance_weight for s in all_srcs)
        have_weight  = sum(s.importance_weight for s in all_srcs if s in present)
        return round(have_weight / max(total_weight, 1e-9), 4)

    def average_confidence(self, strategy_id: str) -> float:
        """Average confidence of all latest updates for a strategy."""
        state = self.get_state(strategy_id)
        if not state:
            return 0.0
        updates = list(state.all_latest().values())
        if not updates:
            return 0.0
        return round(sum(u.confidence for u in updates) / len(updates), 2)

    def freshness_score(
        self,
        strategy_id:  str,
        warn_seconds: float = STALENESS_WARNING_SECONDS,
        crit_seconds: float = STALENESS_CRITICAL_SECONDS,
    ) -> float:
        """Freshness score 0–1. 1.0 = all data is very fresh."""
        state = self.get_state(strategy_id)
        if not state:
            return 0.0
        updates = list(state.all_latest().values())
        if not updates:
            return 0.0
        now    = datetime.now(timezone.utc)
        scores = []
        for u in updates:
            age = (now - u.timestamp).total_seconds()
            if age <= 3600:
                scores.append(1.0)
            elif age <= warn_seconds:
                scores.append(0.8)
            elif age <= crit_seconds:
                scores.append(0.5)
            else:
                scores.append(0.1)
        return round(sum(scores) / len(scores), 4)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_strategies":  self._total_strategies,
                "total_updates":     self._total_updates,
                "active_states":     len(self._states),
            }
