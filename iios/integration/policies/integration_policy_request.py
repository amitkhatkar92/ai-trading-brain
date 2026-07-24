"""
integration_policy_request.py — iios.integration.policies
-----------------------------------------------------------
IntegrationPolicyRequest — governance evaluation request submitted
to the policy engine.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import PolicyDomain, PolicyType
from .integration_policy_context import IntegrationPolicyContext


@dataclass(frozen=True)
class IntegrationPolicyRequest:
    """
    Immutable request submitted to the policy engine for governance evaluation.

    Carries the evaluation context and optional domain/type filters
    that restrict which policies are evaluated.
    """

    request_id:        str
    policy_context:    IntegrationPolicyContext
    requested_domains: Tuple[PolicyDomain, ...]   # empty = all domains
    requested_types:   Tuple[PolicyType, ...]     # empty = all types
    correlation_id:    str
    trace_id:          str
    metadata:          Dict[str, Any]
    created_at:        str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        policy_context:    IntegrationPolicyContext,
        requested_domains: Optional[List[PolicyDomain]] = None,
        requested_types:   Optional[List[PolicyType]]   = None,
        *,
        correlation_id:    str                       = "",
        trace_id:          str                       = "",
        metadata:          Optional[Dict[str, Any]]  = None,
        request_id:        Optional[str]             = None,
    ) -> "IntegrationPolicyRequest":
        return cls(
            request_id        = request_id or f"preq-{uuid.uuid4().hex[:12]}",
            policy_context    = policy_context,
            requested_domains = tuple(requested_domains or list(PolicyDomain)),
            requested_types   = tuple(requested_types   or []),
            correlation_id    = correlation_id or f"corr-{uuid.uuid4().hex[:8]}",
            trace_id          = trace_id       or f"trc-{uuid.uuid4().hex[:8]}",
            metadata          = dict(metadata  or {}),
            created_at        = datetime.now(timezone.utc).isoformat(),
        )

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "policy_context":    self.policy_context.to_dict(),
            "requested_domains": [d.value for d in self.requested_domains],
            "requested_types":   [t.value for t in self.requested_types],
            "correlation_id":    self.correlation_id,
            "trace_id":          self.trace_id,
            "metadata":          self.metadata,
            "created_at":        self.created_at,
        }
