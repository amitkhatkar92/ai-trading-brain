"""iios/investment/strategy/learning/performance_monitor.py
PerformanceMonitor — rolling performance watcher per strategy.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    ewma, linear_trend, rolling_mean
)


class StrategyPerformanceMonitor:
    """
    Maintains rolling performance metrics per strategy.
    Thread-safe; append observations and query rolling stats.
    """

    def __init__(self, window: int = 20, max_history: int = 500) -> None:
        self._window = window
        self._max    = max_history
        self._store: Dict[str, deque] = {}
        self._lock   = threading.RLock()

    def observe(self, obs: LearningObservation) -> None:
        with self._lock:
            sid = obs.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(obs)

    def rolling_mean_score(self, strategy_id: str, n: Optional[int] = None) -> float:
        window = n or self._window
        scores = self._scores(strategy_id, window)
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def ewma_score(self, strategy_id: str, alpha: float = 0.20) -> float:
        scores = self._scores(strategy_id, self._window)
        return ewma(scores, alpha) if scores else 0.0

    def score_trend(self, strategy_id: str) -> float:
        scores = self._scores(strategy_id, self._window)
        return linear_trend(scores) if len(scores) >= 2 else 0.0

    def is_improving(self, strategy_id: str) -> bool:
        return self.score_trend(strategy_id) > 0

    def is_declining(self, strategy_id: str) -> bool:
        return self.score_trend(strategy_id) < 0

    def recent_min_score(self, strategy_id: str) -> float:
        scores = self._scores(strategy_id, self._window)
        return min(scores) if scores else 0.0

    def recent_max_score(self, strategy_id: str) -> float:
        scores = self._scores(strategy_id, self._window)
        return max(scores) if scores else 0.0

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def observation_count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def _scores(self, strategy_id: str, n: int) -> List[float]:
        with self._lock:
            buf = list(self._store.get(strategy_id, []))
            return [o.evaluation_score for o in buf[-n:]]
