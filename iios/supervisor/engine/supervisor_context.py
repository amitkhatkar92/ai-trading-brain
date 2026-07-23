"""
supervisor_context.py — iios.supervisor.engine
------------------------------------------------
Immutable engine-level operational context for a supervisor workflow request.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    SupervisorWorkflowType,
    SchedulerPriority,
)


@dataclass(frozen=True)
class SupervisorEngineContext:
    """
    Immutable operational context attached to a supervisor workflow request.

    Captured at request creation; never mutated afterwards.

    Fields
    ------
    context_id :       Unique identifier.
    supervision_id :   Supervision run identifier.
    subsystem_id :     Target subsystem identifier.
    workflow_type :    Supervisor workflow classification.
    priority :         Scheduling priority.
    workflow_id :      Workflow routing correlation.
    metadata :         Supplementary context metadata.
    framework_version: Framework version.
    """
    context_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     SupervisorWorkflowType
    priority:          SchedulerPriority  = SchedulerPriority.NORMAL
    workflow_id:       str               = ""
    metadata:          Dict[str, Any]    = field(default_factory=dict)
    framework_version: str               = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  SupervisorWorkflowType,
        *,
        context_id:  Optional[str]          = None,
        priority:    SchedulerPriority       = SchedulerPriority.NORMAL,
        workflow_id: str                    = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "SupervisorEngineContext":
        return cls(
            context_id     = context_id or str(uuid.uuid4()),
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            priority       = priority,
            workflow_id    = workflow_id,
            metadata       = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":      self.context_id,
            "supervision_id":  self.supervision_id,
            "subsystem_id":    self.subsystem_id,
            "workflow_type":   self.workflow_type.value,
            "priority":        self.priority.value,
            "workflow_id":     self.workflow_id,
            "framework_version": self.framework_version,
        }
