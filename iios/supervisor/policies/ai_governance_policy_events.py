"""
ai_governance_policy_events.py — iios.supervisor.policies
-----------------------------------------------------------
Event value objects and factory functions for the AI Governance Policy
Framework.

Nine event types (matching the spec):
  GovernanceEvaluationStarted
  GovernancePolicyLoaded
  GovernancePolicyValidated
  GovernanceApproved
  GovernanceRejected
  GovernanceBlocked
  HumanApprovalRequested
  EmergencyStopTriggered
  GovernanceCompleted

Plus two engine lifecycle events:
  PolicyEngineStarted
  PolicyEngineStopped

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import AI_GOVERNANCE_SYSTEM_ID, VERSION, AIGovernancePolicyEventType


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIGovernancePolicyEvent:
    """
    Immutable AI governance policy framework event.

    Fields
    ------
    event_id :          Unique identifier.
    event_type :        One of the :class:`AIGovernancePolicyEventType` values.
    supervision_id :    Supervision run identifier.
    source :            Component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        AIGovernancePolicyEventType
    supervision_id:    str            = ""
    source:            str            = AI_GOVERNANCE_SYSTEM_ID
    payload:           Dict[str, Any] = field(default_factory=dict)
    occurred_at:       float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "supervision_id":    self.supervision_id,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:     AIGovernancePolicyEventType,
    supervision_id: str = "",
    *,
    source:  str = AI_GOVERNANCE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> AIGovernancePolicyEvent:
    return AIGovernancePolicyEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        supervision_id = supervision_id,
        source         = source,
        payload        = payload or {},
    )


# ---------------------------------------------------------------------------
# Factory functions — one per event type
# ---------------------------------------------------------------------------

def make_evaluation_started_event(
    supervision_id: str = "",
    *,
    request_id: str = "",
    workflow_type: str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.EVALUATION_STARTED,
        supervision_id,
        payload={"request_id": request_id, "workflow_type": workflow_type},
    )


def make_policy_loaded_event(
    supervision_id: str = "",
    *,
    policy_id:    str = "",
    policy_name:  str = "",
    policy_type:  str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.POLICY_LOADED,
        supervision_id,
        payload={"policy_id": policy_id, "policy_name": policy_name, "policy_type": policy_type},
    )


def make_policy_validated_event(
    supervision_id: str = "",
    *,
    policy_id: str = "",
    is_valid:  bool = True,
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.POLICY_VALIDATED,
        supervision_id,
        payload={"policy_id": policy_id, "is_valid": is_valid},
    )


def make_governance_approved_event(
    supervision_id: str = "",
    *,
    request_id:       str   = "",
    final_action:     str   = "",
    policies_evaluated: int = 0,
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.APPROVED,
        supervision_id,
        payload={"request_id": request_id, "final_action": final_action,
                 "policies_evaluated": policies_evaluated},
    )


def make_governance_rejected_event(
    supervision_id: str = "",
    *,
    request_id:          str = "",
    dominant_policy_id:  str = "",
    rationale:           str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.REJECTED,
        supervision_id,
        payload={"request_id": request_id, "dominant_policy_id": dominant_policy_id,
                 "rationale": rationale},
    )


def make_governance_blocked_event(
    supervision_id: str = "",
    *,
    request_id:         str = "",
    dominant_policy_id: str = "",
    rationale:          str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.BLOCKED,
        supervision_id,
        payload={"request_id": request_id, "dominant_policy_id": dominant_policy_id,
                 "rationale": rationale},
    )


def make_human_approval_requested_event(
    supervision_id: str = "",
    *,
    request_id:         str = "",
    dominant_policy_id: str = "",
    rationale:          str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.HUMAN_APPROVAL_REQUESTED,
        supervision_id,
        payload={"request_id": request_id, "dominant_policy_id": dominant_policy_id,
                 "rationale": rationale},
    )


def make_emergency_stop_triggered_event(
    supervision_id: str = "",
    *,
    request_id:         str = "",
    dominant_policy_id: str = "",
    rationale:          str = "",
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.EMERGENCY_STOP_TRIGGERED,
        supervision_id,
        payload={"request_id": request_id, "dominant_policy_id": dominant_policy_id,
                 "rationale": rationale},
    )


def make_evaluation_completed_event(
    supervision_id: str = "",
    *,
    request_id:    str   = "",
    final_action:  str   = "",
    elapsed_s:     float = 0.0,
    is_success:    bool  = True,
) -> AIGovernancePolicyEvent:
    return _make_event(
        AIGovernancePolicyEventType.EVALUATION_COMPLETED,
        supervision_id,
        payload={"request_id": request_id, "final_action": final_action,
                 "elapsed_s": elapsed_s, "is_success": is_success},
    )


def make_engine_started_event(supervision_id: str = "") -> AIGovernancePolicyEvent:
    return _make_event(AIGovernancePolicyEventType.POLICY_ENGINE_STARTED, supervision_id)


def make_engine_stopped_event(supervision_id: str = "") -> AIGovernancePolicyEvent:
    return _make_event(AIGovernancePolicyEventType.POLICY_ENGINE_STOPPED, supervision_id)
