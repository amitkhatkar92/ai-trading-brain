"""iios/execution/monitoring/alerts/exception_handler.py"""
from __future__ import annotations

import logging
from typing import Any, Callable

from iios.execution.monitoring.monitoring_constants import AlertSeverity
from iios.execution.monitoring.alerts.alert_manager import AlertManager
from iios.execution.monitoring.alerts.notification_event import Alert

logger = logging.getLogger(__name__)

ExceptionHandlerFn = Callable[[str, Exception, dict[str, Any]], None]


class ExceptionHandler:
    """
    Converts unhandled runtime exceptions in the execution pipeline into Alerts.

    Register callbacks for specific exception types to route them to
    the appropriate response (alert, escalate, suppress).
    """

    def __init__(self, alert_manager: AlertManager | None = None) -> None:
        self._alert_manager = alert_manager or AlertManager(load_defaults=False)
        self._handlers:      dict[type, ExceptionHandlerFn] = {}

    def register_handler(self, exc_type: type, handler: ExceptionHandlerFn) -> None:
        self._handlers[exc_type] = handler

    def handle(
        self,
        exc:        Exception,
        context:    dict[str, Any] = {},
        severity:   AlertSeverity  = AlertSeverity.HIGH,
        entity_id:  str            = "",
        entity_type: str           = "system",
    ) -> Alert:
        """Convert *exc* into an Alert and store it."""
        # Check for custom handler first
        handler = self._handlers.get(type(exc))
        if handler:
            handler(str(exc), exc, context)
        # Always create an alert
        alert = Alert(
            rule_name="exception_handler",
            severity=severity,
            title=f"Execution Exception: {type(exc).__name__}",
            message=str(exc),
            entity_id=entity_id,
            entity_type=entity_type,
            metadata={"exception_type": type(exc).__name__, "context": context},
        )
        self._alert_manager._engine._alerts.append(alert)
        logger.error("ExceptionHandler: %s — %s", type(exc).__name__, exc)
        return alert
