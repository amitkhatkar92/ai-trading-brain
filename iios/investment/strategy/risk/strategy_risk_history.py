"""iios/investment/strategy/risk/strategy_risk_history.py
StrategyRiskHistory — thread-safe ring buffer of risk snapshots per strategy.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.risk.strategy_risk_profile import StrategyRiskProfile
from iios.investment.strategy.risk.strategy_risk_snapshot import StrategyRiskSnapshot


class StrategyRiskHistory:
    """Append-only ring buffer of StrategyRiskSnapshot objects."""

    def __init__(self, max_per_strategy: int = 1_000) -> None:
        self._max   = max_per_strategy
        self._store: Dict[str, Deque[StrategyRiskSnapshot]] = {}
        self._lock  = threading.RLock()

    def capture(self, profile: StrategyRiskProfile) -> StrategyRiskSnapshot:
        snap = StrategyRiskSnapshot.from_profile(profile)
        with self._lock:
            sid = profile.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(snap)
        return snap

    def latest(self, strategy_id: str) -> Optional[StrategyRiskSnapshot]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1] if buf else None

    def history(self, strategy_id: str, n: int = 20) -> List[StrategyRiskSnapshot]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[-n:]

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)

    def risk_score_trend(self, strategy_id: str, n: int = 10) -> List[float]:
        """Last N overall risk scores in chronological order."""
        return [s.overall_risk_score for s in self.history(strategy_id, n)]
