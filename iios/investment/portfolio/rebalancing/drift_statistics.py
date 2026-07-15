"""iios/investment/portfolio/rebalancing/drift_statistics.py

Thread-safe accumulator for drift analysis history.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.rebalancing_types import DriftLevel


@dataclass(frozen=True)
class DriftStatisticsSnapshot:
    """Rolling statistics over multiple drift observations."""

    n_observations:         int   = 0
    avg_total_drift:        float = 0.0
    avg_max_drift:          float = 0.0
    max_observed_drift:     float = 0.0
    pct_critical:           float = 0.0   # % of observations with critical drift
    pct_recommended_rebalance: float = 0.0
    consecutive_drifting:   int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_observations":            self.n_observations,
            "avg_total_drift":           round(self.avg_total_drift, 4),
            "max_observed_drift":        round(self.max_observed_drift, 4),
            "pct_critical":              round(self.pct_critical, 4),
            "pct_recommended_rebalance": round(self.pct_recommended_rebalance, 4),
        }


class DriftStatistics:
    """Thread-safe rolling accumulator for drift observations."""

    def __init__(self, max_observations: int = 500) -> None:
        self._max  = max_observations
        self._lock = threading.RLock()
        self._data: List[AllocationDrift] = []

    def record(self, drift: AllocationDrift) -> None:
        with self._lock:
            self._data.append(drift)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def snapshot(self) -> DriftStatisticsSnapshot:
        with self._lock:
            if not self._data:
                return DriftStatisticsSnapshot()
            n    = len(self._data)
            tot  = [d.total_abs_drift for d in self._data]
            mx   = [d.max_abs_drift   for d in self._data]
            crits = sum(1 for d in self._data if d.drift_level == DriftLevel.CRITICAL)
            recs  = sum(1 for d in self._data if d.rebalance_recommended)

            # Count consecutive observations with drift > minor
            consec = 0
            for d in reversed(self._data):
                if d.drift_level != DriftLevel.NONE:
                    consec += 1
                else:
                    break

            return DriftStatisticsSnapshot(
                n_observations           = n,
                avg_total_drift          = round(sum(tot) / n, 4),
                avg_max_drift            = round(sum(mx) / n, 4),
                max_observed_drift       = round(max(mx), 4),
                pct_critical             = round(crits / n, 4),
                pct_recommended_rebalance= round(recs / n, 4),
                consecutive_drifting     = consec,
            )
