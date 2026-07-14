"""iios/investment/decision/explainability/explanation_statistics.py
Thread-safe statistics tracker for the Explainability Engine.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.explainability.explainability_constants import DecisionOutcome


@dataclass(frozen=True)
class ExplanationStatistics:
    total_explanations:   int
    successful:           int
    failed:               int
    avg_score:            float
    avg_duration_ms:      float
    proceed_count:        int
    caution_count:        int
    halt_count:           int
    insufficient_count:   int
    computed_at:          datetime

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_explanations)

    @property
    def halt_rate(self) -> float:
        return self.halt_count / max(1, self.successful)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_explanations": self.total_explanations,
            "successful":         self.successful,
            "failed":             self.failed,
            "success_rate":       round(self.success_rate, 4),
            "avg_score":          round(self.avg_score, 2),
            "avg_duration_ms":    round(self.avg_duration_ms, 2),
            "proceed_count":      self.proceed_count,
            "caution_count":      self.caution_count,
            "halt_count":         self.halt_count,
            "insufficient_count": self.insufficient_count,
            "halt_rate":          round(self.halt_rate, 4),
            "computed_at":        self.computed_at.isoformat(),
        }


class ExplanationStatisticsTracker:
    """Thread-safe accumulator for explainability statistics."""

    def __init__(self) -> None:
        self._lock       = threading.RLock()
        self._total      = 0
        self._successful = 0
        self._failed     = 0
        self._score_sum  = 0.0
        self._dur_sum    = 0.0
        self._outcome_counts: Dict[str, int] = {
            "proceed": 0, "caution": 0, "halt": 0, "insufficient_data": 0,
        }

    def record_success(
        self,
        outcome:     DecisionOutcome,
        score:       float,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self._total      += 1
            self._successful += 1
            self._score_sum  += score
            self._dur_sum    += duration_ms
            self._outcome_counts[outcome.value] = \
                self._outcome_counts.get(outcome.value, 0) + 1

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def summary(self) -> ExplanationStatistics:
        with self._lock:
            s = max(1, self._successful)
            return ExplanationStatistics(
                total_explanations=self._total,
                successful=self._successful,
                failed=self._failed,
                avg_score=round(self._score_sum / s, 4),
                avg_duration_ms=round(self._dur_sum / s, 4),
                proceed_count=self._outcome_counts.get("proceed", 0),
                caution_count=self._outcome_counts.get("caution", 0),
                halt_count=self._outcome_counts.get("halt", 0),
                insufficient_count=self._outcome_counts.get("insufficient_data", 0),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._score_sum = self._dur_sum = 0.0
            self._outcome_counts = {
                "proceed": 0, "caution": 0, "halt": 0, "insufficient_data": 0,
            }
