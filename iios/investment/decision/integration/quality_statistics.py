"""iios/investment/decision/integration/quality_statistics.py
Quality-specific statistics tracker.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.integration.integration_constants import QualityGrade


@dataclass(frozen=True)
class QualityStatistics:
    total_evaluations: int
    grade_a_count:     int
    grade_b_count:     int
    grade_c_count:     int
    grade_d_count:     int
    grade_f_count:     int
    avg_quality_score: float
    avg_completeness:  float

    @property
    def high_quality_rate(self) -> float:
        high = self.grade_a_count + self.grade_b_count
        return high / max(1, self.total_evaluations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "grade_a_count":     self.grade_a_count,
            "grade_b_count":     self.grade_b_count,
            "grade_c_count":     self.grade_c_count,
            "grade_d_count":     self.grade_d_count,
            "grade_f_count":     self.grade_f_count,
            "avg_quality_score": round(self.avg_quality_score, 2),
            "avg_completeness":  round(self.avg_completeness, 3),
            "high_quality_rate": round(self.high_quality_rate, 3),
        }


class QualityStatisticsTracker:
    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._total        = 0
        self._grade_counts = {g: 0 for g in QualityGrade}
        self._quality_sum  = 0.0
        self._complete_sum = 0.0

    def record(self, quality_score: float, completeness: float) -> None:
        grade = QualityGrade.from_score(quality_score)
        with self._lock:
            self._total += 1
            self._grade_counts[grade] += 1
            self._quality_sum  += quality_score
            self._complete_sum += completeness

    def summary(self) -> QualityStatistics:
        with self._lock:
            n = max(1, self._total)
            return QualityStatistics(
                total_evaluations = self._total,
                grade_a_count     = self._grade_counts[QualityGrade.A],
                grade_b_count     = self._grade_counts[QualityGrade.B],
                grade_c_count     = self._grade_counts[QualityGrade.C],
                grade_d_count     = self._grade_counts[QualityGrade.D],
                grade_f_count     = self._grade_counts[QualityGrade.F],
                avg_quality_score = self._quality_sum  / n,
                avg_completeness  = self._complete_sum / n,
            )

    def reset(self) -> None:
        with self._lock:
            self._total = 0
            self._grade_counts = {g: 0 for g in QualityGrade}
            self._quality_sum  = 0.0
            self._complete_sum = 0.0
