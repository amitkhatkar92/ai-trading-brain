"""iios/investment/decision/reasoning/reasoning_health.py
ReasoningHealth — monitors the health of the reasoning engine across runs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.reasoning.reasoning_score import ReasoningQualityScore


@dataclass(frozen=True)
class HealthReport:
    total_runs:          int
    successful_runs:     int
    failed_runs:         int
    avg_quality:         float
    min_quality:         float
    max_quality:         float
    avg_duration_ms:     float
    grade_distribution:  Dict[str, int]
    computed_at:         datetime

    @property
    def success_rate(self) -> float:
        return round(self.successful_runs / self.total_runs, 3) if self.total_runs else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":         self.total_runs,
            "successful_runs":    self.successful_runs,
            "failed_runs":        self.failed_runs,
            "success_rate":       self.success_rate,
            "avg_quality":        round(self.avg_quality, 2),
            "min_quality":        round(self.min_quality, 2),
            "max_quality":        round(self.max_quality, 2),
            "avg_duration_ms":    round(self.avg_duration_ms, 1),
            "grade_distribution": self.grade_distribution,
            "computed_at":        self.computed_at.isoformat(),
        }


class ReasoningHealth:
    """Thread-safe health monitor for the reasoning engine."""

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total         = 0
        self._success       = 0
        self._fail          = 0
        self._quality_sum   = 0.0
        self._quality_min   = float("inf")
        self._quality_max   = float("-inf")
        self._duration_sum  = 0.0
        self._grades:       Dict[str, int] = {}

    def record_success(self, quality: ReasoningQualityScore, duration_ms: float) -> None:
        with self._lock:
            self._total       += 1
            self._success     += 1
            self._quality_sum += quality.overall
            self._quality_min  = min(self._quality_min, quality.overall)
            self._quality_max  = max(self._quality_max, quality.overall)
            self._duration_sum += duration_ms
            self._grades[quality.grade] = self._grades.get(quality.grade, 0) + 1

    def record_failure(self) -> None:
        with self._lock:
            self._total += 1
            self._fail  += 1

    def report(self) -> HealthReport:
        with self._lock:
            n = self._success or 1
            return HealthReport(
                total_runs=self._total,
                successful_runs=self._success,
                failed_runs=self._fail,
                avg_quality=round(self._quality_sum / n, 2),
                min_quality=round(self._quality_min if self._success else 0.0, 2),
                max_quality=round(self._quality_max if self._success else 0.0, 2),
                avg_duration_ms=round(self._duration_sum / n, 1),
                grade_distribution=dict(self._grades),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._success = self._fail = 0
            self._quality_sum = self._duration_sum = 0.0
            self._quality_min = float("inf")
            self._quality_max = float("-inf")
            self._grades.clear()
