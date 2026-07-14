"""iios/investment/portfolio/construction/construction_statistics.py

Aggregated run-level statistics for the construction engine.

ConstructionStatistics tracks cumulative and rolling metrics across all
construction runs for all portfolios.  It is a monitoring artefact —
it never participates in the construction pipeline itself.
"""
from __future__ import annotations

import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# RunMetric
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunMetric:
    """Single-run metric record stored in the statistics aggregator."""

    run_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str   = ""
    succeeded:    bool  = False
    slots_built:  int   = 0
    duration_ms:  float = 0.0
    quality_score:float = 0.0
    run_at:       float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":        self.run_id,
            "portfolio_id":  self.portfolio_id,
            "succeeded":     self.succeeded,
            "slots_built":   self.slots_built,
            "duration_ms":   round(self.duration_ms, 2),
            "quality_score": round(self.quality_score, 4),
            "run_at":        self.run_at,
        }


# ---------------------------------------------------------------------------
# ConstructionStatisticsSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstructionStatisticsSnapshot:
    """Point-in-time statistics snapshot."""

    snapshot_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    total_runs:         int   = 0
    success_runs:       int   = 0
    failed_runs:        int   = 0
    success_rate:       float = 0.0
    avg_duration_ms:    float = 0.0
    p50_duration_ms:    float = 0.0
    p95_duration_ms:    float = 0.0
    avg_slots_built:    float = 0.0
    avg_quality_score:  float = 0.0
    portfolios_served:  int   = 0
    snapshotted_at:     float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "total_runs":        self.total_runs,
            "success_runs":      self.success_runs,
            "failed_runs":       self.failed_runs,
            "success_rate":      round(self.success_rate, 4),
            "avg_duration_ms":   round(self.avg_duration_ms, 2),
            "p50_duration_ms":   round(self.p50_duration_ms, 2),
            "p95_duration_ms":   round(self.p95_duration_ms, 2),
            "avg_slots_built":   round(self.avg_slots_built, 2),
            "avg_quality_score": round(self.avg_quality_score, 4),
            "portfolios_served": self.portfolios_served,
            "snapshotted_at":    self.snapshotted_at,
        }


# ---------------------------------------------------------------------------
# ConstructionStatistics
# ---------------------------------------------------------------------------

class ConstructionStatistics:
    """
    Thread-safe, bounded accumulator of construction run metrics.

    Keeps at most max_runs individual RunMetric records; summaries are
    always computed over the full buffer.
    """

    __slots__ = ("_max_runs", "_runs", "_portfolios", "_lock")

    def __init__(self, max_runs: int = 1000) -> None:
        self._max_runs = max(1, max_runs)
        self._runs: List[RunMetric] = []
        self._portfolios: set = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record(self, metric: RunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max_runs:
                self._runs.pop(0)
            if metric.portfolio_id:
                self._portfolios.add(metric.portfolio_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def snapshot(self) -> ConstructionStatisticsSnapshot:
        with self._lock:
            runs       = list(self._runs)
            n_pf       = len(self._portfolios)

        total   = len(runs)
        if total == 0:
            return ConstructionStatisticsSnapshot(portfolios_served=n_pf)

        success_runs = sum(1 for r in runs if r.succeeded)
        failed_runs  = total - success_runs
        durations    = sorted(r.duration_ms for r in runs)
        slots        = [r.slots_built for r in runs if r.succeeded]
        qualities    = [r.quality_score for r in runs if r.succeeded and r.quality_score > 0]

        p50  = _percentile(durations, 50)
        p95  = _percentile(durations, 95)

        return ConstructionStatisticsSnapshot(
            total_runs        = total,
            success_runs      = success_runs,
            failed_runs       = failed_runs,
            success_rate      = success_runs / total,
            avg_duration_ms   = sum(durations) / len(durations),
            p50_duration_ms   = p50,
            p95_duration_ms   = p95,
            avg_slots_built   = sum(slots) / len(slots) if slots else 0.0,
            avg_quality_score = sum(qualities) / len(qualities) if qualities else 0.0,
            portfolios_served = n_pf,
        )

    def for_portfolio(self, portfolio_id: str) -> "ConstructionStatistics":
        """Return a new ConstructionStatistics containing only runs for portfolio_id."""
        subset = ConstructionStatistics(max_runs=self._max_runs)
        with self._lock:
            for r in self._runs:
                if r.portfolio_id == portfolio_id:
                    subset._runs.append(r)
                    subset._portfolios.add(portfolio_id)
        return subset

    def recent(self, n: int = 20) -> Tuple[RunMetric, ...]:
        with self._lock:
            return tuple(self._runs[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(sorted_values: List[float], pct: int) -> float:
    """Compute the p-th percentile of a pre-sorted list."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    idx = max(0, min(n - 1, int(pct / 100 * n)))
    return sorted_values[idx]
