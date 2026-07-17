"""iios/execution/gateway/routing/routing_events.py
==================================================
RoutingEvent — domain event emitted by the Routing Framework —
and factory functions for each event type.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_ROUTING_ENGINE,
    ROUTING_SYSTEM_ID,
    RoutingEventType,
    VERSION,
)


@dataclass(frozen=True)
class RoutingEvent:
    """
    Immutable domain event for the Routing Framework.

    Events are fired in the order they occur during route()
    and delivered synchronously to registered listeners.
    """

    event_id:   str
    event_type: RoutingEventType
    routing_id: str
    actor:      str
    occurred_at: float
    version:    str = VERSION

    # Optional correlation / detail fields
    broker_id:  Optional[str] = None
    policy_id:  Optional[str] = None
    metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "routing_id":  self.routing_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "broker_id":   self.broker_id,
            "policy_id":   self.policy_id,
            "metadata":    dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"RoutingEvent("
            f"type={self.event_type.value!r}, "
            f"routing_id={self.routing_id!r}"
            f")"
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def _make_event(
    event_type:  RoutingEventType,
    routing_id:  str,
    *,
    actor:      str                    = ACTOR_ROUTING_ENGINE,
    broker_id:  Optional[str]          = None,
    policy_id:  Optional[str]          = None,
    metadata:   Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return RoutingEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        routing_id=routing_id,
        actor=actor,
        occurred_at=time.time(),
        broker_id=broker_id,
        policy_id=policy_id,
        metadata=dict(metadata or {}),
    )


def make_routing_started_event(
    routing_id: str,
    *,
    actor:    str = ACTOR_ROUTING_ENGINE,
    metadata: Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.ROUTING_STARTED,
        routing_id,
        actor=actor,
        metadata=metadata,
    )


def make_routing_completed_event(
    routing_id: str,
    *,
    broker_id: Optional[str] = None,
    actor:     str = ACTOR_ROUTING_ENGINE,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.ROUTING_COMPLETED,
        routing_id,
        actor=actor,
        broker_id=broker_id,
        metadata=metadata,
    )


def make_broker_selected_event(
    routing_id: str,
    broker_id:  str,
    *,
    policy_id: Optional[str] = None,
    actor:     str = ACTOR_ROUTING_ENGINE,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.BROKER_SELECTED,
        routing_id,
        actor=actor,
        broker_id=broker_id,
        policy_id=policy_id,
        metadata=metadata,
    )


def make_broker_rejected_event(
    routing_id: str,
    broker_id:  str,
    *,
    policy_id: Optional[str] = None,
    actor:     str = ACTOR_ROUTING_ENGINE,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.BROKER_REJECTED,
        routing_id,
        actor=actor,
        broker_id=broker_id,
        policy_id=policy_id,
        metadata=metadata,
    )


def make_failover_activated_event(
    routing_id: str,
    broker_id:  str,
    *,
    policy_id: Optional[str] = None,
    actor:     str = ACTOR_ROUTING_ENGINE,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.FAILOVER_ACTIVATED,
        routing_id,
        actor=actor,
        broker_id=broker_id,
        policy_id=policy_id,
        metadata=metadata,
    )


def make_policy_applied_event(
    routing_id: str,
    policy_id:  str,
    *,
    actor:    str = ACTOR_ROUTING_ENGINE,
    metadata: Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.POLICY_APPLIED,
        routing_id,
        actor=actor,
        policy_id=policy_id,
        metadata=metadata,
    )


def make_routing_failed_event(
    routing_id: str,
    *,
    actor:     str = ACTOR_ROUTING_ENGINE,
    policy_id: Optional[str] = None,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingEvent:
    return _make_event(
        RoutingEventType.ROUTING_FAILED,
        routing_id,
        actor=actor,
        policy_id=policy_id,
        metadata=metadata,
    )
