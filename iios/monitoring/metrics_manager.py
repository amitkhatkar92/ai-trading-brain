"""
iios/monitoring/metrics_manager.py
=====================================
Time-series metrics collection for IIOS subsystems.

Supports:
  - Counter   — monotonically increasing (e.g. trade count)
  - Gauge     — current value (e.g. CPU %)
  - Histogram — distribution (e.g. latency buckets)
  - Timer     — duration (alias for histogram)
  - Rate      — events per second derived from a counter

Metrics are stored in-memory with configurable retention. Thread-safe.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import time
import threading
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .monitoring_constants import MetricType, DEFAULT_METRIC_RETENTION_SECONDS, MAX_METRIC_HISTORY
from .monitoring_models import MetricPoint, MetricSeries
from .monitoring_exceptions import MetricError

__all__ = [
    "MetricsManager",
    "get_metrics_manager",
]

_instance_lock = threading.Lock()
_instance: Optional["MetricsManager"] = None


class MetricsManager:
    """Central metrics store for all IIOS subsystems.

    Usage::

        m = get_metrics_manager()
        m.increment("trades.executed", labels={"symbol": "RELIANCE"})
        m.gauge("cpu.percent", 45.2)
        with m.timer("GlobalIntelligence.fetch"):
            ...

    Args:
        retention_seconds: How long to keep metric history.
        max_history:       Maximum data points per series.
    """

    def __init__(
        self,
        retention_seconds: int = DEFAULT_METRIC_RETENTION_SECONDS,
        max_history: int = MAX_METRIC_HISTORY,
    ) -> None:
        self._lock = threading.Lock()
        self._series: dict[str, MetricSeries] = {}
        self._retention = retention_seconds
        self._max_history = max_history
        self._start_time = time.monotonic()

    # ------------------------------------------------------------------
    # Counter
    # ------------------------------------------------------------------

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[dict[str, str]] = None,
        description: str = "",
    ) -> float:
        """Increment a counter by *value* (default 1)."""
        series = self._get_or_create(name, MetricType.COUNTER, description, labels)
        with self._lock:
            new_val = (series.last_value if series.count > 0 else 0.0) + value
        series.record(new_val, labels)
        return new_val

    def reset_counter(self, name: str) -> None:
        """Reset a counter to zero."""
        with self._lock:
            series = self._series.get(name)
            if series:
                series.record(0.0)

    # ------------------------------------------------------------------
    # Gauge
    # ------------------------------------------------------------------

    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
        description: str = "",
        unit: str = "",
    ) -> None:
        """Set a gauge to *value*."""
        series = self._get_or_create(name, MetricType.GAUGE, description, labels, unit=unit)
        series.record(value, labels)

    # ------------------------------------------------------------------
    # Histogram / Timer
    # ------------------------------------------------------------------

    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
        description: str = "",
        unit: str = "",
    ) -> None:
        """Record a histogram observation."""
        series = self._get_or_create(name, MetricType.HISTOGRAM, description, labels, unit=unit)
        series.record(value, labels)

    @contextmanager
    def timer(
        self,
        name: str,
        labels: Optional[dict[str, str]] = None,
        description: str = "",
    ) -> Generator[None, None, None]:
        """Context manager that measures and records execution time in ms."""
        t_start = time.monotonic()
        try:
            yield
        finally:
            duration_ms = (time.monotonic() - t_start) * 1000
            self.histogram(name, duration_ms, labels=labels, description=description, unit="ms")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[MetricSeries]:
        """Return the ``MetricSeries`` for *name*."""
        with self._lock:
            return self._series.get(name)

    def get_value(self, name: str, default: float = 0.0) -> float:
        """Return the last recorded value for *name*."""
        with self._lock:
            series = self._series.get(name)
        return series.last_value if series and series.count > 0 else default

    def get_counter(self, name: str) -> float:
        """Return current counter value."""
        return self.get_value(name)

    def summary(self, name: str) -> dict[str, Any]:
        """Return aggregated statistics for *name*."""
        with self._lock:
            series = self._series.get(name)
        if not series or series.count == 0:
            return {}
        return {
            "name": name,
            "type": series.metric_type,
            "count": series.count,
            "last": round(series.last_value, 4),
            "min": round(series.minimum, 4) if series.minimum != float("inf") else 0.0,
            "max": round(series.maximum, 4) if series.maximum != float("-inf") else 0.0,
            "avg": round(series.average, 4),
            "total": round(series.total, 4),
            "unit": series.unit,
        }

    def all_metrics(self) -> list[dict[str, Any]]:
        """Return summaries for all registered metrics."""
        with self._lock:
            names = list(self._series.keys())
        return [self.summary(n) for n in names if self.summary(n)]

    def names(self) -> list[str]:
        """Return all metric names."""
        with self._lock:
            return list(self._series.keys())

    def recent_points(self, name: str, n: int = 50) -> list[MetricPoint]:
        """Return recent data points for *name*."""
        with self._lock:
            series = self._series.get(name)
        if not series:
            return []
        return list(series.points)[-n:]

    # ------------------------------------------------------------------
    # Computed / derived metrics
    # ------------------------------------------------------------------

    def success_rate(self, success_name: str, failure_name: str) -> float:
        """Compute success rate from two counters."""
        successes = self.get_value(success_name)
        failures = self.get_value(failure_name)
        total = successes + failures
        return successes / total if total > 0 else 1.0

    def uptime_seconds(self) -> float:
        """Return seconds since the metrics manager was created."""
        return time.monotonic() - self._start_time

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def prune(self) -> int:
        """Remove old data points beyond retention window. Returns pruned count."""
        cutoff = time.monotonic() - self._retention
        pruned = 0
        with self._lock:
            for series in self._series.values():
                before = len(series.points)
                series.points = [p for p in series.points if p.timestamp >= cutoff]
                pruned += before - len(series.points)
        return pruned

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._series.clear()

    @property
    def series_count(self) -> int:
        with self._lock:
            return len(self._series)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_create(
        self,
        name: str,
        metric_type: MetricType,
        description: str = "",
        labels: Optional[dict[str, str]] = None,
        unit: str = "",
    ) -> MetricSeries:
        with self._lock:
            if name not in self._series:
                self._series[name] = MetricSeries(
                    name=name,
                    metric_type=metric_type.value,
                    description=description,
                    unit=unit,
                    labels=labels or {},
                )
            return self._series[name]


def get_metrics_manager() -> MetricsManager:
    """Return (or create) the global ``MetricsManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = MetricsManager()
        return _instance


def _reset_metrics_manager() -> None:
    global _instance
    with _instance_lock:
        _instance = None
