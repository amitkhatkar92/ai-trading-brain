"""iios/execution/gateway/engine/gateway_events.py
==================================================
GatewayEngineEvent — immutable domain event emitted by the
Execution Gateway Engine.

Seven factory functions produce one event per engine milestone:
  make_gateway_started_event
  make_request_received_event
  make_request_queued_event
  make_request_dispatched_event
  make_dispatch_completed_event
  make_dispatch_failed_event
  make_gateway_stopped_event

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import ACTOR_ENGINE, EngineEventType, VERSION


# ── GatewayEngineEvent ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GatewayEngineEvent:
    """
    Immutable domain event emitted by the Execution Gateway Engine.

    Events are append-only and never mutated after creation.
    Engine-level events (GATEWAY_STARTED, GATEWAY_STOPPED) leave
    ``request_id`` and ``gateway_id`` empty.
    """

    event_id:     str
    event_type:   EngineEventType
    gateway_id:   str             # M1 lifecycle request ID; empty for engine-level events
    request_id:   str             # EngineGatewayRequest.request_id
    execution_id: str
    portfolio_id: str
    strategy_id:  str
    actor:        str
    occurred_at:  float
    version:      str             = VERSION
    metadata:     Dict[str, Any]  = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_engine_event(self) -> bool:
        """True for engine-level events that are not tied to a specific request."""
        return self.event_type in (
            EngineEventType.GATEWAY_STARTED,
            EngineEventType.GATEWAY_STOPPED,
        )

    @property
    def is_success_event(self) -> bool:
        return self.event_type == EngineEventType.DISPATCH_COMPLETED

    @property
    def is_failure_event(self) -> bool:
        return self.event_type == EngineEventType.DISPATCH_FAILED

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "gateway_id":   self.gateway_id,
            "request_id":   self.request_id,
            "execution_id": self.execution_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id":  self.strategy_id,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
            "version":      self.version,
            "metadata":     dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"GatewayEngineEvent("
            f"event_type={self.event_type.value!r}, "
            f"request_id={self.request_id!r}, "
            f"occurred_at={self.occurred_at})"
        )


# ── Internal helper ───────────────────────────────────────────────────────────

def _make_event(
    event_type:   EngineEventType,
    *,
    gateway_id:   str = "",
    request_id:   str = "",
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    return GatewayEngineEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Factory functions ─────────────────────────────────────────────────────────

def make_gateway_started_event(
    *,
    actor:    str = ACTOR_ENGINE,
    metadata: Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """Engine has started and is ready to accept requests."""
    return _make_event(
        EngineEventType.GATEWAY_STARTED,
        actor=actor,
        metadata=metadata,
    )


def make_request_received_event(
    request_id:   str,
    execution_id: str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    gateway_id:   str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """A request has been received and registered by the engine."""
    return _make_event(
        EngineEventType.REQUEST_RECEIVED,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_request_queued_event(
    request_id:   str,
    execution_id: str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    gateway_id:   str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """A request has been placed in the dispatch queue."""
    return _make_event(
        EngineEventType.REQUEST_QUEUED,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_request_dispatched_event(
    request_id:   str,
    execution_id: str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    gateway_id:   str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """A request has been handed to the broker abstraction layer."""
    return _make_event(
        EngineEventType.REQUEST_DISPATCHED,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_dispatch_completed_event(
    request_id:   str,
    execution_id: str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    gateway_id:   str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """Dispatch was accepted by the broker abstraction layer."""
    return _make_event(
        EngineEventType.DISPATCH_COMPLETED,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_dispatch_failed_event(
    request_id:   str,
    execution_id: str,
    portfolio_id: str,
    strategy_id:  str,
    *,
    gateway_id:   str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """Dispatch was rejected, deferred, or errored."""
    return _make_event(
        EngineEventType.DISPATCH_FAILED,
        gateway_id=gateway_id,
        request_id=request_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_gateway_stopped_event(
    *,
    actor:    str = ACTOR_ENGINE,
    metadata: Optional[Dict[str, Any]] = None,
) -> GatewayEngineEvent:
    """Engine has stopped."""
    return _make_event(
        EngineEventType.GATEWAY_STOPPED,
        actor=actor,
        metadata=metadata,
    )
