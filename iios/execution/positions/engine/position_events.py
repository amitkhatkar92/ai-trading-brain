"""iios/execution/positions/engine/position_events.py
==================================================
EngineEvent — immutable domain event emitted by the Position Engine.

Factory functions produce one event per engine milestone.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import ACTOR_ENGINE, EngineEventType, VERSION


@dataclass(frozen=True)
class EngineEvent:
    """
    Immutable domain event emitted by the Position Engine.

    Events are append-only and never mutated after creation.
    """

    event_id:     str
    event_type:   EngineEventType
    position_id:  str
    portfolio_id: str
    strategy_id:  str
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
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "metadata":    dict(self.metadata),
        }


# ── Private helper ────────────────────────────────────────────────────────────

def _evt(
    event_type:   EngineEventType,
    position_id:  str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return EngineEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_position_created_event(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.POSITION_CREATED, position_id, portfolio_id, strategy_id, actor, metadata)


def make_position_updated_event(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.POSITION_UPDATED, position_id, portfolio_id, strategy_id, actor, metadata)


def make_position_closed_event(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.POSITION_CLOSED, position_id, portfolio_id, strategy_id, actor, metadata)


def make_position_synchronized_event(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.POSITION_SYNCHRONIZED, position_id, portfolio_id, strategy_id, actor, metadata)


def make_position_archived_event(
    position_id:  str,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.POSITION_ARCHIVED, position_id, portfolio_id, strategy_id, actor, metadata)


def make_engine_started_event(
    actor:    str = ACTOR_ENGINE,
    metadata: Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.ENGINE_STARTED, actor=actor, metadata=metadata)


def make_engine_stopped_event(
    actor:    str = ACTOR_ENGINE,
    metadata: Dict[str, Any] | None = None,
) -> EngineEvent:
    return _evt(EngineEventType.ENGINE_STOPPED, actor=actor, metadata=metadata)
