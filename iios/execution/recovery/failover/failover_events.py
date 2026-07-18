"""
iios/execution/recovery/failover/failover_events.py
===================================================
Domain events emitted by the Failover Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import FailoverEventType, VERSION


@dataclass(frozen=True)
class FailoverEvent:
    """Immutable domain event emitted by the Failover Engine."""

    event_id:            str
    event_type:          FailoverEventType
    failover_session_id: str
    request_id:          str
    occurred_at:         float
    version:             str
    actor:               str            = ""
    action:              str            = ""
    reason:              str            = ""
    metadata:            Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":            self.event_id,
            "event_type":          self.event_type.value,
            "failover_session_id": self.failover_session_id,
            "request_id":          self.request_id,
            "occurred_at":         self.occurred_at,
            "actor":               self.actor,
            "action":              self.action,
            "reason":              self.reason,
        }


def _make_event(
    event_type: FailoverEventType,
    failover_session_id: str,
    request_id: str,
    *,
    actor: str = "",
    action: str = "",
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> FailoverEvent:
    return FailoverEvent(
        event_id            = event_id or str(uuid.uuid4()),
        event_type          = event_type,
        failover_session_id = failover_session_id,
        request_id          = request_id,
        occurred_at         = time.time(),
        version             = VERSION,
        actor               = actor,
        action              = action,
        reason              = reason,
        metadata            = dict(metadata) if metadata else {},
    )


def make_failover_started(
    failover_session_id: str, request_id: str, *, actor: str = "", action: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_STARTED, failover_session_id, request_id,
        actor=actor, action=action,
    )


def make_failover_prepared(
    failover_session_id: str, request_id: str, *, actor: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_PREPARED, failover_session_id, request_id, actor=actor,
    )


def make_failover_executed(
    failover_session_id: str, request_id: str, *, actor: str = "", action: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_EXECUTED, failover_session_id, request_id,
        actor=actor, action=action,
    )


def make_failover_verified(
    failover_session_id: str, request_id: str, *, actor: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_VERIFIED, failover_session_id, request_id, actor=actor,
    )


def make_failover_completed(
    failover_session_id: str, request_id: str, *, actor: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_COMPLETED, failover_session_id, request_id, actor=actor,
    )


def make_failover_failed(
    failover_session_id: str, request_id: str, *, actor: str = "", reason: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FAILOVER_FAILED, failover_session_id, request_id,
        actor=actor, reason=reason,
    )


def make_fallback_activated(
    failover_session_id: str, request_id: str, *, actor: str = "", action: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.FALLBACK_ACTIVATED, failover_session_id, request_id,
        actor=actor, action=action,
    )


def make_manual_escalation_requested(
    failover_session_id: str, request_id: str, *, actor: str = "", reason: str = ""
) -> FailoverEvent:
    return _make_event(
        FailoverEventType.MANUAL_ESCALATION_REQUESTED, failover_session_id, request_id,
        actor=actor, reason=reason,
    )
