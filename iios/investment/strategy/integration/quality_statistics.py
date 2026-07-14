"""iios/investment/strategy/integration/quality_statistics.py
Rolling statistics tracker for QualityReports.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.strategy.integration.integration_constants import QualityDimension
from iios.investment.strategy.integration.strategy_quality import QualityReport


@dataclass(frozen=True)
class QualityStatistics:
    total_reports:    int
    avg_overall_score: float
    avg_by_dimension: Dict[str, float]   # QualityDimension.value → avg
    computed_at:      datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reports":     self.total_reports,
            "avg_overall_score": round(self.avg_overall_score, 2),
            "avg_by_dimension":  {k: round(v, 2) for k, v in self.avg_by_dimension.items()},
            "computed_at":       self.computed_at.isoformat(),
        }


class QualityStatisticsTracker:
    """Thread-safe rolling accumulator for QualityReport statistics."""

    def __init__(self) -> None:
        self._lock:          threading.RLock = threading.RLock()
        self._total:         int             = 0
        self._overall_sum:   float           = 0.0
        self._dim_sums:      Dict[str, float] = {d.value: 0.0 for d in QualityDimension}

    def record(self, report: QualityReport) -> None:
        with self._lock:
            self._total       += 1
            self._overall_sum += report.overall_score
            for key, val in report.scores.items():
                self._dim_sums[key] = self._dim_sums.get(key, 0.0) + val

    def summary(self) -> QualityStatistics:
        with self._lock:
            n = self._total
            avg_overall = (self._overall_sum / n) if n else 0.0
            avg_by_dim  = {
                k: round(v / n, 2) if n else 0.0
                for k, v in self._dim_sums.items()
            }
            return QualityStatistics(
                total_reports=n,
                avg_overall_score=round(avg_overall, 2),
                avg_by_dimension=avg_by_dim,
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total       = 0
            self._overall_sum = 0.0
            self._dim_sums    = {d.value: 0.0 for d in QualityDimension}
