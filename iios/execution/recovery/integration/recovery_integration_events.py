"""
iios/execution/recovery/integration/recovery_integration_events.py
==================================================================
IntegrationEvent — immutable events emitted by the Integration subsystem.

Eight event types covering the full integration lifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_INTEGRATION, VERSION, IntegrationEventType


@dataclass(frozen=True)
class IntegrationEvent:
    """Immutable event emitted by the Integration subsystem."""

    event_id:   str
    event_type: IntegrationEventType
    request_id: str
    occurred_at: float
    version:    str
    actor:      str
    reason:     str
    metadata:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "request_id": self.request_id,
            "occurred_at": self.occurred_at,
            "version":    self.version,
            "actor":      self.actor,
            "reason":     self.reason,
            "metadata":   dict(self.metadata),
        }


def _make(
    event_type: IntegrationEventType,
    request_id: str = "",
    *,
    actor: str = ACTOR_INTEGRATION,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        request_id = request_id,
        occurred_at = time.time(),
        version    = VERSION,
        actor      = actor,
        reason     = reason,
        metadata   = dict(metadata) if metadata else {},
    )


def make_recovery_initialized(
    request_id: str = "", *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_INITIALIZED, request_id, actor=actor, **kw)


def make_recovery_started(
    request_id: str, *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_STARTED, request_id, actor=actor, **kw)


def make_recovery_completed(
    request_id: str, *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_COMPLETED, request_id, actor=actor, **kw)


def make_recovery_stopped(
    request_id: str = "", *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_STOPPED, request_id, actor=actor, **kw)


def make_recovery_restarted(
    *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_RESTARTED, "", actor=actor, **kw)


def make_recovery_validated(
    request_id: str, *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(IntegrationEventType.RECOVERY_VALIDATED, request_id, actor=actor, **kw)


def make_recovery_health_changed(
    health: str, request_id: str = "", *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.RECOVERY_HEALTH_CHANGED,
        request_id,
        actor=actor,
        reason=f"health={health}",
        **kw,
    )


def make_recovery_snapshot_published(
    request_id: str, snapshot_id: str, *, actor: str = ACTOR_INTEGRATION, **kw
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.RECOVERY_SNAPSHOT_PUBLISHED,
        request_id,
        actor=actor,
        metadata={"snapshot_id": snapshot_id},
        **kw,
    )
