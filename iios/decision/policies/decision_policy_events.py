"""
decision_policy_events.py — iios.decision.policies
====================================================
Event value objects and factory functions for the Policy Framework.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import VERSION, PolicyAction, PolicyEventType


@dataclass(frozen=True)
class DecisionPolicyEvent:
    """
    Immutable event emitted by the Decision Policy Framework.

    Parameters
    ----------
    event_id :          Unique event identifier.
    event_type :        The type of event.
    request_id :        Originating evaluation request ID.
    decision_id :       Decision being evaluated.
    source :            Component that emitted the event.
    payload :           Event-specific data.
    occurred_at :       When the event occurred.
    framework_version : Framework version string.
    """

    event_id:          str
    event_type:        PolicyEventType
    request_id:        str
    decision_id:       str
    source:            str
    payload:           Dict[str, Any]
    occurred_at:       datetime
    framework_version: str = VERSION

    def to_dict(self) -> dict:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "source":            self.source,
            "payload":           self.payload,
            "occurred_at":       self.occurred_at.isoformat(),
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Factory functions — one per PolicyEventType
# ---------------------------------------------------------------------------

def _make_event(
    event_type:  PolicyEventType,
    request_id:  str,
    decision_id: str,
    source:      str,
    payload:     Dict[str, Any],
) -> DecisionPolicyEvent:
    return DecisionPolicyEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        decision_id = decision_id,
        source      = source,
        payload     = payload,
        occurred_at = datetime.now(timezone.utc),
    )


def make_policy_evaluation_started(
    request_id:       str,
    decision_id:      str,
    source:           str,
    *,
    policy_count:     int  = 0,
    chain_mode:       str  = "",
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_STARTED,
        request_id, decision_id, source,
        {"policy_count": policy_count, "chain_mode": chain_mode},
    )


def make_policy_loaded(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    policy_id:   str = "",
    policy_name: str = "",
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_LOADED,
        request_id, decision_id, source,
        {"policy_id": policy_id, "policy_name": policy_name},
    )


def make_policy_validated(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    policy_id:   str  = "",
    is_valid:    bool = True,
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_VALIDATED,
        request_id, decision_id, source,
        {"policy_id": policy_id, "is_valid": is_valid},
    )


def make_policy_approved(
    request_id:    str,
    decision_id:   str,
    source:        str,
    *,
    action:        str  = "approve",
    has_conditions: bool = False,
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_APPROVED,
        request_id, decision_id, source,
        {"action": action, "has_conditions": has_conditions},
    )


def make_policy_rejected(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    reason:      str = "",
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_REJECTED,
        request_id, decision_id, source,
        {"reason": reason},
    )


def make_policy_blocked(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    reason:      str = "",
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_BLOCKED,
        request_id, decision_id, source,
        {"reason": reason},
    )


def make_policy_escalated(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    reason:      str = "",
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_ESCALATED,
        request_id, decision_id, source,
        {"reason": reason},
    )


def make_policy_evaluation_completed(
    request_id:       str,
    decision_id:      str,
    source:           str,
    *,
    final_action:     str   = "",
    evaluation_time_s: float = 0.0,
    total_evaluated:  int   = 0,
) -> DecisionPolicyEvent:
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_COMPLETED,
        request_id, decision_id, source,
        {
            "final_action":      final_action,
            "evaluation_time_s": evaluation_time_s,
            "total_evaluated":   total_evaluated,
        },
    )
