"""iios/execution/recovery/lifecycle/recovery_events.py
==================================================
RecoveryEvent — immutable domain events emitted by RecoveryLifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .constants import RecoveryEventType, RecoveryState, VERSION


@dataclass(frozen=True)
class RecoveryEvent:
    """
    Immutable domain event emitted on every recovery lifecycle transition.

    Fields
    ------
    event_id:     Globally unique event ID.
    event_type:   Classification of this event.
    session_id:   Owning recovery session.
    actor:        Component that triggered the event.
    occurred_at:  Wall-time of the event.
    version:      Framework version.
    reason:       Optional human-readable context.
    metadata:     Optional supplementary data.
    """

    event_id:    str
    event_type:  RecoveryEventType
    session_id:  str
    actor:       str
    occurred_at: float
    version:     str
    reason:      Optional[str]   = None
    metadata:    Dict[str, Any]  = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "reason":      self.reason,
            "metadata":    dict(self.metadata),
        }


# ── Internal factory helper ───────────────────────────────────────────────────

def _make_event(
    event_type: RecoveryEventType,
    session_id: str,
    *,
    actor:    str             = "iios:execution:recovery:lifecycle",
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        session_id = session_id,
        actor      = actor,
        occurred_at= time.time(),
        version    = VERSION,
        reason     = reason,
        metadata   = metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_recovery_created(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_CREATED, session_id, actor=actor, reason=reason)

def make_recovery_initialized(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_INITIALIZED, session_id, actor=actor, reason=reason)

def make_recovery_detecting(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_DETECTING, session_id, actor=actor, reason=reason)

def make_recovery_assessing(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_ASSESSING, session_id, actor=actor, reason=reason)

def make_recovery_ready(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_READY, session_id, actor=actor, reason=reason)

def make_recovery_started(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_STARTED, session_id, actor=actor, reason=reason)

def make_recovery_verifying(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_VERIFYING, session_id, actor=actor, reason=reason)

def make_recovery_completed(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_COMPLETED, session_id, actor=actor, reason=reason)

def make_recovery_failed(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_FAILED, session_id, actor=actor, reason=reason)

def make_recovery_aborted(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_ABORTED, session_id, actor=actor, reason=reason)

def make_recovery_archived(session_id: str, *, actor: str = "iios:execution:recovery:lifecycle", reason: Optional[str] = None) -> RecoveryEvent:
    return _make_event(RecoveryEventType.RECOVERY_ARCHIVED, session_id, actor=actor, reason=reason)


# ── State → event factory mapping ────────────────────────────────────────────

_STATE_EVENT_FACTORY: Dict[RecoveryState, Callable[[str], RecoveryEvent]] = {
    RecoveryState.INITIALIZING: make_recovery_initialized,
    RecoveryState.DETECTING:    make_recovery_detecting,
    RecoveryState.ASSESSING:    make_recovery_assessing,
    RecoveryState.READY:        make_recovery_ready,
    RecoveryState.RECOVERING:   make_recovery_started,
    RecoveryState.VERIFYING:    make_recovery_verifying,
    RecoveryState.COMPLETED:    make_recovery_completed,
    RecoveryState.FAILED:       make_recovery_failed,
    RecoveryState.ABORTED:      make_recovery_aborted,
    RecoveryState.ARCHIVED:     make_recovery_archived,
}
