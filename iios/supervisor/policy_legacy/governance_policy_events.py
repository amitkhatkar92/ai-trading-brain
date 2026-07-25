"""
governance_policy_events.py — iios.supervisor.policy
------------------------------------------------------
Event value objects and factory functions for the governance policy framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import POLICY_SYSTEM_ID, VERSION, GovernancePolicyEventType


@dataclass(frozen=True)
class GovernancePolicyEvent:
    """
    Immutable governance policy framework event.

    Fields
    ------
    event_id :          Unique identifier.
    event_type :        One of the :class:`GovernancePolicyEventType` values.
    supervision_id :    Supervision run identifier.
    source :            Component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        GovernancePolicyEventType
    supervision_id:    str            = ""
    source:            str            = POLICY_SYSTEM_ID
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


def _make_event(
    event_type:     GovernancePolicyEventType,
    supervision_id: str = "",
    *,
    source:  str = POLICY_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> GovernancePolicyEvent:
    return GovernancePolicyEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        supervision_id = supervision_id,
        source         = source,
        payload        = payload or {},
    )


def make_policy_registered_event(
    supervision_id: str = "",
    *,
    policy_id: str = "",
    policy_name: str = "",
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.POLICY_REGISTERED,
        supervision_id,
        payload={"policy_id": policy_id, "policy_name": policy_name},
    )


def make_policy_unregistered_event(
    supervision_id: str = "",
    *,
    policy_id: str = "",
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.POLICY_UNREGISTERED,
        supervision_id,
        payload={"policy_id": policy_id},
    )


def make_evaluation_started_event(
    supervision_id: str = "",
    *,
    request_id: str = "",
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.EVALUATION_STARTED,
        supervision_id,
        payload={"request_id": request_id},
    )


def make_evaluation_completed_event(
    supervision_id: str = "",
    *,
    request_id:   str   = "",
    final_action: str   = "",
    elapsed_s:    float = 0.0,
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.EVALUATION_COMPLETED,
        supervision_id,
        payload={"request_id": request_id, "final_action": final_action, "elapsed_s": elapsed_s},
    )


def make_evaluation_failed_event(
    supervision_id: str = "",
    *,
    request_id: str = "",
    reason:     str = "",
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.EVALUATION_FAILED,
        supervision_id,
        payload={"request_id": request_id, "reason": reason},
    )


def make_engine_started_event(supervision_id: str = "") -> GovernancePolicyEvent:
    return _make_event(GovernancePolicyEventType.POLICY_ENGINE_STARTED, supervision_id)


def make_engine_stopped_event(supervision_id: str = "") -> GovernancePolicyEvent:
    return _make_event(GovernancePolicyEventType.POLICY_ENGINE_STOPPED, supervision_id)


def make_conflict_resolved_event(
    supervision_id: str = "",
    *,
    dominant_policy_id: str = "",
    final_action:       str = "",
) -> GovernancePolicyEvent:
    return _make_event(
        GovernancePolicyEventType.CONFLICT_RESOLVED,
        supervision_id,
        payload={"dominant_policy_id": dominant_policy_id, "final_action": final_action},
    )
