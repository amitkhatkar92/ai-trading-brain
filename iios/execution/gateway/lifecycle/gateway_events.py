"""iios/execution/gateway/lifecycle/gateway_events.py
==================================================
GatewayEvent — immutable domain event emitted by the execution
gateway lifecycle.

Factory functions produce one event per lifecycle milestone.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    ACTOR_LIFECYCLE,
    GatewayEventType,
    GatewayState,
    VERSION,
)


@dataclass(frozen=True)
class GatewayEvent:
    """
    Immutable domain event emitted by the execution gateway lifecycle layer.

    Events are append-only and never mutated after creation.
    """

    event_id:     str
    event_type:   GatewayEventType
    gateway_id:   str
    execution_id: str
    portfolio_id: str
    strategy_id:  str
    state:        GatewayState
    actor:        str
    occurred_at:  float
    version:      str               = VERSION
    metadata:     Dict[str, Any]    = field(default_factory=dict, compare=False)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "gateway_id":   self.gateway_id,
            "execution_id": self.execution_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id":  self.strategy_id,
            "state":        self.state.value,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
            "version":      self.version,
            "metadata":     dict(self.metadata),
        }


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_event(
    event_type:   GatewayEventType,
    gateway_id:   str,
    state:        GatewayState,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return GatewayEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        gateway_id=gateway_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        state=state,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_gateway_created(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_CREATED, gateway_id, GatewayState.CREATED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_received(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_RECEIVED, gateway_id, GatewayState.RECEIVED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_validated(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_VALIDATED, gateway_id, GatewayState.READY,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_queued(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_QUEUED, gateway_id, GatewayState.QUEUED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_dispatched(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_DISPATCHED, gateway_id, GatewayState.DISPATCHED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_completed(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_COMPLETED, gateway_id, GatewayState.COMPLETED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_failed(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_FAILED, gateway_id, GatewayState.FAILED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_cancelled(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_CANCELLED, gateway_id, GatewayState.CANCELLED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_gateway_archived(
    gateway_id:   str,
    execution_id: str                    = "",
    portfolio_id: str                    = "",
    strategy_id:  str                    = "",
    actor:        str                    = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None  = None,
) -> GatewayEvent:
    return _make_event(
        GatewayEventType.GATEWAY_ARCHIVED, gateway_id, GatewayState.ARCHIVED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )
