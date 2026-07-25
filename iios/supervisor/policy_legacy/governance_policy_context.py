"""
governance_policy_context.py — iios.supervisor.policy
-------------------------------------------------------
Immutable evaluation context for a governance policy request.

Carries all enterprise supervision state required for policy evaluation.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION, GovernancePolicyType


@dataclass(frozen=True)
class GovernancePolicyContext:
    """
    Immutable context for a governance policy evaluation.

    Fields
    ------
    context_id :           Unique identifier.
    supervision_id :       Supervision run correlation identifier.
    subsystem_id :         Target subsystem being evaluated.
    workflow_type :        Supervisor workflow type string.
    session_id :           Lifecycle session identifier.
    platform_health :      Aggregated subsystem health data.
    subsystems_available : List of available subsystem IDs.
    platform_metrics :     Enterprise performance metrics.
    inputs :               Full collected enterprise snapshot data.
    evaluated_at :         Context creation wall-clock time.
    framework_version :    Framework version string.
    """
    context_id:           str
    supervision_id:       str
    subsystem_id:         str            = ""
    workflow_type:        str            = ""
    session_id:           str            = ""
    platform_health:      Dict[str, Any] = field(default_factory=dict)
    subsystems_available: List[str]      = field(default_factory=list)
    platform_metrics:     Dict[str, Any] = field(default_factory=dict)
    inputs:               Dict[str, Any] = field(default_factory=dict)
    evaluated_at:         float          = field(default_factory=time.time)
    framework_version:    str            = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        *,
        context_id:           Optional[str]           = None,
        subsystem_id:         str                     = "",
        workflow_type:        str                     = "",
        session_id:           str                     = "",
        platform_health:      Optional[Dict[str, Any]] = None,
        subsystems_available: Optional[List[str]]     = None,
        platform_metrics:     Optional[Dict[str, Any]] = None,
        inputs:               Optional[Dict[str, Any]] = None,
    ) -> "GovernancePolicyContext":
        return cls(
            context_id           = context_id or str(uuid.uuid4()),
            supervision_id       = supervision_id,
            subsystem_id         = subsystem_id,
            workflow_type        = workflow_type,
            session_id           = session_id,
            platform_health      = dict(platform_health or {}),
            subsystems_available = list(subsystems_available or []),
            platform_metrics     = dict(platform_metrics or {}),
            inputs               = dict(inputs or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":           self.context_id,
            "supervision_id":       self.supervision_id,
            "subsystem_id":         self.subsystem_id,
            "workflow_type":        self.workflow_type,
            "session_id":           self.session_id,
            "platform_health":      dict(self.platform_health),
            "subsystems_available": list(self.subsystems_available),
            "platform_metrics":     dict(self.platform_metrics),
            "evaluated_at":         self.evaluated_at,
            "framework_version":    self.framework_version,
        }
