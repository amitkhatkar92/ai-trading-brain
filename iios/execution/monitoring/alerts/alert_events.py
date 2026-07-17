"""iios/execution/monitoring/alerts/alert_events.py
==================================================
Domain events emitted by the Execution Alert Framework.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import AlertEventType, VERSION


@dataclass(frozen=True)
class AlertEvent:
    """Immutable domain event emitted by the Alert Framework."""

    event_id:    str
    event_type:  AlertEventType
    session_id:  str
    alert_id:    str
    actor:       str
    occurred_at: float
    version:     str
    reason:      Optional[str]
    metadata:    Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "alert_id":    self.alert_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "reason":      self.reason,
        }


# ── Internal factory ──────────────────────────────────────────────────────────

def _make_alert_event(
    event_type: AlertEventType,
    session_id: str,
    alert_id:   str,
    actor:      str,
    *,
    reason:   Optional[str]            = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AlertEvent:
    return AlertEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        session_id  = session_id,
        alert_id    = alert_id,
        actor       = actor,
        occurred_at = time.time(),
        version     = VERSION,
        reason      = reason,
        metadata    = dict(metadata) if metadata else {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_alert_generated(
    session_id: str,
    alert_id:   str,
    actor:      str = "engine",
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_GENERATED, session_id, alert_id, actor, reason=reason
    )


def make_alert_acknowledged(
    session_id: str,
    alert_id:   str,
    actor:      str,
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_ACKNOWLEDGED, session_id, alert_id, actor, reason=reason
    )


def make_alert_escalated(
    session_id: str,
    alert_id:   str,
    actor:      str = "engine",
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_ESCALATED, session_id, alert_id, actor, reason=reason
    )


def make_alert_resolved(
    session_id: str,
    alert_id:   str,
    actor:      str,
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_RESOLVED, session_id, alert_id, actor, reason=reason
    )


def make_alert_expired(
    session_id: str,
    alert_id:   str,
    actor:      str = "engine",
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_EXPIRED, session_id, alert_id, actor, reason=reason
    )


def make_alert_suppressed(
    session_id: str,
    alert_id:   str,
    actor:      str = "engine",
    *,
    reason: Optional[str] = None,
) -> AlertEvent:
    return _make_alert_event(
        AlertEventType.ALERT_SUPPRESSED, session_id, alert_id, actor, reason=reason
    )
