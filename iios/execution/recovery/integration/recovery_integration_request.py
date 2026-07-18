"""
iios/execution/recovery/integration/recovery_integration_request.py
===================================================================
IntegrationRequest — the client-facing input to the integration engine.

External subsystems submit IntegrationRequests; the integration engine
converts them into M2 RecoveryRequests and FailureContexts internally.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION


@dataclass(frozen=True)
class IntegrationRequest:
    """
    Immutable request submitted by an external subsystem to trigger recovery.

    Intentionally decoupled from M2 internals — callers do not need to
    know about RecoveryRequest, FailureContext, or recovery pipeline details.
    """

    request_id:           str
    execution_session_id: str
    subsystem_id:         str
    failure_type:         str
    failure_reason:       str
    recovery_reason:      str
    requested_at:         float
    failure_severity:     str           = "MEDIUM"
    workflow_id:          str           = ""
    gateway_id:           str           = ""
    broker_id:            str           = ""
    portfolio_id:         str           = ""
    strategy_id:          str           = ""
    request_priority:     str           = "NORMAL"
    request_type:         str           = "AUTOMATIC"
    requester:            str           = ACTOR_SYSTEM
    tags:                 Tuple[str, ...] = ()
    metadata:             Dict[str, Any]  = field(default_factory=dict)
    framework_version:    str           = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failure_type":         self.failure_type,
            "failure_reason":       self.failure_reason,
            "recovery_reason":      self.recovery_reason,
            "requested_at":         self.requested_at,
            "failure_severity":     self.failure_severity,
            "workflow_id":          self.workflow_id,
            "request_priority":     self.request_priority,
            "request_type":         self.request_type,
            "requester":            self.requester,
            "tags":                 list(self.tags),
            "framework_version":    self.framework_version,
        }


def make_integration_request(
    execution_session_id: str,
    subsystem_id:         str,
    failure_type:         str,
    failure_reason:       str,
    recovery_reason:      str,
    *,
    failure_severity: str  = "MEDIUM",
    workflow_id:      str  = "",
    gateway_id:       str  = "",
    broker_id:        str  = "",
    portfolio_id:     str  = "",
    strategy_id:      str  = "",
    request_priority: str  = "NORMAL",
    request_type:     str  = "AUTOMATIC",
    requester:        str  = ACTOR_SYSTEM,
    tags:             Optional[Tuple[str, ...]] = None,
    metadata:         Optional[Dict[str, Any]]  = None,
    request_id:       Optional[str]             = None,
    requested_at:     Optional[float]           = None,
) -> IntegrationRequest:
    return IntegrationRequest(
        request_id           = request_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failure_type         = failure_type,
        failure_reason       = failure_reason,
        recovery_reason      = recovery_reason,
        requested_at         = requested_at if requested_at is not None else time.time(),
        failure_severity     = failure_severity,
        workflow_id          = workflow_id,
        gateway_id           = gateway_id,
        broker_id            = broker_id,
        portfolio_id         = portfolio_id,
        strategy_id         = strategy_id,
        request_priority     = request_priority,
        request_type         = request_type,
        requester            = requester,
        tags                 = tags or (),
        metadata             = dict(metadata) if metadata else {},
    )
