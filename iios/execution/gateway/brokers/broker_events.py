"""iios/execution/gateway/brokers/broker_events.py
==================================================
BrokerEvent — immutable domain event emitted by the Broker
Abstraction Layer.

Factory functions produce one event per BAL milestone.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_BROKER_MANAGER, BROKER_SYSTEM_ID, BrokerEventType, VERSION


@dataclass(frozen=True)
class BrokerEvent:
    """
    Immutable domain event emitted by the Broker Abstraction Layer.

    Events are append-only and never mutated after creation.
    """

    event_id:    str
    event_type:  BrokerEventType
    broker_id:   str
    actor:       str
    occurred_at: float
    version:     str             = VERSION
    metadata:    Dict[str, Any]  = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_connection_event(self) -> bool:
        return self.event_type in (
            BrokerEventType.BROKER_CONNECTED,
            BrokerEventType.BROKER_DISCONNECTED,
            BrokerEventType.RECONNECT_STARTED,
            BrokerEventType.RECONNECT_SUCCEEDED,
        )

    @property
    def is_auth_event(self) -> bool:
        return self.event_type in (
            BrokerEventType.AUTHENTICATION_SUCCEEDED,
            BrokerEventType.AUTHENTICATION_FAILED,
            BrokerEventType.SESSION_EXPIRED,
        )

    @property
    def is_health_event(self) -> bool:
        return self.event_type == BrokerEventType.BROKER_HEALTH_CHANGED

    @property
    def is_failure_event(self) -> bool:
        return self.event_type in (
            BrokerEventType.AUTHENTICATION_FAILED,
            BrokerEventType.SESSION_EXPIRED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "broker_id":  self.broker_id,
            "actor":      self.actor,
            "occurred_at": self.occurred_at,
            "version":    self.version,
            "metadata":   dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"BrokerEvent("
            f"event_type={self.event_type.value!r}, "
            f"broker_id={self.broker_id!r}"
            f")"
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def _make_event(
    event_type: BrokerEventType,
    broker_id:  str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return BrokerEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        broker_id=broker_id,
        actor=actor,
        occurred_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_broker_registered_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.BROKER_REGISTERED, broker_id, actor=actor, metadata=metadata)


def make_broker_connected_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.BROKER_CONNECTED, broker_id, actor=actor, metadata=metadata)


def make_broker_disconnected_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.BROKER_DISCONNECTED, broker_id, actor=actor, metadata=metadata)


def make_authentication_succeeded_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.AUTHENTICATION_SUCCEEDED, broker_id, actor=actor, metadata=metadata)


def make_authentication_failed_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.AUTHENTICATION_FAILED, broker_id, actor=actor, metadata=metadata)


def make_session_expired_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.SESSION_EXPIRED, broker_id, actor=actor, metadata=metadata)


def make_reconnect_started_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.RECONNECT_STARTED, broker_id, actor=actor, metadata=metadata)


def make_reconnect_succeeded_event(
    broker_id: str,
    *,
    actor:    str = ACTOR_BROKER_MANAGER,
    metadata: Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    return _make_event(BrokerEventType.RECONNECT_SUCCEEDED, broker_id, actor=actor, metadata=metadata)


def make_health_changed_event(
    broker_id: str,
    *,
    is_healthy: bool = True,
    actor:      str = ACTOR_BROKER_MANAGER,
    metadata:   Optional[Dict[str, Any]] = None,
) -> BrokerEvent:
    meta = dict(metadata or {})
    meta["is_healthy"] = is_healthy
    return _make_event(BrokerEventType.BROKER_HEALTH_CHANGED, broker_id, actor=actor, metadata=meta)
