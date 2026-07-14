"""iios/investment/decision/risk/risk_statistics.py
RiskStatisticsTracker — thread-safe accumulator for risk engine telemetry.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.risk.risk_constants import RiskQualityGrade


@dataclass(frozen=True)
class RiskStatistics:
    total_evaluations: int
    successful:        int
    failed:            int
    avg_overall_risk:  float
    avg_duration_ms:   float
    elevated_count:    int     # overall_risk >= 60
    critical_count:    int     # overall_risk >= 80
    computed_at:       datetime

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_evaluations)

    @property
    def elevated_rate(self) -> float:
        return self.elevated_count / max(1, self.successful)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "successful":        self.successful,
            "failed":            self.failed,
            "success_rate":      round(self.success_rate, 4),
            "avg_overall_risk":  round(self.avg_overall_risk, 2),
            "avg_duration_ms":   round(self.avg_duration_ms, 2),
            "elevated_count":    self.elevated_count,
            "critical_count":    self.critical_count,
            "elevated_rate":     round(self.elevated_rate, 4),
            "computed_at":       self.computed_at.isoformat(),
        }


class RiskStatisticsTracker:
    """Thread-safe accumulator."""

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total         = 0
        self._successful    = 0
        self._failed        = 0
        self._sum_risk      = 0.0
        self._sum_duration  = 0.0
        self._elevated      = 0
        self._critical      = 0

    def record_success(
        self,
        overall_risk: float,
        duration_ms:  float,
    ) -> None:
        with self._lock:
            self._total         += 1
            self._successful    += 1
            self._sum_risk      += overall_risk
            self._sum_duration  += duration_ms
            if overall_risk >= 60.0:
                self._elevated += 1
            if overall_risk >= 80.0:
                self._critical += 1

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def summary(self) -> RiskStatistics:
        with self._lock:
            s = max(1, self._successful)
            return RiskStatistics(
                total_evaluations=self._total,
                successful=self._successful,
                failed=self._failed,
                avg_overall_risk=round(self._sum_risk / s, 4),
                avg_duration_ms=round(self._sum_duration / s, 4),
                elevated_count=self._elevated,
                critical_count=self._critical,
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._sum_risk = self._sum_duration = 0.0
            self._elevated = self._critical = 0
