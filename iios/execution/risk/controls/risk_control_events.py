"""iios/execution/risk/controls/risk_control_events.py
==================================================
ControlEvent and factory functions for the Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_ENGINE,
    CONTROLS_SYSTEM_ID,
    VERSION,
    ControlAction,
    ControlEventType,
    PolicyType,
)


@dataclass(frozen=True)
class ControlEvent:
    """Immutable domain event emitted by the Controls Framework."""

    event_id:      str
    event_type:    ControlEventType
    decision_id:   str
    evaluation_id: str
    action:        Optional[ControlAction]
    policy_used:   Optional[PolicyType]
    actor:         str
    occurred_at:   float
    version:       str
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "decision_id":   self.decision_id,
            "evaluation_id": self.evaluation_id,
            "action":        self.action.value if self.action else None,
            "policy_used":   self.policy_used.value if self.policy_used else None,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "version":       self.version,
        }


def _event(
    event_type:    ControlEventType,
    decision_id:   str,
    evaluation_id: str,
    action:        Optional[ControlAction] = None,
    policy_used:   Optional[PolicyType]   = None,
    actor:         str = ACTOR_ENGINE,
    metadata:      Dict[str, Any] | None = None,
) -> ControlEvent:
    return ControlEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        decision_id=decision_id,
        evaluation_id=evaluation_id,
        action=action,
        policy_used=policy_used,
        actor=actor,
        occurred_at=time.time(),
        version=VERSION,
        metadata=metadata or {},
    )


def make_control_evaluated_event(
    decision_id: str, evaluation_id: str, action: ControlAction,
    policy_used: PolicyType, *, metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.CONTROL_EVALUATED, decision_id, evaluation_id,
                  action, policy_used, metadata=metadata)


def make_control_approved_event(
    decision_id: str, evaluation_id: str, action: ControlAction,
    *, metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.CONTROL_APPROVED, decision_id, evaluation_id,
                  action, metadata=metadata)


def make_control_paused_event(
    decision_id: str, evaluation_id: str,
    *, metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.CONTROL_PAUSED, decision_id, evaluation_id,
                  ControlAction.PAUSE, metadata=metadata)


def make_control_retried_event(
    decision_id: str, evaluation_id: str,
    *, metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.CONTROL_RETRIED, decision_id, evaluation_id,
                  ControlAction.RETRY, metadata=metadata)


def make_override_requested_event(
    decision_id: str, evaluation_id: str, original_action: ControlAction,
    *, approver: str = "", metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.OVERRIDE_REQUESTED, decision_id, evaluation_id,
                  original_action, metadata={**(metadata or {}), "approver": approver})


def make_override_approved_event(
    decision_id: str, evaluation_id: str, new_action: ControlAction,
    *, approver: str = "", override_id: str = "", metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.OVERRIDE_APPROVED, decision_id, evaluation_id,
                  new_action, metadata={
                      **(metadata or {}),
                      "approver":   approver,
                      "override_id": override_id,
                  })


def make_execution_blocked_event(
    decision_id: str, evaluation_id: str, action: ControlAction,
    *, reason: str = "", metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.EXECUTION_BLOCKED, decision_id, evaluation_id,
                  action, metadata={**(metadata or {}), "reason": reason})


def make_emergency_triggered_event(
    decision_id: str, evaluation_id: str,
    *, trigger: str = "", halt_level: str = "TRADING",
    metadata: Dict[str, Any] | None = None,
) -> ControlEvent:
    return _event(ControlEventType.EMERGENCY_TRIGGERED, decision_id, evaluation_id,
                  ControlAction.EMERGENCY_STOP, metadata={
                      **(metadata or {}),
                      "trigger":    trigger,
                      "halt_level": halt_level,
                  })
