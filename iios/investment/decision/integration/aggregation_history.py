"""iios/investment/decision/integration/aggregation_history.py
Rolling history of AggregationState snapshots, indexed by decision_id and subject_id.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.integration_constants import (
    INTEGRATION_HISTORY_WINDOW,
)


class AggregationHistory:
    """
    Thread-safe rolling store of aggregation state snapshots.
    Provides lookup by decision_id, subject_id, or recency.
    """

    def __init__(self, max_size: int = INTEGRATION_HISTORY_WINDOW) -> None:
        self._lock       = threading.RLock()
        self._max        = max_size
        self._timeline:  Deque[_AggregationStateSnapshot] = deque(maxlen=max_size)
        self._by_decision: Dict[str, _AggregationStateSnapshot] = {}
        self._by_subject:  Dict[str, List[_AggregationStateSnapshot]] = {}

    def record(self, snap: _AggregationStateSnapshot) -> None:
        with self._lock:
            self._timeline.append(snap)
            self._by_decision[snap.decision_id] = snap
            lst = self._by_subject.setdefault(snap.subject_id, [])
            lst.append(snap)
            if len(lst) > self._max:
                lst.pop(0)

    def get_by_decision(self, decision_id: str) -> Optional[_AggregationStateSnapshot]:
        with self._lock:
            return self._by_decision.get(decision_id)

    def get_by_subject(self, subject_id: str) -> List[_AggregationStateSnapshot]:
        with self._lock:
            return list(self._by_subject.get(subject_id, []))

    def latest_for_subject(self, subject_id: str) -> Optional[_AggregationStateSnapshot]:
        with self._lock:
            lst = self._by_subject.get(subject_id, [])
            return lst[-1] if lst else None

    def recent(self, n: int = 20) -> List[_AggregationStateSnapshot]:
        with self._lock:
            items = list(self._timeline)
            return items[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._timeline)

    def known_decisions(self) -> List[str]:
        with self._lock:
            return list(self._by_decision.keys())

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._by_subject.keys())

    def completeness_series(self, subject_id: str) -> List[float]:
        with self._lock:
            return [s.completeness for s in self._by_subject.get(subject_id, [])]

    def reset(self) -> None:
        with self._lock:
            self._timeline.clear()
            self._by_decision.clear()
            self._by_subject.clear()
