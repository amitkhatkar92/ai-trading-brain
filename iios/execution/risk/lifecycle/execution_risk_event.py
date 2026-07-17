"""iios/execution/risk/lifecycle/execution_risk_event.py
==================================================
RiskEvent — immutable domain event emitted by the execution risk lifecycle.

Factory functions produce one event per lifecycle milestone.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    ACTOR_LIFECYCLE,
    RiskEventType,
    RiskState,
    VERSION,
)


@dataclass(frozen=True)
class RiskEvent:
    """
    Immutable domain event emitted by the execution risk lifecycle layer.

    Events are append-only and never mutated after creation.
    """

    event_id:     str
    event_type:   RiskEventType
    risk_id:      str
    execution_id: str
    portfolio_id: str
    strategy_id:  str
    state:        RiskState
    actor:        str
    occurred_at:  float
    version:      str = VERSION
    metadata:     Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "risk_id":      self.risk_id,
            "execution_id": self.execution_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id":  self.strategy_id,
            "state":        self.state.value,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
            "version":      self.version,
            "metadata":     dict(self.metadata),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_event(
    event_type:   RiskEventType,
    risk_id:      str,
    state:        RiskState,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return RiskEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        risk_id=risk_id,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        state=state,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_risk_created(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_CREATED,
        risk_id, RiskState.CREATED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_evaluation_started(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_EVALUATION_STARTED,
        risk_id, RiskState.EVALUATING,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_passed(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_PASSED,
        risk_id, RiskState.PASSED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_warning(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_WARNING,
        risk_id, RiskState.WARNING,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_blocked(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_BLOCKED,
        risk_id, RiskState.BLOCKED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_overridden(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_OVERRIDDEN,
        risk_id, RiskState.OVERRIDDEN,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_expired(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_EXPIRED,
        risk_id, RiskState.EXPIRED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )


def make_risk_archived(
    risk_id:      str,
    execution_id: str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_LIFECYCLE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_ARCHIVED,
        risk_id, RiskState.ARCHIVED,
        execution_id=execution_id, portfolio_id=portfolio_id,
        strategy_id=strategy_id, actor=actor, metadata=metadata,
    )
