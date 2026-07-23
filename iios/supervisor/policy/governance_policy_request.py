"""
governance_policy_request.py — iios.supervisor.policy
-------------------------------------------------------
Immutable governance policy evaluation request value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION, GovernancePolicyType
from .governance_policy_context import GovernancePolicyContext


@dataclass(frozen=True)
class GovernancePolicyRequest:
    """
    Immutable governance policy evaluation request.

    Fields
    ------
    request_id :          Unique request identifier.
    supervision_id :      Supervision run identifier.
    subsystem_id :        Target subsystem identifier.
    workflow_type :       Supervisor workflow type string.
    context :             Evaluation context.
    policy_types :        Which policy domains to evaluate (empty = all enabled).
    inputs :              Enterprise snapshot inputs for condition evaluation.
    requested_at :        Wall-clock request creation time.
    metadata :            Supplementary request metadata.
    framework_version :   Framework version string.
    """
    request_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     str
    context:           GovernancePolicyContext
    policy_types:      List[GovernancePolicyType] = field(default_factory=list)
    inputs:            Dict[str, Any]             = field(default_factory=dict)
    requested_at:      float                      = field(default_factory=time.time)
    metadata:          Dict[str, Any]             = field(default_factory=dict)
    framework_version: str                        = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  str = "",
        *,
        request_id:   Optional[str]                      = None,
        context:      Optional[GovernancePolicyContext]  = None,
        policy_types: Optional[List[GovernancePolicyType]] = None,
        inputs:       Optional[Dict[str, Any]]           = None,
        metadata:     Optional[Dict[str, Any]]           = None,
    ) -> "GovernancePolicyRequest":
        ctx = context or GovernancePolicyContext.create(
            supervision_id,
            subsystem_id  = subsystem_id,
            workflow_type = workflow_type,
            inputs        = inputs or {},
        )
        return cls(
            request_id     = request_id or str(uuid.uuid4()),
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            context        = ctx,
            policy_types   = list(policy_types or []),
            inputs         = dict(inputs or {}),
            metadata       = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "GovernancePolicyRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        return GovernancePolicyRequest(
            request_id     = self.request_id,
            supervision_id = self.supervision_id,
            subsystem_id   = self.subsystem_id,
            workflow_type  = self.workflow_type,
            context        = self.context,
            policy_types   = list(self.policy_types),
            inputs         = merged,
            metadata       = dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "supervision_id":    self.supervision_id,
            "subsystem_id":      self.subsystem_id,
            "workflow_type":     self.workflow_type,
            "policy_types":      [p.value for p in self.policy_types],
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
