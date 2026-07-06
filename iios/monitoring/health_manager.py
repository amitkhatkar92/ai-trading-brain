"""
iios/monitoring/health_manager.py
===================================
Orchestrates all health checks and produces ``SystemHealthReport``.

``HealthManager`` maintains a registry of ``HealthCheck`` instances,
runs them on demand (or periodically in the background), and returns
an aggregated ``SystemHealthReport``.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from .monitoring_constants import HealthStatus
from .monitoring_exceptions import HealthCheckError
from .monitoring_models import HealthCheckResult, SystemHealthReport
from .health_checker import (
    HealthCheck,
    CPUHealthCheck,
    DiskHealthCheck,
    MemoryHealthCheck,
    ThreadPoolHealthCheck,
    LambdaHealthCheck,
)

__all__ = [
    "HealthManager",
    "get_health_manager",
]

_LOG = logging.getLogger("iios.monitoring.health")
_instance_lock = threading.Lock()
_instance: Optional["HealthManager"] = None


class HealthManager:
    """Manages and executes all registered health checks.

    Args:
        auto_register_system: If True, register CPU/memory/disk/threads checks.
        background_interval:  If >0, run all checks in a background thread
                              every N seconds.
    """

    def __init__(
        self,
        auto_register_system: bool = True,
        background_interval: float = 0.0,
    ) -> None:
        self._lock = threading.Lock()
        self._checks: dict[str, HealthCheck] = {}
        self._last_results: dict[str, HealthCheckResult] = {}
        self._start_time = time.monotonic()
        self._background_interval = background_interval
        self._bg_thread: Optional[threading.Thread] = None
        self._running = False
        self._change_callbacks: list[Callable[[SystemHealthReport], None]] = []

        if auto_register_system:
            self._register_system_checks()

        if background_interval > 0:
            self.start_background()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, check: HealthCheck) -> "HealthManager":
        """Register a health check. Replaces any existing check with same name."""
        with self._lock:
            self._checks[check.name] = check
        return self

    def register_lambda(
        self,
        name: str,
        fn: Callable[[], Any],
        category: str = "custom",
        healthy_message: str = "OK",
        unhealthy_message: str = "Check failed",
    ) -> "HealthManager":
        """Register a simple callable as a health check."""
        return self.register(LambdaHealthCheck(
            name=name,
            fn=fn,
            category=category,
            healthy_message=healthy_message,
            unhealthy_message=unhealthy_message,
        ))

    def unregister(self, name: str) -> bool:
        with self._lock:
            existed = name in self._checks
            self._checks.pop(name, None)
        return existed

    @property
    def check_names(self) -> list[str]:
        with self._lock:
            return list(self._checks.keys())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def check(self, name: str) -> HealthCheckResult:
        """Run a single named check and return its result."""
        with self._lock:
            check = self._checks.get(name)
        if check is None:
            raise HealthCheckError(f"Unknown health check: {name!r}", name)
        result = check.run()
        with self._lock:
            self._last_results[name] = result
        return result

    def check_all(self, parallel: bool = False) -> SystemHealthReport:
        """Run all registered checks and return a ``SystemHealthReport``.

        Args:
            parallel: If True, run checks concurrently using threads.
        """
        with self._lock:
            checks = dict(self._checks)

        if parallel:
            results = self._run_parallel(checks)
        else:
            results = {name: c.run() for name, c in checks.items()}

        with self._lock:
            self._last_results.update(results)

        report = self._build_report(results)
        self._notify(report)
        return report

    def get_last_report(self) -> SystemHealthReport:
        """Return a report from the last cached results (no re-check)."""
        with self._lock:
            results = dict(self._last_results)
        return self._build_report(results)

    def is_healthy(self) -> bool:
        """Quick overall health check using cached results."""
        report = self.get_last_report()
        return report.overall_status == HealthStatus.HEALTHY.value

    # ------------------------------------------------------------------
    # Background runner
    # ------------------------------------------------------------------

    def start_background(self) -> None:
        """Start a background thread that periodically runs all checks."""
        if self._running or self._background_interval <= 0:
            return
        self._running = True
        self._bg_thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="health-manager-bg",
        )
        self._bg_thread.start()
        _LOG.debug("Health manager background thread started (interval=%ss)", self._background_interval)

    def stop_background(self) -> None:
        """Stop the background thread."""
        self._running = False
        if self._bg_thread:
            self._bg_thread.join(timeout=self._background_interval + 1)
        _LOG.debug("Health manager background thread stopped")

    def on_change(self, callback: Callable[[SystemHealthReport], None]) -> None:
        """Register a callback invoked after every ``check_all()``."""
        with self._lock:
            self._change_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _register_system_checks(self) -> None:
        for check in [CPUHealthCheck(), MemoryHealthCheck(), DiskHealthCheck(), ThreadPoolHealthCheck()]:
            self.register(check)

    def _run_parallel(self, checks: dict[str, HealthCheck]) -> dict[str, HealthCheckResult]:
        results: dict[str, HealthCheckResult] = {}
        lock = threading.Lock()

        def _run(name: str, check: HealthCheck) -> None:
            result = check.run()
            with lock:
                results[name] = result

        threads = [
            threading.Thread(target=_run, args=(n, c), daemon=True)
            for n, c in checks.items()
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return results

    def _build_report(self, results: dict[str, HealthCheckResult]) -> SystemHealthReport:
        report = SystemHealthReport(
            checks=results,
            uptime_seconds=time.monotonic() - self._start_time,
        )
        report.compute_overall()
        report.summary = (
            f"{report.healthy_count} healthy, "
            f"{report.degraded_count} degraded, "
            f"{report.unhealthy_count} unhealthy "
            f"of {len(results)} checks"
        )
        return report

    def _notify(self, report: SystemHealthReport) -> None:
        with self._lock:
            cbs = list(self._change_callbacks)
        for cb in cbs:
            try:
                cb(report)
            except Exception as exc:
                _LOG.warning("Health change callback error: %s", exc)

    def _background_loop(self) -> None:
        while self._running:
            try:
                self.check_all()
            except Exception as exc:
                _LOG.error("Health background check failed: %s", exc)
            time.sleep(self._background_interval)


def get_health_manager() -> HealthManager:
    """Return (or create) the global ``HealthManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = HealthManager()
        return _instance


def _reset_health_manager() -> None:
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.stop_background()
        _instance = None
