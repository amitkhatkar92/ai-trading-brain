"""
supervisor_request.py — iios.supervisor.engine
------------------------------------------------
Immutable supervisor workflow request value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    SupervisorWorkflowType,
    SchedulerPriority,
)
from .supervisor_context import SupervisorEngineContext


@dataclass(frozen=True)
class SupervisorRequest:
    """
    Immutable supervisor workflow request.

    Wraps all inputs required to execute a single supervisor workflow pipeline.

    Fields
    ------
    request_id :       Unique request identifier.
    supervision_id :   Supervision run identifier.
    subsystem_id :     Target subsystem identifier.
    workflow_type :    Supervisor workflow classification.
    priority :         Scheduling priority.
    context :          Engine-level operational context.
    inputs :           Collected enterprise snapshots and health data.
                       Keys include: "execution_snapshot",
                       "execution_recovery_snapshot",
                       "execution_analytics_snapshot",
                       "decision_snapshot", "portfolio_snapshot",
                       "risk_snapshot", "market_snapshot",
                       "system_health", "platform_metrics".
    requested_at :     Wall-clock request creation time.
    metadata :         Supplementary request metadata.
    framework_version: Framework version string.
    """
    request_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     SupervisorWorkflowType
    priority:          SchedulerPriority
    context:           SupervisorEngineContext
    inputs:            Dict[str, Any] = field(default_factory=dict)
    requested_at:      float          = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  SupervisorWorkflowType = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        *,
        request_id:  Optional[str]                       = None,
        priority:    SchedulerPriority                    = SchedulerPriority.NORMAL,
        context:     Optional[SupervisorEngineContext]    = None,
        workflow_id: str                                 = "",
        inputs:      Optional[Dict[str, Any]]             = None,
        metadata:    Optional[Dict[str, Any]]             = None,
    ) -> "SupervisorRequest":
        rid = request_id or str(uuid.uuid4())
        ctx = context or SupervisorEngineContext.create(
            supervision_id,
            subsystem_id,
            workflow_type,
            priority    = priority,
            workflow_id = workflow_id,
        )
        return cls(
            request_id     = rid,
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            priority       = priority,
            context        = ctx,
            inputs         = dict(inputs or {}),
            metadata       = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "SupervisorRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        return SupervisorRequest(
            request_id     = self.request_id,
            supervision_id = self.supervision_id,
            subsystem_id   = self.subsystem_id,
            workflow_type  = self.workflow_type,
            priority       = self.priority,
            context        = self.context,
            inputs         = merged,
            requested_at   = self.requested_at,
            metadata       = dict(self.metadata),
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":      self.request_id,
            "supervision_id":  self.supervision_id,
            "subsystem_id":    self.subsystem_id,
            "workflow_type":   self.workflow_type.value,
            "priority":        self.priority.value,
            "input_keys":      list(self.inputs.keys()),
            "requested_at":    self.requested_at,
            "framework_version": self.framework_version,
        }
