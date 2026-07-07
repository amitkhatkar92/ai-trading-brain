"""
iios/observation/collectors/collector_manager.py
================================================
CollectorManager — top-level orchestrator for the Collection Framework.

The single authoritative entry point for:
- Registering / unregistering collectors
- Running collectors (single, batch, parallel, by category)
- Scheduling (interval, market-hours, event-triggered)
- Health monitoring
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..models.observation  import Observation
from .base_collector       import BaseCollector, CollectorConfig
from .collector_constants  import CollectorCategory, CollectorStatus
from .collector_exceptions import CollectorNotFoundError
from .collector_executor   import CollectorExecutor, ExecutionResult, get_collector_executor
from .collector_factory    import CollectorFactory, get_collector_factory
from .collector_metrics    import CollectorMetrics, get_collector_metrics
from .collector_monitor    import CollectorMonitor, HealthReport, get_collector_monitor
from .collector_registry   import CollectorRegistry, get_collector_registry
from .collector_scheduler  import CollectorScheduler, get_collector_scheduler
from .scheduled_collector  import ScheduleConfig

__all__ = ["CollectorManager", "get_collector_manager", "reset_collector_manager"]

_LOG  = logging.getLogger("iios.collector.manager")
_lock = threading.Lock()
_mgr: Optional["CollectorManager"] = None


class CollectorManager:
    """
    Top-level orchestrator for the Observation Collection Framework.

    Usage::

        mgr = get_collector_manager()
        mgr.initialise()
        mgr.register(my_collector)
        results = mgr.run_all()
        mgr.shutdown()
    """

    def __init__(
        self,
        registry:  Optional[CollectorRegistry]  = None,
        executor:  Optional[CollectorExecutor]   = None,
        scheduler: Optional[CollectorScheduler]  = None,
        monitor:   Optional[CollectorMonitor]    = None,
        factory:   Optional[CollectorFactory]    = None,
        metrics:   Optional[CollectorMetrics]    = None,
    ) -> None:
        self._registry   = registry  or get_collector_registry()
        self._executor   = executor  or get_collector_executor()
        self._scheduler  = scheduler or get_collector_scheduler()
        self._monitor    = monitor   or get_collector_monitor()
        self._factory    = factory   or get_collector_factory()
        self._metrics    = metrics   or get_collector_metrics()
        self._lock       = threading.RLock()
        self._initialised = False
        self._startup_at  = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        with self._lock:
            if self._initialised:
                return
            self._startup_at  = time.time()
            self._initialised = True
            _LOG.info("CollectorManager initialised")

    def shutdown(self) -> None:
        with self._lock:
            if not self._initialised:
                return
            _LOG.info("CollectorManager shutting down …")
            for c in self._registry.all():
                if c.status not in (CollectorStatus.STOPPED, CollectorStatus.IDLE):
                    try:
                        c.shutdown()
                    except Exception as exc:
                        _LOG.warning("Shutdown error [%s]: %s", c.name, exc)
            try:
                self._scheduler.stop()
            except Exception:
                pass
            try:
                self._monitor.stop()
            except Exception:
                pass
            self._initialised = False
            _LOG.info("CollectorManager stopped")

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        collector:  BaseCollector,
        schedule:   Optional[ScheduleConfig] = None,
        auto_init:  bool = True,
        overwrite:  bool = False,
    ) -> str:
        """Register a collector. Returns its name."""
        self._registry.register(collector, overwrite=overwrite)
        if auto_init:
            try:
                collector.initialise()
            except Exception as exc:
                _LOG.warning("Init error [%s]: %s", collector.name, exc)
        if schedule:
            self._scheduler.add(collector, schedule=schedule)
        _LOG.info("Registered collector: %s", collector.name)
        return collector.name

    def register_from_dict(self, d: dict[str, Any], **kwargs: Any) -> str:
        """Build and register a collector from a config dict."""
        c = self._factory.from_dict(d)
        return self.register(c, **kwargs)

    def unregister(self, name: str) -> None:
        self._registry.unregister(name)

    def get(self, name: str) -> BaseCollector:
        return self._registry.get(name)

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(self, name: str) -> ExecutionResult:
        """Run a single named collector."""
        return self._executor.run_one(self._registry.get(name))

    def run_all(self, timeout_s: Optional[float] = None) -> list[ExecutionResult]:
        return self._executor.run_all(self._registry, timeout_s=timeout_s)

    def run_category(
        self,
        category:  CollectorCategory,
        timeout_s: Optional[float] = None,
    ) -> list[ExecutionResult]:
        return self._executor.run_by_category(self._registry, category, timeout_s=timeout_s)

    def run_enabled(self, timeout_s: Optional[float] = None) -> list[ExecutionResult]:
        return self._executor.run_enabled(self._registry, timeout_s=timeout_s)

    # ── Scheduling ────────────────────────────────────────────────────────────

    def start_scheduler(self) -> None:
        self._scheduler.start()

    def stop_scheduler(self) -> None:
        self._scheduler.stop()

    def schedule(self, name: str, schedule: ScheduleConfig) -> str:
        return self._scheduler.add(self._registry.get(name), schedule=schedule)

    def trigger_now(self, name: str) -> ExecutionResult:
        return self.run(name)

    def trigger_event(self, event_name: str) -> int:
        return self._scheduler.trigger_event(event_name)

    # ── Monitoring ────────────────────────────────────────────────────────────

    def start_monitor(self) -> None:
        self._monitor.start(self._registry)

    def stop_monitor(self) -> None:
        self._monitor.stop()

    def health(self, name: str) -> HealthReport:
        return self._monitor.check_one(self._registry.get(name))

    def all_health(self) -> dict[str, HealthReport]:
        return self._monitor.check_all(self._registry)

    def system_health(self) -> dict[str, Any]:
        return self._monitor.system_health()

    # ── Status / info ─────────────────────────────────────────────────────────

    def list_collectors(self) -> list[str]:
        return self._registry.names()

    def status(self) -> dict[str, Any]:
        return {
            "initialised":    self._initialised,
            "uptime_s":       round(time.time() - self._startup_at, 1) if self._startup_at else 0,
            "collector_count": self._registry.count(),
            "registry":       self._registry.status_summary(),
            "scheduler":      self._scheduler.status(),
            "system_health":  self._monitor.system_health(),
        }


def get_collector_manager() -> CollectorManager:
    global _mgr
    if _mgr is None:
        with _lock:
            if _mgr is None:
                _mgr = CollectorManager()
    return _mgr


def reset_collector_manager() -> None:
    global _mgr
    with _lock:
        if _mgr is not None:
            try:
                _mgr.shutdown()
            except Exception:
                pass
        _mgr = None
