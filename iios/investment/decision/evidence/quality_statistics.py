"""iios/investment/decision/evidence/quality_statistics.py
QualityStatistics — rolling aggregate quality metrics.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.evidence.quality_score import QualityScore


@dataclass(frozen=True)
class QualityStatistics:
    total_computed:   int
    avg_overall:      float
    min_overall:      float
    max_overall:      float
    grade_dist:       Dict[str, int]   # {"A": n, "B": n, ...}
    computed_at:      datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_computed": self.total_computed,
            "avg_overall":    round(self.avg_overall, 2),
            "min_overall":    round(self.min_overall, 2),
            "max_overall":    round(self.max_overall, 2),
            "grade_dist":     self.grade_dist,
            "computed_at":    self.computed_at.isoformat(),
        }


class QualityStatisticsTracker:
    """Thread-safe tracker for QualityScore history."""

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._total       = 0
        self._overall_sum = 0.0
        self._min         = float("inf")
        self._max         = float("-inf")
        self._grades:     Dict[str, int] = {}

    def record(self, score: QualityScore) -> None:
        with self._lock:
            self._total       += 1
            self._overall_sum += score.overall
            self._min          = min(self._min, score.overall)
            self._max          = max(self._max, score.overall)
            self._grades[score.grade] = self._grades.get(score.grade, 0) + 1

    def summary(self) -> QualityStatistics:
        with self._lock:
            n = self._total or 1
            return QualityStatistics(
                total_computed=self._total,
                avg_overall=round(self._overall_sum / n, 2),
                min_overall=round(self._min if self._total else 0.0, 2),
                max_overall=round(self._max if self._total else 0.0, 2),
                grade_dist=dict(self._grades),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = 0
            self._overall_sum = 0.0
            self._min = float("inf")
            self._max = float("-inf")
            self._grades.clear()
