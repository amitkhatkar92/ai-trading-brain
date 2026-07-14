"""iios/investment/decision/integration/quality_history.py
Rolling history of quality scores.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.investment.decision.integration.integration_constants import (
    QUALITY_HISTORY_WINDOW,
    QualityGrade,
)


@dataclass(frozen=True)
class QualityRecord:
    decision_id:   str
    subject_id:    str
    quality_score: float
    quality_grade: QualityGrade
    intelligence_score: float
    confidence:    float
    completeness:  float
    recorded_at:   datetime

    def to_dict(self):
        return {
            "decision_id":       self.decision_id,
            "subject_id":        self.subject_id,
            "quality_score":     round(self.quality_score, 2),
            "quality_grade":     self.quality_grade.value,
            "intelligence_score":round(self.intelligence_score, 2),
            "confidence":        round(self.confidence, 2),
            "completeness":      round(self.completeness, 3),
            "recorded_at":       self.recorded_at.isoformat(),
        }


class QualityHistory:
    """Thread-safe rolling store of QualityRecord entries."""

    def __init__(self, max_size: int = QUALITY_HISTORY_WINDOW) -> None:
        self._lock      = threading.RLock()
        self._max       = max_size
        self._timeline: Deque[QualityRecord] = deque(maxlen=max_size)
        self._by_subject: Dict[str, List[QualityRecord]] = {}

    def record(
        self,
        decision_id:   str,
        subject_id:    str,
        quality_score: float,
        intelligence_score: float,
        confidence:    float,
        completeness:  float,
    ) -> None:
        rec = QualityRecord(
            decision_id        = decision_id,
            subject_id         = subject_id,
            quality_score      = quality_score,
            quality_grade      = QualityGrade.from_score(quality_score),
            intelligence_score = intelligence_score,
            confidence         = confidence,
            completeness       = completeness,
            recorded_at        = datetime.now(timezone.utc),
        )
        with self._lock:
            self._timeline.append(rec)
            lst = self._by_subject.setdefault(subject_id, [])
            lst.append(rec)
            if len(lst) > self._max:
                lst.pop(0)

    def for_subject(self, subject_id: str) -> List[QualityRecord]:
        with self._lock:
            return list(self._by_subject.get(subject_id, []))

    def quality_series(self, subject_id: str) -> List[float]:
        with self._lock:
            return [r.quality_score for r in self._by_subject.get(subject_id, [])]

    def recent(self, n: int = 20) -> List[QualityRecord]:
        with self._lock:
            return list(self._timeline)[-n:]

    def average_quality(self) -> float:
        with self._lock:
            if not self._timeline:
                return 0.0
            return sum(r.quality_score for r in self._timeline) / len(self._timeline)

    def reset(self) -> None:
        with self._lock:
            self._timeline.clear()
            self._by_subject.clear()
