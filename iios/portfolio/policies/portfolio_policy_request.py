"""
portfolio_policy_request.py — iios.portfolio.policies
======================================================
Immutable request object submitted to the Portfolio Policy Engine.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    POLICY_SYSTEM_ID,
    VERSION,
    PolicyPriority,
    PolicyType,
)
from .portfolio_policy_context import PolicyContext


@dataclass(frozen=True)
class PortfolioPolicyRequest:
    """
    Immutable request submitted to the Portfolio Policy Engine for evaluation.

    Carries the portfolio identifier, the set of policy types to evaluate,
    the evaluation context, and all input data required by policy conditions.

    Fields
    ------
    request_id :       Unique identifier for this request.
    portfolio_id :     Portfolio being evaluated.
    policy_types :     Specific policy types to evaluate (empty = all active).
    priority :         Scheduling priority.
    context :          Evaluation context.
    inputs :           Input data dict (decision_snapshot, position_snapshot, …).
    requested_at :     Wall-clock creation time.
    metadata :         Supplementary free-form data.
    framework_version: Framework version string.
    """
    request_id:        str
    portfolio_id:      str
    policy_types:      tuple           # Tuple[PolicyType, ...]
    priority:          PolicyPriority
    context:           PolicyContext
    inputs:            Dict[str, Any]
    requested_at:      float
    metadata:          Dict[str, Any]
    framework_version: str

    @classmethod
    def create(
        cls,
        portfolio_id:   str,
        policy_types:   Optional[List[PolicyType]] = None,
        *,
        priority:       PolicyPriority = PolicyPriority.MEDIUM,
        inputs:         Optional[Dict[str, Any]] = None,
        metadata:       Optional[Dict[str, Any]] = None,
        context:        Optional[PolicyContext] = None,
    ) -> "PortfolioPolicyRequest":
        """Create a new PortfolioPolicyRequest with a generated request_id."""
        pts = tuple(policy_types or [])
        ctx = context or PolicyContext.create(
            portfolio_id,
            policy_types = list(pts),
            priority     = priority,
        )
        return cls(
            request_id        = str(uuid.uuid4()),
            portfolio_id      = portfolio_id,
            policy_types      = pts,
            priority          = priority,
            context           = ctx,
            inputs            = dict(inputs or {}),
            requested_at      = time.time(),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    def with_inputs(self, additional_inputs: Dict[str, Any]) -> "PortfolioPolicyRequest":
        """Return a new request with merged inputs (non-mutating)."""
        merged = {**self.inputs, **additional_inputs}
        return PortfolioPolicyRequest(
            request_id        = self.request_id,
            portfolio_id      = self.portfolio_id,
            policy_types      = self.policy_types,
            priority          = self.priority,
            context           = self.context,
            inputs            = merged,
            requested_at      = self.requested_at,
            metadata          = dict(self.metadata),
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging or persistence."""
        return {
            "request_id":       self.request_id,
            "portfolio_id":     self.portfolio_id,
            "policy_types":     [pt.value for pt in self.policy_types],
            "priority":         self.priority.name,
            "input_keys":       sorted(self.inputs.keys()),
            "requested_at":     self.requested_at,
            "metadata":         dict(self.metadata),
            "framework_version": self.framework_version,
        }
