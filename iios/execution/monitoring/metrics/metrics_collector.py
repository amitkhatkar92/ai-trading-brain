"""iios/execution/monitoring/metrics/metrics_collector.py
==================================================
MetricsCollector — thread-safe raw data collection per session and
metric type.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_MAX_POINTS,
    WINDOW_SECONDS,
    MetricType,
    WindowSize,
)


@dataclass
class MetricPoint:
    """A single recorded data point."""

    value:     float
    timestamp: float
    tags:      Dict[str, str] = field(default_factory=dict)


class _MetricBuffer:
    """Thread-safe bounded deque for a single metric stream."""

    def __init__(self, max_points: int = DEFAULT_MAX_POINTS) -> None:
        self._max_points = max(1, max_points)
        self._points: deque = deque(maxlen=self._max_points)
        self._lock = threading.Lock()

    def append(self, point: MetricPoint) -> None:
        with self._lock:
            self._points.append(point)

    def all_values(self) -> List[float]:
        with self._lock:
            return [p.value for p in self._points]

    def windowed_values(self, window_seconds: float) -> List[float]:
        if window_seconds <= 0:
            return self.all_values()
        cutoff = time.time() - window_seconds
        with self._lock:
            return [p.value for p in self._points if p.timestamp >= cutoff]

    def tail(self, n: int) -> List[float]:
        with self._lock:
            pts = list(self._points)
        return [p.value for p in pts[-n:]]

    def count(self) -> int:
        with self._lock:
            return len(self._points)

    def clear(self) -> None:
        with self._lock:
            self._points.clear()


class MetricsCollector:
    """
    Thread-safe raw data collection for all sessions and metric types.

    Each (session_id, metric_type) pair owns an independent _MetricBuffer.
    """

    def __init__(self, max_points_per_series: int = DEFAULT_MAX_POINTS) -> None:
        self._max_points = max(1, max_points_per_series)
        self._buffers: Dict[Tuple[str, str], _MetricBuffer] = {}
        self._lock = threading.RLock()

    # ── Record ────────────────────────────────────────────────────────────────

    def record(
        self,
        session_id:  str,
        metric_type: MetricType,
        value:       float,
        *,
        timestamp: Optional[float]         = None,
        tags:      Optional[Dict[str, str]] = None,
    ) -> MetricPoint:
        """
        Record a single data point.

        Thread-safe — may be called from multiple threads simultaneously.
        """
        point = MetricPoint(
            value=float(value),
            timestamp=timestamp if timestamp is not None else time.time(),
            tags=tags or {},
        )
        key = (session_id, metric_type.value)
        with self._lock:
            if key not in self._buffers:
                self._buffers[key] = _MetricBuffer(self._max_points)
        self._buffers[key].append(point)
        return point

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def collect(
        self,
        session_id:  str,
        metric_type: MetricType,
        *,
        limit: Optional[int] = None,
    ) -> List[float]:
        """Return all recorded values, optionally limited to last ``limit``."""
        key = (session_id, metric_type.value)
        buf = self._buffers.get(key)
        if buf is None:
            return []
        if limit is not None:
            return buf.tail(limit)
        return buf.all_values()

    def collect_windowed(
        self,
        session_id:  str,
        metric_type: MetricType,
        window_size: WindowSize,
    ) -> List[float]:
        """Return values within the given rolling time window."""
        key = (session_id, metric_type.value)
        buf = self._buffers.get(key)
        if buf is None:
            return []
        window_secs = WINDOW_SECONDS.get(window_size.value, 0)
        return buf.windowed_values(window_secs)

    def count(self, session_id: str, metric_type: MetricType) -> int:
        key = (session_id, metric_type.value)
        buf = self._buffers.get(key)
        return buf.count() if buf else 0

    # ── Management ────────────────────────────────────────────────────────────

    def clear(
        self,
        session_id:  str,
        metric_type: Optional[MetricType] = None,
    ) -> None:
        """Clear buffers for a session, or a specific metric within a session."""
        with self._lock:
            if metric_type is not None:
                key = (session_id, metric_type.value)
                if key in self._buffers:
                    self._buffers[key].clear()
            else:
                for key in list(self._buffers.keys()):
                    if key[0] == session_id:
                        self._buffers[key].clear()

    def remove_session(self, session_id: str) -> None:
        """Remove all buffers for a session."""
        with self._lock:
            for key in [k for k in self._buffers if k[0] == session_id]:
                del self._buffers[key]

    def sessions(self) -> List[str]:
        with self._lock:
            return list({k[0] for k in self._buffers})

    def series_count(self) -> int:
        with self._lock:
            return len(self._buffers)

    def total_points(self) -> int:
        with self._lock:
            return sum(b.count() for b in self._buffers.values())
