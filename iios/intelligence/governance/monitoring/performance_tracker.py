"""
iios/intelligence/governance/monitoring/performance_tracker.py
==============================================================
PerformanceTracker — lightweight rolling-metric store per source.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

# We deliberately avoid importing PerformanceTracker from learning_system
# to prevent cross-layer circular imports.  This is a governance-local class.


@dataclass
class MetricSample:
    """A single time-stamped metric observation."""
    source_id:   str
    metric_name: str
    value:       float
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":   self.source_id,
            "metric_name": self.metric_name,
            "value":       round(self.value, 4),
            "recorded_at": self.recorded_at,
        }


class PerformanceTracker:
    """
    Records named metric samples per source and provides rolling statistics.
    """

    _WINDOW = 200   # max samples kept per (source, metric) pair

    def __init__(self) -> None:
        # (source_id, metric_name) → deque[MetricSample]
        self._buffers: dict[tuple[str, str], deque[MetricSample]] = {}
        self._lock: threading.RLock = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def record(self, source_id: str, metric_name: str, value: float) -> None:
        key = (source_id, metric_name)
        sample = MetricSample(source_id=source_id, metric_name=metric_name, value=value)
        with self._lock:
            if key not in self._buffers:
                self._buffers[key] = deque(maxlen=self._WINDOW)
            self._buffers[key].append(sample)

    # -- Read ──────────────────────────────────────────────────────────────────

    def rolling_avg(self, source_id: str, metric_name: str, n: int = 20) -> float:
        key = (source_id, metric_name)
        with self._lock:
            buf = self._buffers.get(key)
            if not buf:
                return 0.0
            samples = list(buf)[-n:]
        return sum(s.value for s in samples) / len(samples)

    def rolling_trend(self, source_id: str, metric_name: str, n: int = 20) -> str:
        """Returns 'improving', 'degrading', or 'stable'."""
        key = (source_id, metric_name)
        with self._lock:
            buf = self._buffers.get(key)
            if not buf or len(buf) < 4:
                return "stable"
            samples = list(buf)[-n:]
        half = len(samples) // 2
        first_avg  = sum(s.value for s in samples[:half]) / half
        second_avg = sum(s.value for s in samples[half:]) / (len(samples) - half)
        delta = second_avg - first_avg
        if delta > 0.02:
            return "improving"
        if delta < -0.02:
            return "degrading"
        return "stable"

    def recent_samples(self, source_id: str, metric_name: str, n: int = 20) -> list[MetricSample]:
        key = (source_id, metric_name)
        with self._lock:
            buf = self._buffers.get(key, deque())
            return list(buf)[-n:]

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            sources  = {k[0] for k in self._buffers}
            metrics  = {k[1] for k in self._buffers}
            total    = sum(len(v) for v in self._buffers.values())
        return {
            "monitored_sources": len(sources),
            "tracked_metrics":   len(metrics),
            "total_samples":     total,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock             = threading.Lock()
_TRACKER: PerformanceTracker | None = None


def get_governance_performance_tracker() -> PerformanceTracker:
    global _TRACKER
    if _TRACKER is None:
        with _LOCK:
            if _TRACKER is None:
                _TRACKER = PerformanceTracker()
    return _TRACKER


def reset_governance_performance_tracker() -> None:
    global _TRACKER
    with _LOCK:
        _TRACKER = None
