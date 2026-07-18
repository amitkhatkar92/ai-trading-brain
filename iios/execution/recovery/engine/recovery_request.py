"""
iios/execution/recovery/engine/recovery_request.py
==================================================
RecoveryRequest — the primary input to the Execution Recovery Engine.

Created by external subsystems, operators, or the scheduler to initiate
a recovery workflow.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTOR_SYSTEM,
    VERSION,
    RecoveryRequestPriority,
    RecoveryRequestType,
)
from .recovery_context import FailureContext


@dataclass(frozen=True)
class RecoveryRequest:
    """
    Immutable request to initiate a recovery session.

    The engine validates this object before creating a recovery context and
    driving a pipeline.
    """

    request_id:           str
    request_type:         RecoveryRequestType
    priority:             RecoveryRequestPriority
    execution_session_id: str
    subsystem_id:         str
    failure_context:      FailureContext
    recovery_reason:      str
    requested_at:         float
    requester:            str            = ACTOR_SYSTEM
    workflow_id:          str            = ""
    tags:                 Tuple[str, ...] = ()
    metadata:             Dict[str, Any]  = field(default_factory=dict)
    framework_version:    str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "request_type":         self.request_type.value,
            "priority":             self.priority.value,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failure_context":      self.failure_context.to_dict(),
            "recovery_reason":      self.recovery_reason,
            "requested_at":         self.requested_at,
            "requester":            self.requester,
            "workflow_id":          self.workflow_id,
            "tags":                 list(self.tags),
            "framework_version":    self.framework_version,
        }


def make_recovery_request(
    execution_session_id: str,
    subsystem_id: str,
    failure_context: FailureContext,
    recovery_reason: str,
    *,
    request_type: RecoveryRequestType     = RecoveryRequestType.AUTOMATIC,
    priority:     RecoveryRequestPriority = RecoveryRequestPriority.NORMAL,
    requester:    str                     = ACTOR_SYSTEM,
    workflow_id:  str                     = "",
    tags:         Tuple[str, ...]         = (),
    metadata:     Optional[Dict[str, Any]] = None,
    request_id:   Optional[str]           = None,
) -> RecoveryRequest:
    """Factory for RecoveryRequest."""
    return RecoveryRequest(
        request_id           = request_id or str(uuid.uuid4()),
        request_type         = request_type,
        priority             = priority,
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failure_context      = failure_context,
        recovery_reason      = recovery_reason,
        requested_at         = time.time(),
        requester            = requester or ACTOR_SYSTEM,
        workflow_id          = workflow_id,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
