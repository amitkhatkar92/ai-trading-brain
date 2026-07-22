"""
portfolio_policy_events.py — iios.portfolio.policies
=====================================================
Event value objects and eight factory functions for the Portfolio Policy
Framework lifecycle.

All event objects are immutable frozen dataclasses.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    POLICY_SYSTEM_ID,
    VERSION,
    PolicyAction,
    PolicyEventType,
)


@dataclass(frozen=True)
class PolicyEngineEvent:
    """
    Immutable portfolio policy lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the eight PolicyEventType values.
    evaluation_id :     Evaluation run that produced the event.
    portfolio_id :      Portfolio associated with the event.
    policy_id :         Specific policy involved (empty for run-level events).
    source :            Identifier of the component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of event occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        PolicyEventType
    evaluation_id:     str
    portfolio_id:      str
    policy_id:         str
    source:            str
    payload:           Dict[str, Any]
    occurred_at:       float
    framework_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "evaluation_id":     self.evaluation_id,
            "portfolio_id":      self.portfolio_id,
            "policy_id":         self.policy_id,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:    PolicyEventType,
    evaluation_id: str,
    portfolio_id:  str,
    *,
    policy_id: str = "",
    source:    str = POLICY_SYSTEM_ID,
    payload:   Optional[Dict[str, Any]] = None,
) -> PolicyEngineEvent:
    return PolicyEngineEvent(
        event_id          = str(uuid.uuid4()),
        event_type        = event_type,
        evaluation_id     = evaluation_id,
        portfolio_id      = portfolio_id,
        policy_id         = policy_id,
        source            = source,
        payload           = dict(payload or {}),
        occurred_at       = time.time(),
        framework_version = VERSION,
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per PolicyEventType
# ---------------------------------------------------------------------------

def make_policy_evaluation_started(
    evaluation_id: str,
    portfolio_id:  str,
    *,
    policy_count: int = 0,
    source:       str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when a policy evaluation run begins."""
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_STARTED,
        evaluation_id,
        portfolio_id,
        source  = source,
        payload = {"policy_count": policy_count},
    )


def make_policy_loaded(
    evaluation_id: str,
    portfolio_id:  str,
    policy_id:     str,
    policy_name:   str = "",
    *,
    source: str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when a policy is loaded for evaluation."""
    return _make_event(
        PolicyEventType.POLICY_LOADED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"policy_name": policy_name},
    )


def make_policy_validated(
    evaluation_id: str,
    portfolio_id:  str,
    policy_id:     str,
    *,
    passed: bool = True,
    source: str  = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted after a policy passes configuration validation."""
    return _make_event(
        PolicyEventType.POLICY_VALIDATED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"passed": passed},
    )


def make_policy_approved(
    evaluation_id: str,
    portfolio_id:  str,
    *,
    policy_id: str = "",
    source:    str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when the final evaluation outcome is APPROVE."""
    return _make_event(
        PolicyEventType.POLICY_APPROVED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"action": PolicyAction.APPROVE.value},
    )


def make_policy_rejected(
    evaluation_id: str,
    portfolio_id:  str,
    *,
    reason:    str = "",
    policy_id: str = "",
    source:    str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when the final evaluation outcome is REJECT."""
    return _make_event(
        PolicyEventType.POLICY_REJECTED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"action": PolicyAction.REJECT.value, "reason": reason},
    )


def make_policy_blocked(
    evaluation_id: str,
    portfolio_id:  str,
    *,
    reason:    str = "",
    policy_id: str = "",
    source:    str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when the final evaluation outcome is BLOCK."""
    return _make_event(
        PolicyEventType.POLICY_BLOCKED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"action": PolicyAction.BLOCK.value, "reason": reason},
    )


def make_policy_escalated(
    evaluation_id: str,
    portfolio_id:  str,
    *,
    reason:    str = "",
    policy_id: str = "",
    source:    str = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when the final evaluation outcome is ESCALATE."""
    return _make_event(
        PolicyEventType.POLICY_ESCALATED,
        evaluation_id,
        portfolio_id,
        policy_id = policy_id,
        source    = source,
        payload   = {"action": PolicyAction.ESCALATE.value, "reason": reason},
    )


def make_policy_evaluation_completed(
    evaluation_id: str,
    portfolio_id:  str,
    final_action:  PolicyAction,
    *,
    elapsed_s:     float = 0.0,
    total_policies: int  = 0,
    source:        str   = POLICY_SYSTEM_ID,
) -> PolicyEngineEvent:
    """Emitted when a policy evaluation run completes."""
    return _make_event(
        PolicyEventType.POLICY_EVALUATION_COMPLETED,
        evaluation_id,
        portfolio_id,
        source  = source,
        payload = {
            "final_action":   final_action.value,
            "elapsed_s":      elapsed_s,
            "total_policies": total_policies,
        },
    )
