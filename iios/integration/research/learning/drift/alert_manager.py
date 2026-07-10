"""drift/alert_manager.py — Alert generation for drift and monitoring events."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from iios.integration.research.learning.learning_constants import AlertSeverity


@dataclass
class Alert:
    """A single alert raised by the monitoring subsystem."""
    alert_id:   str
    severity:   AlertSeverity
    category:   str            # "drift" | "performance" | "training" | "system"
    model_id:   Optional[str]
    message:    str
    detail:     dict[str, Any]
    raised_at:  float
    resolved:   bool
    resolved_at: Optional[float]

    @classmethod
    def create(
        cls,
        severity:  AlertSeverity,
        category:  str,
        message:   str,
        *,
        alert_id:  Optional[str] = None,
        model_id:  Optional[str] = None,
        detail:    Optional[dict] = None,
    ) -> "Alert":
        return cls(
            alert_id    = alert_id or f"alt_{uuid.uuid4().hex[:10]}",
            severity    = severity,
            category    = category,
            model_id    = model_id,
            message     = message,
            detail      = detail or {},
            raised_at   = time.time(),
            resolved    = False,
            resolved_at = None,
        )

    def resolve(self) -> None:
        self.resolved    = True
        self.resolved_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id":    self.alert_id,
            "severity":    self.severity.value,
            "category":    self.category,
            "model_id":    self.model_id,
            "message":     self.message,
            "detail":      self.detail,
            "raised_at":   self.raised_at,
            "resolved":    self.resolved,
            "resolved_at": self.resolved_at,
        }


AlertHandler = Callable[[Alert], None]


class AlertManager:
    """Raises, stores, and dispatches learning-system alerts."""

    def __init__(self) -> None:
        self._alerts:   list[Alert]        = []
        self._handlers: list[AlertHandler] = []

    def register_handler(self, handler: AlertHandler) -> None:
        self._handlers.append(handler)

    def raise_alert(
        self,
        severity: AlertSeverity,
        category: str,
        message:  str,
        *,
        model_id: Optional[str] = None,
        detail:   Optional[dict] = None,
    ) -> Alert:
        alert = Alert.create(severity, category, message, model_id=model_id, detail=detail)
        self._alerts.append(alert)
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:
                pass
        return alert

    def resolve(self, alert_id: str) -> None:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolve()
                return

    def open_alerts(self, severity: Optional[AlertSeverity] = None) -> list[Alert]:
        alerts = [a for a in self._alerts if not a.resolved]
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def all_alerts(self, limit: int = 100) -> list[Alert]:
        return self._alerts[-limit:]

    def count(self) -> int:
        return len(self._alerts)

    def stats(self) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        for a in self._alerts:
            key = a.severity.value
            by_severity[key] = by_severity.get(key, 0) + 1
        return {
            "total":      len(self._alerts),
            "open":       sum(1 for a in self._alerts if not a.resolved),
            "by_severity": by_severity,
        }
