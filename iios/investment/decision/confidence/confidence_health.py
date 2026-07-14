"""iios/investment/decision/confidence/confidence_health.py
ConfidenceHealthMonitor — tracks engine health metrics over time.
"""
from __future__ import annotations

import statistics
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.decision.confidence.confidence_constants import ConfidenceQualityGrade


@dataclass(frozen=True)
class ConfidenceHealthReport:
    total_runs:        int
    successful_runs:   int
    failed_runs:       int
    avg_confidence:    float
    min_confidence:    float
    max_confidence:    float
    avg_duration_ms:   float
    grade_distribution: Dict[str, int]
    computed_at:       datetime

    @property
    def success_rate(self) -> float:
        return self.successful_runs / max(1, self.total_runs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":          self.total_runs,
            "successful_runs":     self.successful_runs,
            "failed_runs":         self.failed_runs,
            "success_rate":        round(self.success_rate, 4),
            "avg_confidence":      round(self.avg_confidence, 2),
            "min_confidence":      round(self.min_confidence, 2),
            "max_confidence":      round(self.max_confidence, 2),
            "avg_duration_ms":     round(self.avg_duration_ms, 2),
            "grade_distribution":  self.grade_distribution,
            "computed_at":         self.computed_at.isoformat(),
        }


class ConfidenceHealthMonitor:
    """Thread-safe health monitor for the confidence engine."""

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._total       = 0
        self._successful  = 0
        self._failed      = 0
        self._confidences: List[float] = []
        self._durations:   List[float] = []
        self._grades:      Dict[str, int] = {g.value: 0 for g in ConfidenceQualityGrade}

    def record_success(self, confidence: float, duration_ms: float) -> None:
        with self._lock:
            self._total      += 1
            self._successful += 1
            self._confidences.append(confidence)
            self._durations.append(duration_ms)
            grade = ConfidenceQualityGrade.from_score(confidence).value
            self._grades[grade] = self._grades.get(grade, 0) + 1

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def report(self) -> ConfidenceHealthReport:
        with self._lock:
            confs = self._confidences or [0.0]
            durs  = self._durations   or [0.0]
            return ConfidenceHealthReport(
                total_runs=self._total,
                successful_runs=self._successful,
                failed_runs=self._failed,
                avg_confidence=round(statistics.mean(confs), 4),
                min_confidence=round(min(confs), 4),
                max_confidence=round(max(confs), 4),
                avg_duration_ms=round(statistics.mean(durs), 4),
                grade_distribution=dict(self._grades),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._confidences = []
            self._durations   = []
            self._grades      = {g.value: 0 for g in ConfidenceQualityGrade}
