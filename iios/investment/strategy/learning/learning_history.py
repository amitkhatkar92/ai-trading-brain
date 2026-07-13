"""iios/investment/strategy/learning/learning_history.py
Thread-safe ring buffers for learning observations and snapshots.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_snapshot import LearningSnapshot


class ObservationStore:
    """Append-only ring buffer of LearningObservation per strategy."""

    def __init__(self, max_per_strategy: int = 2_000) -> None:
        self._max   = max_per_strategy
        self._store: Dict[str, Deque[LearningObservation]] = {}
        self._lock  = threading.RLock()

    def append(self, obs: LearningObservation) -> None:
        with self._lock:
            sid = obs.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(obs)

    def get_all(self, strategy_id: str) -> List[LearningObservation]:
        with self._lock:
            return list(self._store.get(strategy_id, []))

    def get_recent(self, strategy_id: str, n: int) -> List[LearningObservation]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[-n:]

    def get_baseline(self, strategy_id: str, n: int) -> List[LearningObservation]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[:n]

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)

    def evaluation_scores(self, strategy_id: str, n: Optional[int] = None) -> List[float]:
        obs = self.get_recent(strategy_id, n) if n else self.get_all(strategy_id)
        return [o.evaluation_score for o in obs]

    def risk_scores(self, strategy_id: str, n: Optional[int] = None) -> List[float]:
        obs = self.get_recent(strategy_id, n) if n else self.get_all(strategy_id)
        return [o.risk_score for o in obs]

    def regimes(self, strategy_id: str, n: Optional[int] = None) -> List[str]:
        obs = self.get_recent(strategy_id, n) if n else self.get_all(strategy_id)
        return [o.current_regime for o in obs]


class LearningSnapshotStore:
    """Append-only ring buffer of LearningSnapshot per strategy."""

    def __init__(self, max_per_strategy: int = 2_000) -> None:
        self._max   = max_per_strategy
        self._store: Dict[str, Deque[LearningSnapshot]] = {}
        self._lock  = threading.RLock()

    def append(self, snap: LearningSnapshot) -> None:
        with self._lock:
            sid = snap.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(snap)

    def latest(self, strategy_id: str) -> Optional[LearningSnapshot]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1] if buf else None

    def history(self, strategy_id: str, n: int = 20) -> List[LearningSnapshot]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[-n:]

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)

    def score_trend(self, strategy_id: str, n: int = 10) -> List[float]:
        return [s.learning_score for s in self.history(strategy_id, n)]
