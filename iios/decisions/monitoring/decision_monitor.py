"""
iios/decisions/monitoring/decision_monitor.py
=============================================
DecisionMonitor — tracks per-source latency, throughput, error rates,
and produces health snapshots.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from ..models.decision_result import DecisionResult


@dataclass
class SourceMetrics:
    """Rolling metrics for one source."""
    source_id:       str
    total:           int   = 0
    succeeded:       int   = 0
    failed:          int   = 0
    latency_buf:     deque = field(default_factory=lambda: deque(maxlen=100))
    error_buf:       deque = field(default_factory=lambda: deque(maxlen=50))

    @property
    def success_rate(self) -> float:
        return self.succeeded / self.total if self.total else 0.0

    @property
    def avg_latency_ms(self) -> float:
        buf = list(self.latency_buf)
        return sum(buf) / len(buf) if buf else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":    self.source_id,
            "total":        self.total,
            "succeeded":    self.succeeded,
            "failed":       self.failed,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class DecisionMonitor:
    """
    Receives DecisionResult objects and maintains per-source rolling metrics.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, SourceMetrics] = {}
        self._global_latency: deque              = deque(maxlen=500)
        self._total:   int                       = 0
        self._lock:    threading.RLock           = threading.RLock()

    def record(self, result: DecisionResult, source_id: str = "") -> None:
        sid = source_id or result.decision.metadata.source_id or "unknown"
        with self._lock:
            if sid not in self._metrics:
                self._metrics[sid] = SourceMetrics(source_id=sid)
            m = self._metrics[sid]
            m.total     += 1
            self._total += 1
            if result.succeeded:
                m.succeeded += 1
            else:
                m.failed    += 1
                m.error_buf.append(result.errors[:1])
            m.latency_buf.append(result.total_elapsed_ms)
            self._global_latency.append(result.total_elapsed_ms)

    def source_metrics(self, source_id: str) -> SourceMetrics | None:
        with self._lock:
            return self._metrics.get(source_id)

    def all_source_metrics(self) -> list[SourceMetrics]:
        with self._lock:
            return list(self._metrics.values())

    def health(self) -> dict[str, Any]:
        with self._lock:
            buf        = list(self._global_latency)
            total      = self._total
            sources    = len(self._metrics)
            total_ok   = sum(m.succeeded for m in self._metrics.values())
            total_fail = sum(m.failed    for m in self._metrics.values())

        avg_lat    = sum(buf) / len(buf) if buf else 0.0
        error_rate = total_fail / total  if total else 0.0
        status     = "healthy" if error_rate < 0.1 else ("degraded" if error_rate < 0.5 else "unhealthy")

        return {
            "status":           status,
            "total_decisions":  total,
            "total_succeeded":  total_ok,
            "total_failed":     total_fail,
            "error_rate":       round(error_rate, 4),
            "avg_latency_ms":   round(avg_lat, 2),
            "monitored_sources": sources,
        }

    def stats(self) -> dict[str, Any]:
        return self.health()


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock           = threading.Lock()
_MONITOR: DecisionMonitor | None  = None


def get_decision_monitor() -> DecisionMonitor:
    global _MONITOR
    if _MONITOR is None:
        with _LOCK:
            if _MONITOR is None:
                _MONITOR = DecisionMonitor()
    return _MONITOR


def reset_decision_monitor() -> None:
    global _MONITOR
    with _LOCK:
        _MONITOR = None
