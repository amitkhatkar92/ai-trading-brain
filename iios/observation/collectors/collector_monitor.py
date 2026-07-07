"""
iios/observation/collectors/collector_monitor.py
================================================
CollectorMonitor — health monitoring for all registered collectors.

Runs a background thread that periodically checks every collector and
builds HealthReport objects for dashboard consumption.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .base_collector       import BaseCollector
from .collector_constants  import CollectorStatus
from .collector_metrics    import get_collector_metrics
from .collector_registry   import CollectorRegistry, get_collector_registry

__all__ = [
    "HealthReport",
    "CollectorMonitor",
    "get_collector_monitor",
    "reset_collector_monitor",
]

_LOG  = logging.getLogger("iios.collector.monitor")
_lock = threading.Lock()
_mon: Optional["CollectorMonitor"] = None


@dataclass
class HealthReport:
    """Health snapshot for one collector."""
    collector_name: str
    status:         CollectorStatus
    is_healthy:     bool
    last_run_at:    float
    total_errors:   int
    circuit_state:  str
    warnings:       list[str]     = field(default_factory=list)
    details:        dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector_name": self.collector_name,
            "status":         self.status.value,
            "is_healthy":     self.is_healthy,
            "last_run_at":    self.last_run_at,
            "total_errors":   self.total_errors,
            "circuit_state":  self.circuit_state,
            "warnings":       self.warnings,
        }


class CollectorMonitor:
    """Periodic health monitor for all collectors."""

    def __init__(
        self,
        stale_threshold_s: float = 300.0,
        error_rate_warn:   float = 0.20,
        check_interval_s:  float = 60.0,
    ) -> None:
        self._stale_threshold = stale_threshold_s
        self._error_rate_warn = error_rate_warn
        self._check_interval  = check_interval_s
        self._lock            = threading.RLock()
        self._last_reports:   dict[str, HealthReport] = {}
        self._running         = False
        self._thread:         Optional[threading.Thread] = None

    # ── Health checks ─────────────────────────────────────────────────────────

    def check_one(self, collector: BaseCollector) -> HealthReport:
        """Evaluate health for a single collector."""
        hc       = collector.health_check()
        stats    = hc.get("stats", {})
        circuit  = hc.get("circuit", {})
        warnings: list[str] = []
        is_healthy = True

        # Stale check
        last_run = stats.get("last_run_at", 0.0)
        if last_run > 0 and (time.time() - last_run) > self._stale_threshold:
            warnings.append(f"Stale: no run in >{self._stale_threshold:.0f}s")
            is_healthy = False

        # Error rate
        total  = (stats.get("total_collected", 0) + stats.get("total_errors", 0))
        errors = stats.get("total_errors", 0)
        if total > 0 and (errors / total) > self._error_rate_warn:
            warnings.append(f"High error rate: {100.0*errors/total:.1f}%")

        # Circuit breaker
        circ_state = circuit.get("state", "closed")
        if circ_state == "open":
            warnings.append("Circuit breaker OPEN")
            is_healthy = False

        # Stopped
        if collector.status == CollectorStatus.STOPPED:
            warnings.append("Collector STOPPED")
            is_healthy = False

        report = HealthReport(
            collector_name = collector.name,
            status         = collector.status,
            is_healthy     = is_healthy,
            last_run_at    = last_run,
            total_errors   = errors,
            circuit_state  = circ_state,
            warnings       = warnings,
            details        = hc,
        )
        with self._lock:
            self._last_reports[collector.name] = report
        return report

    def check_all(
        self, registry: Optional[CollectorRegistry] = None
    ) -> dict[str, HealthReport]:
        reg = registry or get_collector_registry()
        return {c.name: self.check_one(c) for c in reg.all()}

    def last_report(self, name: str) -> Optional[HealthReport]:
        with self._lock:
            return self._last_reports.get(name)

    def all_reports(self) -> dict[str, HealthReport]:
        with self._lock:
            return dict(self._last_reports)

    def system_health(self) -> dict[str, Any]:
        with self._lock:
            reports = list(self._last_reports.values())
        if not reports:
            return {"status": "unknown", "collectors": 0}
        healthy = sum(1 for r in reports if r.is_healthy)
        return {
            "status":       "healthy" if healthy == len(reports) else "degraded",
            "total":        len(reports),
            "healthy":      healthy,
            "unhealthy":    len(reports) - healthy,
            "circuit_open": sum(1 for r in reports if r.circuit_state == "open"),
        }

    # ── Background thread ─────────────────────────────────────────────────────

    def start(self, registry: Optional[CollectorRegistry] = None) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(registry,),
            daemon=True,
            name="CollectorMonitor",
        )
        self._thread.start()
        _LOG.info("CollectorMonitor started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        _LOG.info("CollectorMonitor stopped")

    def _monitor_loop(self, registry: Optional[CollectorRegistry]) -> None:
        while self._running:
            try:
                self.check_all(registry)
            except Exception as exc:
                _LOG.error("Monitor error: %s", exc)
            time.sleep(self._check_interval)


def get_collector_monitor() -> CollectorMonitor:
    global _mon
    if _mon is None:
        with _lock:
            if _mon is None:
                _mon = CollectorMonitor()
    return _mon


def reset_collector_monitor() -> None:
    global _mon
    with _lock:
        if _mon is not None:
            try:
                _mon.stop()
            except Exception:
                pass
        _mon = None
