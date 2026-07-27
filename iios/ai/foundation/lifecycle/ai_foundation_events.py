"""
ai_foundation_events.py — iios.ai.foundation.lifecycle
=======================================================
Frozen lifecycle event dataclasses for the AI Foundation module.

All event objects are immutable (frozen dataclasses) and safe to share
across threads without copying.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    SCHEMA_VERSION,
    VERSION,
    AILifecycleEventType,
    AILifecycleState,
)


@dataclass(frozen=True)
class AILifecycleEvent:
    """
    Immutable lifecycle event emitted by :class:`AILifecycleAwareMixin`
    on every state transition.

    All AI modules (A1–A10) emit instances of this class (or subclasses)
    from their M1 lifecycle layer.

    Fields
    ------
    event_id :    Unique identifier for this event instance.
    event_type :  Structured event type (AILifecycleEventType).
    module_id :   Identifier of the emitting AI module.
    module_name : Human-readable module name (e.g. "AIFoundationGateway").
    from_state :  State before the transition.
    to_state :    State after the transition.
    timestamp :   Wall-clock time (``time.time()``) of emission.
    actor :       Identifier of the entity that triggered the transition.
    error :       Error message if the event represents a failure.
    metadata :    Optional key-value metadata.
    version :     Framework version string.
    schema :      Serialisation schema version.
    """
    event_type:  AILifecycleEventType
    module_id:   str
    from_state:  AILifecycleState
    to_state:    AILifecycleState
    timestamp:   float
    actor:       str                   = ACTOR_LIFECYCLE
    module_name: str                   = ""
    error:       Optional[str]         = None
    metadata:    Optional[Dict[str, Any]] = None
    event_id:    str                   = field(default_factory=lambda: str(uuid.uuid4()))
    version:     str                   = VERSION
    schema:      str                   = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for logging, persistence, or transport."""
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "module_id":   self.module_id,
            "module_name": self.module_name,
            "from_state":  self.from_state.value,
            "to_state":    self.to_state.value,
            "timestamp":   self.timestamp,
            "actor":       self.actor,
            "error":       self.error,
            "metadata":    self.metadata,
            "version":     self.version,
            "schema":      self.schema,
        }


# ---------------------------------------------------------------------------
# Convenience factories — one per transition type
# ---------------------------------------------------------------------------

def _make_event(
    event_type: AILifecycleEventType,
    module_id:  str,
    from_state: AILifecycleState,
    to_state:   AILifecycleState,
    *,
    actor:    str                   = ACTOR_LIFECYCLE,
    error:    Optional[str]         = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AILifecycleEvent:
    return AILifecycleEvent(
        event_type = event_type,
        module_id  = module_id,
        from_state = from_state,
        to_state   = to_state,
        timestamp  = time.time(),
        actor      = actor,
        error      = error,
        metadata   = metadata,
    )


def make_module_initialized(module_id: str, actor: str = ACTOR_LIFECYCLE) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_INITIALIZED,
        module_id,
        AILifecycleState.CREATED,
        AILifecycleState.INITIALIZED,
        actor=actor,
    )


def make_module_started(module_id: str, actor: str = ACTOR_LIFECYCLE) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_STARTED,
        module_id,
        AILifecycleState.INITIALIZED,
        AILifecycleState.RUNNING,
        actor=actor,
    )


def make_module_paused(module_id: str, actor: str = ACTOR_LIFECYCLE) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_PAUSED,
        module_id,
        AILifecycleState.RUNNING,
        AILifecycleState.PAUSED,
        actor=actor,
    )


def make_module_resumed(module_id: str, actor: str = ACTOR_LIFECYCLE) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_RESUMED,
        module_id,
        AILifecycleState.PAUSED,
        AILifecycleState.RUNNING,
        actor=actor,
    )


def make_module_stopped(module_id: str, actor: str = ACTOR_LIFECYCLE) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_STOPPED,
        module_id,
        AILifecycleState.STOPPING,
        AILifecycleState.STOPPED,
        actor=actor,
    )


def make_module_failed(
    module_id: str,
    from_state: AILifecycleState,
    error: str = "",
    actor: str = ACTOR_LIFECYCLE,
) -> AILifecycleEvent:
    return _make_event(
        AILifecycleEventType.MODULE_FAILED,
        module_id,
        from_state,
        AILifecycleState.FAILED,
        actor=actor,
        error=error,
    )
