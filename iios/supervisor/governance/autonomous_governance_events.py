"""
autonomous_governance_events.py — iios.supervisor.governance
-------------------------------------------------------------
Event value objects and factory functions for the Autonomous Governance
Framework.

12 event types (matching the spec):
  GovernanceStarted
  SnapshotsCollected
  DependencyGraphBuilt
  AnomalyDetected
  IncidentCorrelated
  RootCauseIdentified
  RecommendationsGenerated
  SelfHealingGenerated
  EnterpriseAssessmentCompleted
  GovernancePublished
  GovernanceEngineStarted
  GovernanceEngineStopped

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
    VERSION,
    AutonomousGovernanceEventType,
)


@dataclass(frozen=True)
class AutonomousGovernanceEvent:
    """
    Immutable autonomous governance framework event.

    Fields
    ------
    event_id :          Unique identifier.
    event_type :        One of the AutonomousGovernanceEventType values.
    supervision_id :    Supervision run identifier.
    source :            Component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        AutonomousGovernanceEventType
    supervision_id:    str            = ""
    source:            str            = AUTONOMOUS_GOVERNANCE_SYSTEM_ID
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
    event_type:     AutonomousGovernanceEventType,
    supervision_id: str = "",
    *,
    payload: Optional[Dict[str, Any]] = None,
    source:  str = AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
) -> AutonomousGovernanceEvent:
    return AutonomousGovernanceEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        supervision_id = supervision_id,
        source         = source,
        payload        = payload or {},
    )


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def make_governance_started_event(
    supervision_id: str = "",
    *,
    request_id: str = "",
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.GOVERNANCE_STARTED,
        supervision_id,
        payload={"request_id": request_id},
    )


def make_snapshots_collected_event(
    supervision_id: str = "",
    *,
    snapshot_count: int = 0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.SNAPSHOTS_COLLECTED,
        supervision_id,
        payload={"snapshot_count": snapshot_count},
    )


def make_dependency_graph_built_event(
    supervision_id: str = "",
    *,
    dependency_count: int = 0,
    critical_paths:   int = 0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.DEPENDENCY_GRAPH_BUILT,
        supervision_id,
        payload={
            "dependency_count": dependency_count,
            "critical_paths":   critical_paths,
        },
    )


def make_anomaly_detected_event(
    supervision_id: str = "",
    *,
    anomaly_count:   int = 0,
    critical_count:  int = 0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.ANOMALY_DETECTED,
        supervision_id,
        payload={
            "anomaly_count":  anomaly_count,
            "critical_count": critical_count,
        },
    )


def make_incident_correlated_event(
    supervision_id: str = "",
    *,
    incident_count: int = 0,
    severity:       str = "",
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.INCIDENT_CORRELATED,
        supervision_id,
        payload={"incident_count": incident_count, "severity": severity},
    )


def make_root_cause_identified_event(
    supervision_id: str = "",
    *,
    root_cause_count: int = 0,
    identified_count: int = 0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.ROOT_CAUSE_IDENTIFIED,
        supervision_id,
        payload={
            "root_cause_count": root_cause_count,
            "identified_count": identified_count,
        },
    )


def make_recommendations_generated_event(
    supervision_id: str = "",
    *,
    recommendation_count: int = 0,
    critical_count:       int = 0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.RECOMMENDATIONS_GENERATED,
        supervision_id,
        payload={
            "recommendation_count": recommendation_count,
            "critical_count":       critical_count,
        },
    )


def make_self_healing_generated_event(
    supervision_id: str = "",
    *,
    action_count:     int  = 0,
    can_auto_execute: bool = False,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.SELF_HEALING_GENERATED,
        supervision_id,
        payload={
            "action_count":     action_count,
            "can_auto_execute": can_auto_execute,
        },
    )


def make_enterprise_assessment_completed_event(
    supervision_id: str = "",
    *,
    enterprise_state:  str   = "",
    final_decision:    str   = "",
    elapsed_s:         float = 0.0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.ENTERPRISE_ASSESSMENT_COMPLETED,
        supervision_id,
        payload={
            "enterprise_state": enterprise_state,
            "final_decision":   final_decision,
            "elapsed_s":        elapsed_s,
        },
    )


def make_governance_published_event(
    supervision_id: str = "",
    *,
    summary_id:   str   = "",
    is_success:   bool  = True,
    elapsed_s:    float = 0.0,
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.GOVERNANCE_PUBLISHED,
        supervision_id,
        payload={
            "summary_id": summary_id,
            "is_success": is_success,
            "elapsed_s":  elapsed_s,
        },
    )


def make_governance_engine_started_event(
    supervision_id: str = "",
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STARTED,
        supervision_id,
    )


def make_governance_engine_stopped_event(
    supervision_id: str = "",
) -> AutonomousGovernanceEvent:
    return _make_event(
        AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STOPPED,
        supervision_id,
    )
