"""iios/decision_governance/monitoring/governance_alerts.py

Alert system for governance events.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from iios.decision_governance.governance_constants import AlertSeverity


@dataclass
class GovernanceAlert:
    alert_id:    str          = field(default_factory=lambda: str(uuid.uuid4()))
    severity:    AlertSeverity = AlertSeverity.INFO
    message:     str          = ""
    source:      str          = ""
    decision_id: str          = ""
    details:     dict         = field(default_factory=dict)
    timestamp:   float        = field(default_factory=time.time)
    acknowledged: bool        = False

    def to_dict(self) -> dict:
        return {
            "alert_id":     self.alert_id,
            "severity":     self.severity.value,
            "message":      self.message,
            "source":       self.source,
            "decision_id":  self.decision_id,
            "details":      self.details,
            "timestamp":    self.timestamp,
            "acknowledged": self.acknowledged,
        }


AlertHandler = Callable[[GovernanceAlert], None]


class GovernanceAlerts:
    """
    Publishes governance alerts to registered handlers.
    Handlers are called synchronously in the order they were registered.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock             = threading.RLock()
        self._alerts:   list[GovernanceAlert]       = []
        self._handlers: list[AlertHandler]          = []

    def add_handler(self, handler: AlertHandler) -> None:
        with self._lock:
            self._handlers.append(handler)

    def raise_alert(
        self,
        severity:    AlertSeverity,
        message:     str,
        source:      str = "",
        decision_id: str = "",
        details:     dict | None = None,
    ) -> GovernanceAlert:
        alert = GovernanceAlert(
            severity=severity,
            message=message,
            source=source,
            decision_id=decision_id,
            details=details or {},
        )
        with self._lock:
            self._alerts.append(alert)
            handlers = list(self._handlers)

        for handler in handlers:
            try:
                handler(alert)
            except Exception:  # noqa: BLE001
                pass  # handlers must not crash the engine

        return alert

    def acknowledge(self, alert_id: str) -> bool:
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def unacknowledged(self) -> list[GovernanceAlert]:
        with self._lock:
            return [a for a in self._alerts if not a.acknowledged]

    def all(self) -> list[GovernanceAlert]:
        with self._lock:
            return list(self._alerts)

    def count(self) -> int:
        with self._lock:
            return len(self._alerts)
