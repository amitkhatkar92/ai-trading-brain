"""iios/investment/decision/risk/risk_history.py
RiskHistory — thread-safe, per-subject rolling store of RiskSnapshots.
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

from iios.investment.decision.risk.risk_constants import HISTORY_WINDOW_SIZE
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot


class RiskHistory:
    """Thread-safe rolling history of RiskSnapshots keyed by subject_id."""

    def __init__(self, window: int = HISTORY_WINDOW_SIZE) -> None:
        self._window = window
        self._lock   = threading.RLock()
        self._by_subject: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self._window))
        self._by_id: Dict[str, RiskSnapshot] = {}

    def record(self, snapshot: RiskSnapshot) -> None:
        with self._lock:
            self._by_subject[snapshot.subject_id].append(snapshot)
            self._by_id[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def for_subject(self, subject_id: str) -> List[RiskSnapshot]:
        with self._lock:
            return list(self._by_subject.get(subject_id, []))

    def for_decision(self, decision_id: str) -> List[RiskSnapshot]:
        with self._lock:
            return [
                s for dq in self._by_subject.values()
                for s in dq if s.decision_id == decision_id
            ]

    def latest_for_subject(self, subject_id: str) -> Optional[RiskSnapshot]:
        with self._lock:
            dq = self._by_subject.get(subject_id)
            return dq[-1] if dq else None

    def recent(self, n: int = 20) -> List[RiskSnapshot]:
        with self._lock:
            all_s: List[RiskSnapshot] = [
                s for dq in self._by_subject.values() for s in dq
            ]
            all_s.sort(key=lambda s: s.created_at, reverse=True)
            return all_s[:n]

    def risk_series(self, subject_id: str) -> List[float]:
        with self._lock:
            return [s.overall_risk for s in self._by_subject.get(subject_id, [])]

    def count(self) -> int:
        with self._lock:
            return sum(len(dq) for dq in self._by_subject.values())

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._by_subject.keys())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self.count()
            elevated = sum(
                1 for dq in self._by_subject.values()
                for s in dq if s.is_elevated
            )
            return {
                "total_snapshots":    total,
                "elevated_snapshots": elevated,
                "known_subjects":     len(self._by_subject),
                "window_size":        self._window,
            }
