"""
supervisor_context.py — iios.supervisor.lifecycle
--------------------------------------------------
Immutable operational context attached to a supervisor session.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    SupervisorPriority,
    SupervisorScope,
    SupervisorType,
)


@dataclass(frozen=True)
class SupervisorContext:
    """
    Immutable operational context that parameterises a supervisor session.

    Captured at session creation; never mutated afterwards.

    Fields
    ------
    context_id :          Unique identifier.
    supervisor_id :       Supervised entity identifier.
    workflow_id :         Optional workflow routing context.
    supervisor_type :     Classification of the supervisor.
    supervisor_scope :    Institutional scope of the supervision.
    supervisor_priority : Priority level of the session.
    tags :                Free-form key/value tags for filtering.
    framework_version :   Framework version string.
    """
    context_id:          str
    supervisor_id:       str
    workflow_id:         str               = ""
    supervisor_type:     SupervisorType    = SupervisorType.CUSTOM
    supervisor_scope:    SupervisorScope   = SupervisorScope.SYSTEM
    supervisor_priority: SupervisorPriority = SupervisorPriority.MEDIUM
    tags:                Dict[str, str]   = field(default_factory=dict)
    framework_version:   str              = VERSION

    @classmethod
    def create(
        cls,
        supervisor_id: str,
        *,
        context_id:          Optional[str]            = None,
        workflow_id:         str                       = "",
        supervisor_type:     SupervisorType            = SupervisorType.CUSTOM,
        supervisor_scope:    SupervisorScope           = SupervisorScope.SYSTEM,
        supervisor_priority: SupervisorPriority        = SupervisorPriority.MEDIUM,
        tags:                Optional[Dict[str, str]]  = None,
    ) -> "SupervisorContext":
        return cls(
            context_id          = context_id or str(uuid.uuid4()),
            supervisor_id       = supervisor_id,
            workflow_id         = workflow_id,
            supervisor_type     = supervisor_type,
            supervisor_scope    = supervisor_scope,
            supervisor_priority = supervisor_priority,
            tags                = dict(tags or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "supervisor_id":       self.supervisor_id,
            "workflow_id":         self.workflow_id,
            "supervisor_type":     self.supervisor_type.value,
            "supervisor_scope":    self.supervisor_scope.value,
            "supervisor_priority": self.supervisor_priority.value,
            "tags":                dict(self.tags),
            "framework_version":   self.framework_version,
        }
