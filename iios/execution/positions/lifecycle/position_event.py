"""iios/execution/positions/lifecycle/position_event.py
==================================================
PositionEvent — immutable domain event emitted by the position lifecycle.

Factory functions produce one event per lifecycle milestone.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    ACTOR_LIFECYCLE,
    PositionEventType,
    PositionState,
    VERSION,
)


@dataclass(frozen=True)
class PositionEvent:
    """
    Immutable domain event emitted by the position lifecycle layer.

    Events are append-only and never mutated after creation.
    """

    event_id:     str
    event_type:   PositionEventType
    position_id:  str
    portfolio_id: str
    strategy_id:  str
    state:        PositionState
    actor:        str
    occurred_at:  float
    version:      str = VERSION
    metadata:     Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "position_id": self.position_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "state":       self.state.value,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "metadata":    dict(self.metadata),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_event(
    event_type:   PositionEventType,
    position_id:  str,
    state:        PositionState,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return PositionEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        state=state,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_position_created(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_CREATED,
        position_id, PositionState.CREATED,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_opened(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_OPENED,
        position_id, PositionState.OPEN,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_updated(
    position_id:  str,
    state:        PositionState,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_UPDATED,
        position_id, state,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_partially_closed(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_PARTIALLY_CLOSED,
        position_id, PositionState.PARTIALLY_CLOSED,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_closed(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_CLOSED,
        position_id, PositionState.CLOSED,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_recovered(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_RECOVERED,
        position_id, PositionState.RECOVERED,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )


def make_position_archived(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> PositionEvent:
    return _make_event(
        PositionEventType.POSITION_ARCHIVED,
        position_id, PositionState.ARCHIVED,
        portfolio_id=portfolio_id, strategy_id=strategy_id,
        actor=actor, metadata=metadata,
    )
