"""iios/investment/decision/reasoning/hypothesis_history.py
HypothesisHistory — rolling per-subject hypothesis store.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.reasoning_constants import HypothesisType


class HypothesisHistory:
    """Thread-safe per-subject rolling history of hypotheses."""

    def __init__(self, max_per_subject: int = 1_000) -> None:
        self._lock:   threading.RLock                    = threading.RLock()
        self._store:  Dict[str, List[Hypothesis]]         = {}
        self._max     = max_per_subject

    def record(self, subject_id: str, hypothesis: Hypothesis) -> None:
        with self._lock:
            bucket = self._store.setdefault(subject_id, [])
            if len(bucket) >= self._max:
                bucket.pop(0)
            bucket.append(hypothesis)

    def record_all(self, subject_id: str, hypotheses: List[Hypothesis]) -> None:
        for h in hypotheses:
            self.record(subject_id, h)

    def get(self, subject_id: str, last_n: int = 50) -> List[Hypothesis]:
        with self._lock:
            return self._store.get(subject_id, [])[-last_n:]

    def by_type(
        self,
        subject_id:      str,
        hypothesis_type: HypothesisType,
    ) -> List[Hypothesis]:
        with self._lock:
            return [h for h in self._store.get(subject_id, [])
                    if h.hypothesis_type == hypothesis_type]

    def subjects(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "subjects":         len(self._store),
                "total_hypotheses": sum(len(v) for v in self._store.values()),
            }
