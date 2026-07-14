"""iios/investment/portfolio/diversification/diversification_statistics.py

Aggregated run-level statistics for the diversification engine.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DiversificationRunMetric:
    run_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str   = ""
    succeeded:         bool  = False
    n_positions:       int   = 0
    hhi:               float = 0.0
    effective_n:       float = 0.0
    entropy_ratio:     float = 0.0
    avg_correlation:   float = 0.0
    diversification_ratio: float = 0.0
    overall_score:     float = 0.0
    n_alerts:          int   = 0
    duration_ms:       float = 0.0
    run_at:            float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":               self.run_id,
            "portfolio_id":         self.portfolio_id,
            "succeeded":            self.succeeded,
            "n_positions":          self.n_positions,
            "hhi":                  round(self.hhi, 6),
            "effective_n":          round(self.effective_n, 2),
            "entropy_ratio":        round(self.entropy_ratio, 4),
            "avg_correlation":      round(self.avg_correlation, 4),
            "diversification_ratio":round(self.diversification_ratio, 4),
            "overall_score":        round(self.overall_score, 4),
            "n_alerts":             self.n_alerts,
            "duration_ms":          round(self.duration_ms, 2),
            "run_at":               self.run_at,
        }


def _pct(sorted_vals: List[float], pct: int) -> float:
    if not sorted_vals:
        return 0.0
    idx = max(0, min(len(sorted_vals) - 1, int(pct / 100 * len(sorted_vals))))
    return sorted_vals[idx]


@dataclass(frozen=True)
class DiversificationStatisticsSnapshot:
    snapshot_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    total_runs:         int   = 0
    success_runs:       int   = 0
    failed_runs:        int   = 0
    success_rate:       float = 0.0
    avg_duration_ms:    float = 0.0
    p50_duration_ms:    float = 0.0
    p95_duration_ms:    float = 0.0
    avg_overall_score:  float = 0.0
    avg_effective_n:    float = 0.0
    avg_hhi:            float = 0.0
    avg_correlation:    float = 0.0
    portfolios_served:  int   = 0
    snapshotted_at:     float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":      self.total_runs,
            "success_runs":    self.success_runs,
            "failed_runs":     self.failed_runs,
            "success_rate":    round(self.success_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "p50_duration_ms": round(self.p50_duration_ms, 2),
            "p95_duration_ms": round(self.p95_duration_ms, 2),
            "avg_overall_score":round(self.avg_overall_score, 4),
            "avg_effective_n": round(self.avg_effective_n, 2),
            "avg_hhi":         round(self.avg_hhi, 6),
            "avg_correlation": round(self.avg_correlation, 4),
            "portfolios_served":self.portfolios_served,
            "snapshotted_at":  self.snapshotted_at,
        }


class DiversificationStatistics:
    """Thread-safe, bounded accumulator of run metrics."""

    def __init__(self, max_runs: int = 1000) -> None:
        self._max  = max(1, max_runs)
        self._runs: List[DiversificationRunMetric] = []
        self._portfolios: set = set()
        self._lock = threading.Lock()

    def record(self, metric: DiversificationRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max:
                self._runs.pop(0)
            if metric.portfolio_id:
                self._portfolios.add(metric.portfolio_id)

    def snapshot(self) -> DiversificationStatisticsSnapshot:
        with self._lock:
            runs   = list(self._runs)
            n_pf   = len(self._portfolios)

        total   = len(runs)
        if total == 0:
            return DiversificationStatisticsSnapshot(portfolios_served=n_pf)

        success = sum(1 for r in runs if r.succeeded)
        durs    = sorted(r.duration_ms for r in runs)
        ok_runs = [r for r in runs if r.succeeded]
        scores  = [r.overall_score  for r in ok_runs]
        eff_ns  = [r.effective_n    for r in ok_runs]
        hhis    = [r.hhi            for r in ok_runs]
        corrs   = [r.avg_correlation for r in ok_runs]

        return DiversificationStatisticsSnapshot(
            total_runs       = total,
            success_runs     = success,
            failed_runs      = total - success,
            success_rate     = success / total,
            avg_duration_ms  = sum(durs) / len(durs),
            p50_duration_ms  = _pct(durs, 50),
            p95_duration_ms  = _pct(durs, 95),
            avg_overall_score= sum(scores) / len(scores) if scores else 0.0,
            avg_effective_n  = sum(eff_ns) / len(eff_ns) if eff_ns else 0.0,
            avg_hhi          = sum(hhis) / len(hhis) if hhis else 0.0,
            avg_correlation  = sum(corrs) / len(corrs) if corrs else 0.0,
            portfolios_served= n_pf,
        )

    def for_portfolio(self, pid: str) -> "DiversificationStatistics":
        subset = DiversificationStatistics(max_runs=self._max)
        with self._lock:
            for r in self._runs:
                if r.portfolio_id == pid:
                    subset._runs.append(r)
                    subset._portfolios.add(pid)
        return subset

    def recent(self, n: int = 20) -> Tuple[DiversificationRunMetric, ...]:
        with self._lock:
            return tuple(self._runs[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._portfolios)
