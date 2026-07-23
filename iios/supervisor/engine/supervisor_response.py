"""
supervisor_response.py — iios.supervisor.engine
-------------------------------------------------
Supervisor workflow response and snapshot value objects.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    EngineState,
    SupervisorWorkflowType,
    ResponseStatus,
)


# ---------------------------------------------------------------------------
# SupervisorEngineSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorEngineSnapshot:
    """
    Immutable point-in-time snapshot of a supervisor workflow output.

    Published at the end of every successful supervisor pipeline.

    Fields
    ------
    snapshot_id :         Unique identifier.
    supervision_id :      Supervision run identifier.
    subsystem_id :        Target subsystem identifier.
    session_id :          Owning lifecycle session.
    workflow_type :       Workflow that produced this snapshot.
    engine_state :        Engine state at publication time.
    subsystems_collected: List of subsystem IDs whose snapshots were collected.
    health_summary :      Aggregated health information.
    outputs :             Produced supervision outputs.
    published_at :        Wall-clock publication time.
    framework_version :   Framework version string.
    """
    snapshot_id:          str
    supervision_id:       str
    subsystem_id:         str
    session_id:           str
    workflow_type:        SupervisorWorkflowType
    engine_state:         EngineState
    subsystems_collected: List[str]       = field(default_factory=list)
    health_summary:       Dict[str, Any]  = field(default_factory=dict)
    outputs:              Dict[str, Any]  = field(default_factory=dict)
    published_at:         float           = field(default_factory=time.time)
    framework_version:    str             = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        session_id:     str,
        workflow_type:  SupervisorWorkflowType,
        engine_state:   EngineState,
        *,
        snapshot_id:          Optional[str]           = None,
        subsystems_collected: Optional[List[str]]     = None,
        health_summary:       Optional[Dict[str, Any]] = None,
        outputs:              Optional[Dict[str, Any]] = None,
    ) -> "SupervisorEngineSnapshot":
        return cls(
            snapshot_id          = snapshot_id or str(uuid.uuid4()),
            supervision_id       = supervision_id,
            subsystem_id         = subsystem_id,
            session_id           = session_id,
            workflow_type        = workflow_type,
            engine_state         = engine_state,
            subsystems_collected = list(subsystems_collected or []),
            health_summary       = dict(health_summary or {}),
            outputs              = dict(outputs or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "supervision_id":       self.supervision_id,
            "subsystem_id":         self.subsystem_id,
            "session_id":           self.session_id,
            "workflow_type":        self.workflow_type.value,
            "engine_state":         self.engine_state.value,
            "subsystems_collected": list(self.subsystems_collected),
            "health_summary":       dict(self.health_summary),
            "outputs":              dict(self.outputs),
            "published_at":         self.published_at,
            "framework_version":    self.framework_version,
        }


# ---------------------------------------------------------------------------
# SupervisorResponse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorResponse:
    """
    Immutable supervisor workflow response.

    Returned by every :class:`SupervisorEngine` operation.

    Fields
    ------
    response_id :      Unique identifier.
    request_id :       Originating request identifier.
    supervision_id :   Supervision run identifier.
    subsystem_id :     Target subsystem identifier.
    workflow_type :    Workflow that was executed.
    status :           Outcome status (SUCCESS / FAILURE / PARTIAL).
    snapshot :         Published supervisor snapshot (None on failure).
    error_message :    Non-empty when status is FAILURE.
    elapsed_s :        Wall-clock processing duration in seconds.
    metadata :         Supplementary response metadata.
    created_at :       Wall-clock response creation time.
    framework_version: Framework version string.
    """
    response_id:       str
    request_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     SupervisorWorkflowType
    status:            ResponseStatus
    snapshot:          Optional[SupervisorEngineSnapshot] = None
    error_message:     str                               = ""
    elapsed_s:         float                             = 0.0
    metadata:          Dict[str, Any]                   = field(default_factory=dict)
    created_at:        float                             = field(default_factory=time.time)
    framework_version: str                              = VERSION

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == ResponseStatus.FAILURE

    @property
    def is_partial(self) -> bool:
        return self.status == ResponseStatus.PARTIAL

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":     self.response_id,
            "request_id":      self.request_id,
            "supervision_id":  self.supervision_id,
            "subsystem_id":    self.subsystem_id,
            "workflow_type":   self.workflow_type.value,
            "status":          self.status.value,
            "has_snapshot":    self.has_snapshot,
            "error_message":   self.error_message,
            "elapsed_s":       self.elapsed_s,
            "created_at":      self.created_at,
            "framework_version": self.framework_version,
        }
