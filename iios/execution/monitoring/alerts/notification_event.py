"""iios/execution/monitoring/alerts/notification_event.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import AlertSeverity, AlertStatus


@dataclass
class Alert:
    """An alert raised by an AlertRule evaluation."""

    rule_name:      str          = ""
    severity:       AlertSeverity = AlertSeverity.HIGH
    status:         AlertStatus   = AlertStatus.ACTIVE
    title:          str          = ""
    message:        str          = ""
    entity_id:      str          = ""
    entity_type:    str          = ""
    broker_id:      str          = ""
    alert_id:       str          = field(default_factory=lambda: str(uuid.uuid4()))
    triggered_at:   float        = field(default_factory=time.time)
    acknowledged_at: float | None = None
    resolved_at:    float | None  = None
    metadata:       dict[str, Any] = field(default_factory=dict)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def acknowledge(self, user: str = "system") -> None:
        self.status          = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = time.time()
        self.metadata["acknowledged_by"] = user

    def resolve(self, reason: str = "") -> None:
        self.status      = AlertStatus.RESOLVED
        self.resolved_at = time.time()
        if reason:
            self.metadata["resolution"] = reason

    def suppress(self) -> None:
        self.status = AlertStatus.SUPPRESSED

    def is_active(self) -> bool:
        return self.status == AlertStatus.ACTIVE

    def age_sec(self) -> float:
        return time.time() - self.triggered_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id":       self.alert_id,
            "rule_name":      self.rule_name,
            "severity":       self.severity.value,
            "status":         self.status.value,
            "title":          self.title,
            "message":        self.message,
            "entity_id":      self.entity_id,
            "entity_type":    self.entity_type,
            "broker_id":      self.broker_id,
            "triggered_at":   self.triggered_at,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at":    self.resolved_at,
            "metadata":       self.metadata,
        }
