"""iios/execution/risk/engine/execution_risk_events.py
==================================================
RiskEngineEvent — immutable domain event emitted by the Execution Risk
Engine throughout the evaluation lifecycle.

Factory functions produce one event per engine milestone.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    ACTOR_ENGINE,
    ENGINE_SYSTEM_ID,
    EngineEventType,
    RuleOutcome,
    VERSION,
)


@dataclass(frozen=True)
class RiskEngineEvent:
    """
    Immutable domain event emitted during an evaluation.

    Listeners registered with the manager receive these events as each
    lifecycle milestone is reached.
    """

    event_id:      str
    event_type:    EngineEventType
    evaluation_id: str
    portfolio_id:  str
    strategy_id:   str
    rule_name:     str
    actor:         str
    occurred_at:   float
    version:       str = VERSION
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "evaluation_id": self.evaluation_id,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "rule_name":     self.rule_name,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "version":       self.version,
            "metadata":      dict(self.metadata),
        }


# ── Shared helper ─────────────────────────────────────────────────────────────

def _make_event(
    event_type:    EngineEventType,
    evaluation_id: str = "",
    portfolio_id:  str = "",
    strategy_id:   str = "",
    rule_name:     str = "",
    actor:         str = ACTOR_ENGINE,
    metadata:      Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return RiskEngineEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        rule_name=rule_name,
        actor=actor,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_evaluation_started_event(
    evaluation_id: str,
    *,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return _make_event(
        EngineEventType.EVALUATION_STARTED,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=metadata,
    )


def make_rule_execution_started_event(
    evaluation_id: str,
    rule_name:     str,
    *,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return _make_event(
        EngineEventType.RULE_EXECUTION_STARTED,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        rule_name=rule_name,
        actor=actor,
        metadata=metadata,
    )


def make_rule_execution_completed_event(
    evaluation_id: str,
    rule_name:     str,
    outcome:       RuleOutcome,
    *,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    meta = {"outcome": outcome.value, **(metadata or {})}
    return _make_event(
        EngineEventType.RULE_EXECUTION_COMPLETED,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        rule_name=rule_name,
        actor=actor,
        metadata=meta,
    )


def make_evaluation_completed_event(
    evaluation_id: str,
    outcome:       RuleOutcome,
    *,
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    meta = {"outcome": outcome.value, **(metadata or {})}
    return _make_event(
        EngineEventType.EVALUATION_COMPLETED,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=meta,
    )


def make_evaluation_failed_event(
    evaluation_id: str,
    *,
    reason:       str = "",
    portfolio_id: str = "",
    strategy_id:  str = "",
    actor:        str = ACTOR_ENGINE,
    metadata:     Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    meta = {"reason": reason, **(metadata or {})}
    return _make_event(
        EngineEventType.EVALUATION_FAILED,
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        actor=actor,
        metadata=meta,
    )


def make_snapshot_published_event(
    *,
    actor:    str = ACTOR_ENGINE,
    metadata: Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return _make_event(
        EngineEventType.SNAPSHOT_PUBLISHED,
        actor=actor,
        metadata=metadata,
    )


def make_engine_started_event(
    *,
    actor:    str = ACTOR_ENGINE,
    metadata: Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return _make_event(
        EngineEventType.ENGINE_STARTED,
        actor=actor,
        metadata=metadata,
    )


def make_engine_stopped_event(
    *,
    actor:    str = ACTOR_ENGINE,
    metadata: Dict[str, Any] | None = None,
) -> RiskEngineEvent:
    return _make_event(
        EngineEventType.ENGINE_STOPPED,
        actor=actor,
        metadata=metadata,
    )
