"""
iios/observation/quality/quality_metrics.py
============================================
QualityMetrics — rolling aggregate quality statistics.

Tracks OQI scores per (source, obs_type) combination and computes
running statistics: mean, std-dev, and percentiles.
"""
from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import ObservationQuality
from .quality_score          import QualityScore, quality_tier

__all__ = [
    "MetricWindow",
    "QualityMetrics",
    "get_quality_metrics",
    "reset_quality_metrics",
]

_lock:    threading.Lock                = threading.Lock()
_metrics: Optional["QualityMetrics"]   = None


@dataclass
class MetricWindow:
    """Rolling window of OQI scores for one (key) slice."""
    key:        str
    max_size:   int
    _scores:    deque = field(default_factory=deque)

    def add(self, oqi: float) -> None:
        if len(self._scores) >= self.max_size:
            self._scores.popleft()
        self._scores.append(oqi)

    @property
    def count(self) -> int:
        return len(self._scores)

    @property
    def mean(self) -> float:
        if not self._scores:
            return 0.0
        return statistics.mean(self._scores)

    @property
    def stdev(self) -> float:
        if len(self._scores) < 2:
            return 0.0
        return statistics.stdev(self._scores)

    def percentile(self, p: float) -> float:
        """Return the *p*-th percentile (0–100) of the window."""
        if not self._scores:
            return 0.0
        sorted_s = sorted(self._scores)
        idx = max(0, int(len(sorted_s) * p / 100) - 1)
        return sorted_s[idx]

    def tier_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {t.value: 0 for t in ObservationQuality}
        for s in self._scores:
            dist[quality_tier(s).value] += 1
        return dist

    def to_dict(self) -> dict[str, Any]:
        return {
            "key":   self.key,
            "count": self.count,
            "mean":  round(self.mean,  4),
            "stdev": round(self.stdev, 4),
            "p25":   round(self.percentile(25), 4),
            "p50":   round(self.percentile(50), 4),
            "p75":   round(self.percentile(75), 4),
            "p90":   round(self.percentile(90), 4),
            "tiers": self.tier_distribution(),
        }


class QualityMetrics:
    """Aggregate quality statistics across all observations.

    Keys
    ----
    ``_global``            — all observations
    ``source:<name>``      — per-source breakdown
    ``type:<name>``        — per obs_type breakdown
    ``src_type:<s>:<t>``   — combined source+type slice
    """

    def __init__(
        self,
        window_size:    int   = 500,
        max_dimensions: int   = 200,
    ) -> None:
        self._windows:   dict[str, MetricWindow] = {}
        self._lock       = threading.RLock()
        self._window_sz  = window_size
        self._max_dims   = max_dimensions
        self._total      = 0
        self._last_update: float = 0.0

    # ── Record ────────────────────────────────────────────────────────────────

    def record(self, score: QualityScore, source: str = "", obs_type: str = "") -> None:
        """Record *score* into all relevant windows."""
        oqi = score.oqi
        keys = ["_global"]
        if source:
            keys.append(f"source:{source}")
        if obs_type:
            keys.append(f"type:{obs_type}")
        if source and obs_type:
            keys.append(f"src_type:{source}:{obs_type}")

        with self._lock:
            for key in keys:
                if key not in self._windows:
                    if len(self._windows) >= self._max_dims:
                        # Evict least-used (lowest count) to stay within limit
                        evict = min(self._windows, key=lambda k: self._windows[k].count)
                        del self._windows[evict]
                    self._windows[key] = MetricWindow(key=key, max_size=self._window_sz)
                self._windows[key].add(oqi)
            self._total += 1
            self._last_update = time.time()

    # ── Query ─────────────────────────────────────────────────────────────────

    def window(self, key: str = "_global") -> Optional[MetricWindow]:
        with self._lock:
            return self._windows.get(key)

    def global_mean(self) -> float:
        w = self.window("_global")
        return w.mean if w else 0.0

    def source_stats(self, source: str) -> Optional[dict[str, Any]]:
        w = self.window(f"source:{source}")
        return w.to_dict() if w else None

    def type_stats(self, obs_type: str) -> Optional[dict[str, Any]]:
        w = self.window(f"type:{obs_type}")
        return w.to_dict() if w else None

    def all_windows(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {k: w.to_dict() for k, w in self._windows.items()}

    def summary(self) -> dict[str, Any]:
        global_w = self.window("_global")
        with self._lock:
            return {
                "total_recorded":  self._total,
                "window_size":     self._window_sz,
                "dimension_count": len(self._windows),
                "last_update":     self._last_update,
                "global":          global_w.to_dict() if global_w else {},
            }

    def clear(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                self._windows.pop(key, None)
            else:
                self._windows.clear()
                self._total = 0


# ── Singletons ────────────────────────────────────────────────────────────────

def get_quality_metrics() -> QualityMetrics:
    global _metrics
    if _metrics is None:
        with _lock:
            if _metrics is None:
                _metrics = QualityMetrics()
    return _metrics


def reset_quality_metrics() -> None:
    global _metrics
    with _lock:
        _metrics = None
