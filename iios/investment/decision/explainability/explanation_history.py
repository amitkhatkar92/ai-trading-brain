"""iios/investment/decision/explainability/explanation_history.py
Thread-safe rolling store for ExplanationSnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.explainability_constants import (
    EXPLANATION_HISTORY_WINDOW,
)


class ExplanationHistory:
    """
    Thread-safe per-subject rolling history of ExplanationSnapshots.
    Max EXPLANATION_HISTORY_WINDOW entries per subject.
    """

    def __init__(self, window: int = EXPLANATION_HISTORY_WINDOW) -> None:
        self._lock    = threading.RLock()
        self._window  = window
        self._by_id:  Dict[str, ExplanationSnapshot]          = {}
        self._by_subject: Dict[str, deque]                    = {}
        self._by_decision: Dict[str, ExplanationSnapshot]     = {}

    def record(self, snapshot: ExplanationSnapshot) -> None:
        with self._lock:
            self._by_id[snapshot.snapshot_id] = snapshot
            self._by_decision[snapshot.decision_id] = snapshot
            if snapshot.subject_id not in self._by_subject:
                self._by_subject[snapshot.subject_id] = deque(maxlen=self._window)
            self._by_subject[snapshot.subject_id].append(snapshot)

    def get(self, snapshot_id: str) -> Optional[ExplanationSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def for_subject(self, subject_id: str) -> List[ExplanationSnapshot]:
        with self._lock:
            return list(self._by_subject.get(subject_id, []))

    def for_decision(self, decision_id: str) -> Optional[ExplanationSnapshot]:
        with self._lock:
            return self._by_decision.get(decision_id)

    def latest_for_subject(self, subject_id: str) -> Optional[ExplanationSnapshot]:
        with self._lock:
            dq = self._by_subject.get(subject_id)
            return dq[-1] if dq else None

    def recent(self, n: int = 10) -> List[ExplanationSnapshot]:
        with self._lock:
            all_snaps = list(self._by_id.values())
            return sorted(all_snaps, key=lambda s: s.created_at, reverse=True)[:n]

    def outcome_series(self, subject_id: str) -> List[str]:
        """Return outcome values over time for a subject."""
        with self._lock:
            return [s.outcome.value for s in self._by_subject.get(subject_id, [])]

    def score_series(self, subject_id: str) -> List[float]:
        """Return explainability scores over time."""
        with self._lock:
            return [s.explainability_score for s in self._by_subject.get(subject_id, [])]

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._by_subject.keys())
