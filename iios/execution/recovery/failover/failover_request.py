"""
iios/execution/recovery/failover/failover_request.py
====================================================
FailoverRequest — input to the Failover Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTOR_SYSTEM,
    VERSION,
    FailoverAction,
    FailoverType,
)
from .failover_context import FailoverContext


@dataclass(frozen=True)
class FailoverRequest:
    """
    Immutable request submitted to the Failover Engine.

    Contains the FailoverContext plus request-level metadata.
    Always originates from an approved M3 RecoveryPolicyDecision.
    """

    request_id:           str
    failover_session_id:  str
    execution_session_id: str
    subsystem_id:         str
    failover_type:        FailoverType
    primary_action:       FailoverAction
    source_decision_id:   str
    context:              FailoverContext
    requester:            str             = ACTOR_SYSTEM
    requested_at:         float           = field(default_factory=time.time)
    tags:                 Tuple[str, ...] = ()
    metadata:             Dict[str, Any]  = field(default_factory=dict)
    version:              str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "failover_session_id":  self.failover_session_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failover_type":        self.failover_type.value,
            "primary_action":       self.primary_action.value,
            "source_decision_id":   self.source_decision_id,
            "requester":            self.requester,
            "requested_at":         self.requested_at,
        }


def make_failover_request(
    failover_session_id: str,
    execution_session_id: str,
    subsystem_id: str,
    failover_type: FailoverType,
    primary_action: FailoverAction,
    source_decision_id: str,
    context: FailoverContext,
    *,
    requester: str = ACTOR_SYSTEM,
    tags: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> FailoverRequest:
    """Factory for FailoverRequest."""
    return FailoverRequest(
        request_id           = request_id or str(uuid.uuid4()),
        failover_session_id  = failover_session_id,
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failover_type        = failover_type,
        primary_action       = primary_action,
        source_decision_id   = source_decision_id,
        context              = context,
        requester            = requester,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
