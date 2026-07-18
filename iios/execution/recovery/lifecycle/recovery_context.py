"""iios/execution/recovery/lifecycle/recovery_context.py
==================================================
RecoveryContext — immutable value object capturing all inputs required
to create a recovery session.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import RecoveryTrigger, VERSION


@dataclass(frozen=True)
class RecoveryContext:
    """
    Immutable input bundle for a recovery session.

    Fields
    ------
    context_id:           Unique ID for this context object.
    execution_session_id: ID of the failed execution session.
    workflow_id:          Optional originating workflow.
    failure_id:           ID of the failure record that triggered recovery.
    recovery_plan_id:     Optional pre-determined recovery plan.
    subsystem_id:         Subsystem where the failure occurred.
    recovery_trigger:     What initiated this recovery.
    recovery_reason:      Human-readable reason for recovery.
    recovery_version:     Schema version for this context.
    tags:                 Arbitrary classification tags.
    metadata:             Arbitrary key-value context data.
    created_at:           Wall-time of context creation.
    framework_version:    Platform version.
    """

    context_id:           str
    execution_session_id: str
    subsystem_id:         str
    recovery_trigger:     RecoveryTrigger
    recovery_reason:      str

    workflow_id:          Optional[str]       = None
    failure_id:           Optional[str]       = None
    recovery_plan_id:     Optional[str]       = None
    recovery_version:     int                 = 1
    tags:                 Tuple[str, ...]     = ()
    metadata:             Dict[str, Any]      = field(default_factory=dict, compare=False)
    created_at:           float               = field(default_factory=time.time, compare=False)
    framework_version:    str                 = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_workflow(self) -> bool:
        return self.workflow_id is not None

    @property
    def has_failure_id(self) -> bool:
        return self.failure_id is not None

    @property
    def has_recovery_plan(self) -> bool:
        return self.recovery_plan_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":           self.context_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "recovery_trigger":     self.recovery_trigger.value,
            "recovery_reason":      self.recovery_reason,
            "workflow_id":          self.workflow_id,
            "failure_id":           self.failure_id,
            "recovery_plan_id":     self.recovery_plan_id,
            "recovery_version":     self.recovery_version,
            "tags":                 list(self.tags),
            "metadata":             dict(self.metadata),
            "created_at":           self.created_at,
            "framework_version":    self.framework_version,
        }


def make_recovery_context(
    execution_session_id: str,
    subsystem_id:         str,
    recovery_trigger:     RecoveryTrigger,
    recovery_reason:      str,
    *,
    workflow_id:       Optional[str]            = None,
    failure_id:        Optional[str]            = None,
    recovery_plan_id:  Optional[str]            = None,
    recovery_version:  int                      = 1,
    tags:              Tuple[str, ...]          = (),
    metadata:          Optional[Dict[str, Any]] = None,
    context_id:        Optional[str]            = None,
) -> RecoveryContext:
    """Factory function for RecoveryContext."""
    return RecoveryContext(
        context_id           = context_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        recovery_trigger     = recovery_trigger,
        recovery_reason      = recovery_reason,
        workflow_id          = workflow_id,
        failure_id           = failure_id,
        recovery_plan_id     = recovery_plan_id,
        recovery_version     = recovery_version,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
