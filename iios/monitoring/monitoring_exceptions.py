"""
iios/monitoring/monitoring_exceptions.py
==========================================
Exception hierarchy for the IIOS Logging & Monitoring Framework.

Error codes: MON-001 → MON-012
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "MonitoringError",
    "LoggingError",
    "MetricError",
    "HealthCheckError",
    "AlertError",
    "TraceError",
    "DiagnosticError",
    "HeartbeatError",
    "NotificationError",
    "AuditError",
    "EventLogError",
    "RegistryError",
]


class MonitoringError(Exception):
    """Base exception for all monitoring errors."""

    def __init__(
        self,
        message: str,
        code: str = "MON-000",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"


class LoggingError(MonitoringError):
    def __init__(self, message: str, logger_name: str = "") -> None:
        super().__init__(message, "MON-001", {"logger": logger_name})
        self.logger_name = logger_name


class MetricError(MonitoringError):
    def __init__(self, message: str, metric_name: str = "") -> None:
        super().__init__(message, "MON-002", {"metric": metric_name})
        self.metric_name = metric_name


class HealthCheckError(MonitoringError):
    def __init__(self, message: str, check_name: str = "") -> None:
        super().__init__(message, "MON-003", {"check": check_name})
        self.check_name = check_name


class AlertError(MonitoringError):
    def __init__(self, message: str, alert_id: str = "") -> None:
        super().__init__(message, "MON-004", {"alert_id": alert_id})
        self.alert_id = alert_id


class TraceError(MonitoringError):
    def __init__(self, message: str, trace_id: str = "") -> None:
        super().__init__(message, "MON-005", {"trace_id": trace_id})
        self.trace_id = trace_id


class DiagnosticError(MonitoringError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "MON-006")


class HeartbeatError(MonitoringError):
    def __init__(self, message: str, component: str = "") -> None:
        super().__init__(message, "MON-007", {"component": component})
        self.component = component


class NotificationError(MonitoringError):
    def __init__(self, message: str, channel: str = "") -> None:
        super().__init__(message, "MON-008", {"channel": channel})
        self.channel = channel


class AuditError(MonitoringError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "MON-009")


class EventLogError(MonitoringError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "MON-010")


class RegistryError(MonitoringError):
    def __init__(self, message: str, name: str = "") -> None:
        super().__init__(message, "MON-011", {"name": name})
        self.name = name
