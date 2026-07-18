"""
iios/execution/recovery/policies/recovery_request.py
====================================================
PolicyEvaluationRequest — input to the Recovery Policy Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTOR_SYSTEM,
    VERSION,
    FailureCategory,
    FailureSeverity,
)
from .recovery_context import PolicyEvaluationContext


@dataclass(frozen=True)
class PolicyEvaluationRequest:
    """
    Immutable request submitted to the Recovery Policy Engine for evaluation.

    Contains a pre-built PolicyEvaluationContext plus request metadata.
    """

    request_id:           str
    execution_session_id: str
    subsystem_id:         str
    failure_category:     FailureCategory
    failure_severity:     FailureSeverity
    context:              PolicyEvaluationContext
    requester:            str              = ACTOR_SYSTEM
    evaluation_mode:      str              = "standard"   # standard | fast | thorough
    requested_at:         float            = field(default_factory=time.time)
    tags:                 Tuple[str, ...]  = ()
    metadata:             Dict[str, Any]   = field(default_factory=dict)
    framework_version:    str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failure_category":     self.failure_category.value,
            "failure_severity":     self.failure_severity.value,
            "requester":            self.requester,
            "evaluation_mode":      self.evaluation_mode,
            "requested_at":         self.requested_at,
            "tags":                 list(self.tags),
            "framework_version":    self.framework_version,
        }


def make_policy_evaluation_request(
    execution_session_id: str,
    subsystem_id: str,
    context: PolicyEvaluationContext,
    failure_category: FailureCategory,
    failure_severity: FailureSeverity,
    *,
    requester: str = ACTOR_SYSTEM,
    evaluation_mode: str = "standard",
    tags: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> PolicyEvaluationRequest:
    """Factory for PolicyEvaluationRequest."""
    return PolicyEvaluationRequest(
        request_id           = request_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failure_category     = failure_category,
        failure_severity     = failure_severity,
        context              = context,
        requester            = requester,
        evaluation_mode      = evaluation_mode,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
