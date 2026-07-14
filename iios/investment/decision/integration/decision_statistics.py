"""iios/investment/decision/integration/decision_statistics.py
Integration-level statistics tracker.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.integration.integration_constants import SnapshotStatus


@dataclass(frozen=True)
class IntegrationStatistics:
    total_integrations: int
    successful:         int
    failed:             int
    complete_snapshots: int
    partial_snapshots:  int
    conflict_triggered: int
    avg_quality_score:  float
    avg_confidence:     float

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_integrations)

    @property
    def completeness_rate(self) -> float:
        return self.complete_snapshots / max(1, self.successful)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_integrations": self.total_integrations,
            "successful":         self.successful,
            "failed":             self.failed,
            "complete_snapshots": self.complete_snapshots,
            "partial_snapshots":  self.partial_snapshots,
            "conflict_triggered": self.conflict_triggered,
            "avg_quality_score":  round(self.avg_quality_score, 2),
            "avg_confidence":     round(self.avg_confidence, 2),
            "success_rate":       round(self.success_rate, 3),
            "completeness_rate":  round(self.completeness_rate, 3),
        }


class IntegrationStatisticsTracker:
    """Thread-safe accumulator for integration-level metrics."""

    def __init__(self) -> None:
        self._lock              = threading.RLock()
        self._total             = 0
        self._successful        = 0
        self._failed            = 0
        self._complete          = 0
        self._partial           = 0
        self._conflict          = 0
        self._quality_sum       = 0.0
        self._confidence_sum    = 0.0

    def record_success(
        self,
        status:        SnapshotStatus,
        quality_score: float,
        confidence:    float,
        had_conflicts: bool,
    ) -> None:
        with self._lock:
            self._total      += 1
            self._successful += 1
            if status == SnapshotStatus.COMPLETE:
                self._complete += 1
            else:
                self._partial  += 1
            if had_conflicts:
                self._conflict += 1
            self._quality_sum    += quality_score
            self._confidence_sum += confidence

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def summary(self) -> IntegrationStatistics:
        with self._lock:
            n_ok = max(1, self._successful)
            return IntegrationStatistics(
                total_integrations = self._total,
                successful         = self._successful,
                failed             = self._failed,
                complete_snapshots = self._complete,
                partial_snapshots  = self._partial,
                conflict_triggered = self._conflict,
                avg_quality_score  = self._quality_sum  / n_ok,
                avg_confidence     = self._confidence_sum / n_ok,
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._complete = self._partial = self._conflict = 0
            self._quality_sum = self._confidence_sum = 0.0
