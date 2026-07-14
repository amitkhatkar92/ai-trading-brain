"""iios/investment/decision/integration/conflict_history.py
Rolling history of conflicts detected across all decisions.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from iios.investment.decision.integration.conflict_detector import DetectedConflict
from iios.investment.decision.integration.integration_constants import (
    CONFLICT_HISTORY_WINDOW,
    ConflictSeverity,
    ConflictType,
)


class ConflictHistory:
    """
    Thread-safe rolling store of DetectedConflict entries.
    Indexed by decision_id, conflict_type, and severity.
    """

    def __init__(self, max_size: int = CONFLICT_HISTORY_WINDOW) -> None:
        self._lock     = threading.RLock()
        self._max      = max_size
        self._timeline: Deque[DetectedConflict] = deque(maxlen=max_size)
        self._by_decision: Dict[str, List[DetectedConflict]] = {}

    def record(self, decision_id: str, conflicts: List[DetectedConflict]) -> None:
        with self._lock:
            for c in conflicts:
                self._timeline.append(c)
                lst = self._by_decision.setdefault(decision_id, [])
                lst.append(c)
                if len(lst) > self._max:
                    lst.pop(0)

    def for_decision(self, decision_id: str) -> List[DetectedConflict]:
        with self._lock:
            return list(self._by_decision.get(decision_id, []))

    def by_severity(self, severity: ConflictSeverity) -> List[DetectedConflict]:
        with self._lock:
            return [c for c in self._timeline if c.severity == severity]

    def by_type(self, conflict_type: ConflictType) -> List[DetectedConflict]:
        with self._lock:
            return [c for c in self._timeline if c.conflict_type == conflict_type]

    def unresolved(self) -> List[DetectedConflict]:
        with self._lock:
            return [c for c in self._timeline if not c.is_resolved]

    def critical_unresolved(self) -> List[DetectedConflict]:
        with self._lock:
            return [
                c for c in self._timeline
                if not c.is_resolved and c.severity == ConflictSeverity.CRITICAL
            ]

    def recent(self, n: int = 20) -> List[DetectedConflict]:
        with self._lock:
            return list(self._timeline)[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._timeline)

    def reset(self) -> None:
        with self._lock:
            self._timeline.clear()
            self._by_decision.clear()
