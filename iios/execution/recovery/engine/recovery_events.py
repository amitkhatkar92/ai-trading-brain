"""
iios/execution/recovery/engine/recovery_events.py
================================================
Domain events emitted by the Execution Recovery Engine.

Events are immutable and carry the full context needed by listeners.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

from .constants import RecoveryEngineEventType, VERSION


@dataclass(frozen=True)
class RecoveryEngineEvent:
    """Immutable domain event emitted by the Execution Recovery Engine."""

    event_id:    str
    event_type:  RecoveryEngineEventType
    request_id:  str
    session_id:  str
    occurred_at: float
    version:     str
    actor:       str            = ""
    reason:      str            = ""
    metadata:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "request_id":  self.request_id,
            "session_id":  self.session_id,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "actor":       self.actor,
            "reason":      self.reason,
        }


def _make_event(
    event_type: RecoveryEngineEventType,
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> RecoveryEngineEvent:
    return RecoveryEngineEvent(
        event_id    = event_id or str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        session_id  = session_id,
        occurred_at = time.time(),
        version     = VERSION,
        actor       = actor,
        reason      = reason,
        metadata    = dict(metadata) if metadata else {},
    )


def make_recovery_initialized(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_INITIALIZED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_started(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_STARTED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_failure_detected(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.FAILURE_DETECTED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_dispatched(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_DISPATCHED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_verified(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_VERIFIED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_completed(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_COMPLETED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_failed(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_FAILED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_recovery_stopped(
    request_id: str,
    session_id: str,
    *,
    actor: str = "",
    reason: str = "",
) -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.RECOVERY_STOPPED,
        request_id,
        session_id,
        actor=actor,
        reason=reason,
    )


def make_engine_started(*, actor: str = "") -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.ENGINE_STARTED,
        "",
        "",
        actor=actor,
    )


def make_engine_stopped(*, actor: str = "") -> RecoveryEngineEvent:
    return _make_event(
        RecoveryEngineEventType.ENGINE_STOPPED,
        "",
        "",
        actor=actor,
    )
