"""
iios/monitoring/monitoring_registry.py
========================================
Central registry binding all monitoring components together.

``MonitoringRegistry`` is the single entry point for obtaining any
monitoring service. It initialises all components, wires them together
(e.g. alert_manager → notification_manager), and exposes a unified API.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .alert_manager import AlertManager, get_alert_manager
from .audit_logger import AuditLogger, get_audit_logger
from .diagnostic_manager import DiagnosticManager, get_diagnostic_manager
from .error_logger import ErrorLogger, get_error_logger
from .event_logger import EventLogger, get_event_logger
from .health_manager import HealthManager, get_health_manager
from .heartbeat_manager import HeartbeatManager, get_heartbeat_manager
from .logger_factory import LoggerFactory, IIOSLogger
from .metrics_manager import MetricsManager, get_metrics_manager
from .notification_manager import NotificationManager, get_notification_manager
from .performance_logger import PerformanceLogger, get_performance_logger
from .structured_logger import StructuredLogger, get_structured_logger
from .trace_manager import TraceManager, get_trace_manager
from .monitoring_models import SystemHealthReport

__all__ = [
    "MonitoringRegistry",
    "get_monitoring_registry",
]

_LOG = logging.getLogger("iios.monitoring.registry")
_instance_lock = threading.Lock()
_instance: Optional["MonitoringRegistry"] = None


class MonitoringRegistry:
    """Unified access point for all IIOS monitoring services.

    Obtain any monitoring component through this registry to ensure they
    share the same singleton instances and are correctly wired together.

    Usage::

        reg = get_monitoring_registry()
        reg.initialize()

        log  = reg.get_logger("iios.risk", component="RiskGuardian")
        perf = reg.performance
        reg.metrics.increment("cycle.count")
    """

    def __init__(self) -> None:
        self._initialized = False
        self._lock = threading.Lock()
        self._factory: Optional[LoggerFactory] = None

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(
        self,
        log_dir: Optional[str] = None,
        log_level: str = "INFO",
        json_format: bool = False,
        health_background_interval: float = 0.0,
        heartbeat_monitoring: bool = False,
        auto_wire_alerts: bool = True,
    ) -> "MonitoringRegistry":
        """Bootstrap all monitoring components.

        Args:
            log_dir:                   Directory for log files.
            log_level:                 Root log level.
            json_format:               Use JSON-formatted logs.
            health_background_interval: Start health background runner.
            heartbeat_monitoring:      Start heartbeat monitor.
            auto_wire_alerts:          Wire alert_manager to notification_manager.
        """
        with self._lock:
            if self._initialized:
                return self

            # Logger factory
            self._factory = LoggerFactory(
                log_dir=log_dir,
                log_level=log_level,
                json_format=json_format,
            )

            # Wire alerting → notifications
            if auto_wire_alerts:
                notif = self.notifications
                alert = self.alerts
                alert.add_handler(notif.notify_alert)

            # Start health background if requested
            if health_background_interval > 0:
                health_mgr = self.health
                health_mgr._background_interval = health_background_interval
                health_mgr.start_background()

            # Start heartbeat monitor
            if heartbeat_monitoring:
                hb = self.heartbeats
                hb.start()

            self._initialized = True
            _LOG.info("MonitoringRegistry initialised")
            return self

    # ------------------------------------------------------------------
    # Component accessors
    # ------------------------------------------------------------------

    @property
    def metrics(self) -> MetricsManager:
        return get_metrics_manager()

    @property
    def health(self) -> HealthManager:
        return get_health_manager()

    @property
    def heartbeats(self) -> HeartbeatManager:
        return get_heartbeat_manager()

    @property
    def alerts(self) -> AlertManager:
        return get_alert_manager()

    @property
    def notifications(self) -> NotificationManager:
        return get_notification_manager()

    @property
    def traces(self) -> TraceManager:
        return get_trace_manager()

    @property
    def performance(self) -> PerformanceLogger:
        return get_performance_logger()

    @property
    def errors(self) -> ErrorLogger:
        return get_error_logger()

    @property
    def events(self) -> EventLogger:
        return get_event_logger()

    @property
    def audit(self) -> AuditLogger:
        return get_audit_logger()

    @property
    def diagnostics(self) -> DiagnosticManager:
        return get_diagnostic_manager()

    # ------------------------------------------------------------------
    # Logger helpers
    # ------------------------------------------------------------------

    def get_logger(
        self,
        name: str,
        component: str = "",
        layer: str = "",
        **extra: Any,
    ) -> IIOSLogger:
        """Return a configured ``IIOSLogger``."""
        from .logger_factory import get_logger
        return get_logger(name, component=component, layer=layer, **extra)

    def get_structured(
        self,
        name: str,
        component: str = "",
        layer: str = "",
    ) -> StructuredLogger:
        """Return a ``StructuredLogger`` for *name*."""
        return get_structured_logger(name, component=component, layer=layer)

    # ------------------------------------------------------------------
    # Convenience — full system status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a concise dict summarising the monitoring system state."""
        health_report = self.health.check_all()
        diag = self.diagnostics.latest()
        return {
            "health": {
                "overall": health_report.overall_status,
                "summary": health_report.summary,
            },
            "metrics": {
                "series_count": self.metrics.series_count,
                "uptime_seconds": round(self.metrics.uptime_seconds(), 1),
            },
            "alerts": {
                "open": self.alerts.open_count,
                "total": self.alerts.alert_count,
                "critical": self.alerts.critical_count(),
            },
            "errors": {
                "total": self.errors.total_errors,
                "unique": self.errors.unique_error_count,
            },
            "traces": {
                "total": self.traces.trace_count,
                "active": self.traces.active_count,
            },
            "diagnostics": {
                "cpu_percent": diag.cpu_percent if diag else 0.0,
                "mem_percent": diag.mem_percent if diag else 0.0,
                "active_threads": diag.extras.get("active_threads", 0) if diag else 0,
            },
        }

    @property
    def is_initialized(self) -> bool:
        return self._initialized


def get_monitoring_registry() -> MonitoringRegistry:
    """Return (or create) the global ``MonitoringRegistry`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = MonitoringRegistry()
        return _instance


def _reset_monitoring_registry() -> None:
    global _instance
    with _instance_lock:
        _instance = None
