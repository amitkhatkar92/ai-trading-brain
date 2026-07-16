"""iios/execution/brokers/broker_events.py
==================================================
BrokerEvent and BrokerEventType — events emitted by the broker layer.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerHealthStatus,
    BrokerRequestType,
    BrokerResponseStatus,
)


class BrokerEventType(str, Enum):
    """All events that may be emitted by the Broker Abstraction Layer."""

    BROKER_REGISTERED   = "BROKER_REGISTERED"
    BROKER_UNREGISTERED = "BROKER_UNREGISTERED"
    BROKER_CONNECTED    = "BROKER_CONNECTED"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    BROKER_HEALTHY      = "BROKER_HEALTHY"
    BROKER_UNHEALTHY    = "BROKER_UNHEALTHY"
    REQUEST_VALIDATED   = "REQUEST_VALIDATED"
    RESPONSE_RECEIVED   = "RESPONSE_RECEIVED"
    HEARTBEAT_SENT      = "HEARTBEAT_SENT"


# ── Event ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerEvent:
    """Immutable event record emitted by the broker layer."""

    event_id:      str            = field(default_factory=lambda: str(uuid.uuid4()))
    broker_id:     str            = ""
    event_type:    BrokerEventType = BrokerEventType.BROKER_REGISTERED
    occurred_at:   float          = field(default_factory=time.time)
    connection_state: Optional[BrokerConnectionState] = None
    health_status:    Optional[BrokerHealthStatus]    = None
    request_type:     Optional[BrokerRequestType]     = None
    response_status:  Optional[BrokerResponseStatus]  = None
    request_id:    str            = ""
    correlation_id: str           = ""
    error_message: str            = ""
    payload:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "broker_id":        self.broker_id,
            "event_type":       self.event_type.value,
            "occurred_at":      self.occurred_at,
            "connection_state": self.connection_state.value if self.connection_state else None,
            "health_status":    self.health_status.value    if self.health_status    else None,
            "request_type":     self.request_type.value     if self.request_type     else None,
            "response_status":  self.response_status.value  if self.response_status  else None,
            "request_id":       self.request_id,
            "correlation_id":   self.correlation_id,
            "error_message":    self.error_message,
            "payload":          self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerEvent(type={self.event_type.value}, "
            f"broker={self.broker_id!r}, id={self.event_id[:8]})"
        )


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_broker_event(
    broker_id:  str,
    event_type: BrokerEventType,
    *,
    connection_state: Optional[BrokerConnectionState] = None,
    health_status:    Optional[BrokerHealthStatus]    = None,
    request_type:     Optional[BrokerRequestType]     = None,
    response_status:  Optional[BrokerResponseStatus]  = None,
    request_id:    str           = "",
    correlation_id: str          = "",
    error_message:  str          = "",
    payload:        dict[str, Any] | None = None,
    occurred_at:    float        = 0.0,
) -> BrokerEvent:
    return BrokerEvent(
        broker_id        = broker_id,
        event_type       = event_type,
        occurred_at      = occurred_at or time.time(),
        connection_state = connection_state,
        health_status    = health_status,
        request_type     = request_type,
        response_status  = response_status,
        request_id       = request_id,
        correlation_id   = correlation_id,
        error_message    = error_message,
        payload          = payload or {},
    )
