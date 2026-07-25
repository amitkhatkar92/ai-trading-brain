"""
workflow_policy_request.py — iios.workflow.policies
----------------------------------------------------
WorkflowPolicyRequest — the input to the Governance Policy Framework.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import PolicyDomain, PolicyType
from .workflow_policy_context import WorkflowPolicyContext


@dataclass(frozen=True)
class WorkflowPolicyRequest:
    """
    Immutable input to the governance policy evaluation framework.

    Wraps the workflow context and optionally specifies which policy
    types or domains should be evaluated.  When `policy_types` and
    `policy_domains` are empty, all registered policies are evaluated.
    """
    request_id:      str
    workflow_id:     str
    context:         WorkflowPolicyContext
    policy_types:    tuple                      # Tuple[PolicyType, ...]  — filter
    policy_domains:  tuple                      # Tuple[PolicyDomain, ...] — filter
    correlation_id:  str
    trace_id:        str
    metadata:        Dict[str, Any]
    created_at:      str

    @classmethod
    def create(
        cls,
        workflow_id: str,
        context:     WorkflowPolicyContext,
        *,
        policy_types:   Optional[List[PolicyType]]   = None,
        policy_domains: Optional[List[PolicyDomain]] = None,
        correlation_id: str                          = "",
        trace_id:       str                          = "",
        metadata:       Optional[Dict[str, Any]]     = None,
        request_id:     Optional[str]                = None,
    ) -> "WorkflowPolicyRequest":
        return cls(
            request_id     = request_id or f"preq-{uuid.uuid4().hex[:12]}",
            workflow_id    = workflow_id,
            context        = context,
            policy_types   = tuple(policy_types or []),
            policy_domains = tuple(policy_domains or []),
            correlation_id = correlation_id or context.correlation_id,
            trace_id       = trace_id or context.trace_id,
            metadata       = dict(metadata or {}),
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    @property
    def has_type_filter(self) -> bool:
        return len(self.policy_types) > 0

    @property
    def has_domain_filter(self) -> bool:
        return len(self.policy_domains) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "workflow_id":    self.workflow_id,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "policy_types":   [t.value for t in self.policy_types],
            "policy_domains": [d.value for d in self.policy_domains],
            "created_at":     self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowPolicyRequest":
        ctx_data = data.get("context", {})
        context  = WorkflowPolicyContext.create(
            workflow_id = ctx_data.get("workflow_id", ""),
            workflow_type = ctx_data.get("workflow_type", "sequential"),
        )
        return cls.create(
            workflow_id    = data.get("workflow_id", ""),
            context        = context,
            correlation_id = data.get("correlation_id", ""),
            trace_id       = data.get("trace_id", ""),
            request_id     = data.get("request_id"),
        )
