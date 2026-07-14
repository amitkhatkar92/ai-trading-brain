"""iios/investment/decision/evidence/quality_history.py
QualityHistory — per-decision rolling quality score history.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.quality_score import QualityScore


class QualityHistory:
    """Thread-safe per-subject rolling history of QualityScores."""

    def __init__(self, max_per_subject: int = 500) -> None:
        self._lock:   threading.RLock                  = threading.RLock()
        self._store:  Dict[str, List[QualityScore]]     = {}
        self._max     = max_per_subject

    def record(self, subject_id: str, score: QualityScore) -> None:
        with self._lock:
            bucket = self._store.setdefault(subject_id, [])
            if len(bucket) >= self._max:
                bucket.pop(0)
            bucket.append(score)

    def get(self, subject_id: str, last_n: int = 50) -> List[QualityScore]:
        with self._lock:
            return self._store.get(subject_id, [])[-last_n:]

    def latest(self, subject_id: str) -> Optional[QualityScore]:
        scores = self.get(subject_id, 1)
        return scores[-1] if scores else None

    def trend(self, subject_id: str, window: int = 10) -> Optional[float]:
        """Return the change in overall quality over the last `window` scores (latest - oldest)."""
        scores = self.get(subject_id, window)
        if len(scores) < 2:
            return None
        return round(scores[-1].overall - scores[0].overall, 2)

    def subjects(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "subjects":    len(self._store),
                "total_scores": sum(len(v) for v in self._store.values()),
            }
