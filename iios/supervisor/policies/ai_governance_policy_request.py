"""
ai_governance_policy_request.py — iios.supervisor.policies
------------------------------------------------------------
Immutable governance policy evaluation request value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, AIGovernancePolicyType
from .ai_governance_policy_context import AIGovernancePolicyContext


@dataclass(frozen=True)
class AIGovernancePolicyRequest:
    """
    Immutable governance policy evaluation request.

    Fields
    ------
    request_id :        Unique identifier.
    supervision_id :    Parent supervision run identifier.
    subsystem_id :      Requesting subsystem identifier.
    workflow_type :     The autonomous workflow being governed.
    context :           Platform state snapshot.
    policy_types :      Policy domains to evaluate (empty = all enabled).
    inputs :            Flat evaluation inputs for condition matching.
    requested_at :      Wall-clock request creation time.
    metadata :          Arbitrary extension metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    supervision_id:    str
    subsystem_id:      str
    workflow_type:     str
    context:           AIGovernancePolicyContext
    policy_types:      Tuple[AIGovernancePolicyType, ...]
    inputs:            Dict[str, Any]
    requested_at:      float          = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  str,
        *,
        request_id:  Optional[str]                         = None,
        context:     Optional[AIGovernancePolicyContext]    = None,
        policy_types: Optional[List[AIGovernancePolicyType]] = None,
        inputs:      Optional[Dict[str, Any]]               = None,
        metadata:    Optional[Dict[str, Any]]               = None,
    ) -> "AIGovernancePolicyRequest":
        flat_inputs = inputs or {}
        ctx = context or AIGovernancePolicyContext.create(
            supervision_id = supervision_id,
            inputs         = flat_inputs,
        )
        return cls(
            request_id     = request_id or str(uuid.uuid4()),
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            context        = ctx,
            policy_types   = tuple(policy_types or []),
            inputs         = flat_inputs,
            metadata       = metadata or {},
        )

    def with_inputs(self, extra: Dict[str, Any]) -> "AIGovernancePolicyRequest":
        """Return a new request with *extra* merged into the existing inputs."""
        merged = {**self.inputs, **extra}
        return AIGovernancePolicyRequest(
            request_id     = self.request_id,
            supervision_id = self.supervision_id,
            subsystem_id   = self.subsystem_id,
            workflow_type  = self.workflow_type,
            context        = self.context,
            policy_types   = self.policy_types,
            inputs         = merged,
            requested_at   = self.requested_at,
            metadata       = self.metadata,
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "supervision_id":    self.supervision_id,
            "subsystem_id":      self.subsystem_id,
            "workflow_type":     self.workflow_type,
            "policy_types":      [pt.value for pt in self.policy_types],
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
