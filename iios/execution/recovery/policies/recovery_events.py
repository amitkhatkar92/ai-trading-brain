"""
iios/execution/recovery/policies/recovery_events.py
===================================================
Domain events emitted by the Recovery Policy Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import PolicyEventType, VERSION


@dataclass(frozen=True)
class RecoveryPolicyEvent:
    """Immutable domain event emitted by the Recovery Policy Engine."""

    event_id:    str
    event_type:  PolicyEventType
    request_id:  str
    decision_id: str
    occurred_at: float
    version:     str
    actor:       str            = ""
    policy_name: str            = ""
    reason:      str            = ""
    metadata:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "request_id":  self.request_id,
            "decision_id": self.decision_id,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "actor":       self.actor,
            "policy_name": self.policy_name,
            "reason":      self.reason,
        }


def _make_event(
    event_type: PolicyEventType,
    request_id: str,
    decision_id: str,
    *,
    actor: str = "",
    policy_name: str = "",
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> RecoveryPolicyEvent:
    return RecoveryPolicyEvent(
        event_id    = event_id or str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        decision_id = decision_id,
        occurred_at = time.time(),
        version     = VERSION,
        actor       = actor,
        policy_name = policy_name,
        reason      = reason,
        metadata    = dict(metadata) if metadata else {},
    )


def make_policy_evaluation_started(
    request_id: str, *, actor: str = "", policy_name: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_STARTED,
        request_id, "", actor=actor, policy_name=policy_name,
    )


def make_policy_evaluated(
    request_id: str, decision_id: str, *, actor: str = "", policy_name: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_EVALUATED,
        request_id, decision_id, actor=actor, policy_name=policy_name,
    )


def make_strategy_selected(
    request_id: str, decision_id: str, *, actor: str = "", policy_name: str = "", reason: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.STRATEGY_SELECTED,
        request_id, decision_id, actor=actor, policy_name=policy_name, reason=reason,
    )


def make_decision_published(
    request_id: str, decision_id: str, *, actor: str = "", policy_name: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.DECISION_PUBLISHED,
        request_id, decision_id, actor=actor, policy_name=policy_name,
    )


def make_fallback_policy_selected(
    request_id: str, *, actor: str = "", reason: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.FALLBACK_POLICY_SELECTED,
        request_id, "", actor=actor, policy_name="ManualInterventionPolicy", reason=reason,
    )


def make_policy_evaluation_failed(
    request_id: str, *, actor: str = "", reason: str = "", policy_name: str = ""
) -> RecoveryPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_FAILED,
        request_id, "", actor=actor, policy_name=policy_name, reason=reason,
    )


def make_engine_started(*, actor: str = "") -> RecoveryPolicyEvent:
    return _make_event(PolicyEventType.ENGINE_STARTED, "", "", actor=actor)


def make_engine_stopped(*, actor: str = "") -> RecoveryPolicyEvent:
    return _make_event(PolicyEventType.ENGINE_STOPPED, "", "", actor=actor)
