"""iios/investment/decision/risk/scenario_statistics.py
Tracks aggregate statistics about scenario risk analysis runs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ScenarioStatistics:
    total_runs:         int
    successful:         int
    failed:             int
    avg_blended_risk:   float
    avg_worst_risk:     float
    avg_scenario_count: float

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_runs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":         self.total_runs,
            "successful":         self.successful,
            "failed":             self.failed,
            "success_rate":       round(self.success_rate, 4),
            "avg_blended_risk":   round(self.avg_blended_risk, 2),
            "avg_worst_risk":     round(self.avg_worst_risk, 2),
            "avg_scenario_count": round(self.avg_scenario_count, 1),
        }


class ScenarioStatisticsTracker:
    """Thread-safe accumulator for scenario risk statistics."""

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total         = 0
        self._successful    = 0
        self._failed        = 0
        self._blended_sum   = 0.0
        self._worst_sum     = 0.0
        self._count_sum     = 0

    def record_success(
        self,
        blended_risk:   float,
        worst_risk:     float,
        scenario_count: int,
    ) -> None:
        with self._lock:
            self._total       += 1
            self._successful  += 1
            self._blended_sum += blended_risk
            self._worst_sum   += worst_risk
            self._count_sum   += scenario_count

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def summary(self) -> ScenarioStatistics:
        with self._lock:
            s = self._successful or 1
            return ScenarioStatistics(
                total_runs=self._total,
                successful=self._successful,
                failed=self._failed,
                avg_blended_risk=round(self._blended_sum / s, 4),
                avg_worst_risk=round(self._worst_sum / s, 4),
                avg_scenario_count=round(self._count_sum / s, 2),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._blended_sum = self._worst_sum = 0.0
            self._count_sum = 0
