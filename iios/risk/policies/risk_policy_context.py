"""
risk_policy_context.py — iios.risk.policies
=============================================
Immutable engine-level context for a policy evaluation run.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION, PolicyPriority, PolicyType


@dataclass(frozen=True)
class RiskPolicyContext:
    """
    Immutable operational context attached to a policy evaluation request.

    Carries the governance parameters that shape how the policy engine
    processes a single evaluation.

    Fields
    ------
    context_id :        Unique identifier.
    evaluation_id :     Correlation identifier linking to the originating risk workflow.
    portfolio_id :      Target portfolio identifier.
    risk_id :           Originating risk assessment identifier.
    policy_types :      Policy domains to include in evaluation (empty = all).
    priority_floor :    Minimum priority level to consider (inclusive).
    source :            Requesting component or actor identifier.
    correlation_id :    Upstream correlation identifier.
    metadata :          Supplementary context metadata.
    framework_version : Framework version string.
    """
    context_id:        str
    evaluation_id:     str
    portfolio_id:      str
    risk_id:           str
    policy_types:      Tuple[PolicyType, ...]  = field(default_factory=tuple)
    priority_floor:    PolicyPriority          = PolicyPriority.INFORMATIONAL
    source:            str                     = ""
    correlation_id:    str                     = ""
    metadata:          Dict[str, Any]          = field(default_factory=dict)
    framework_version: str                     = VERSION

    @classmethod
    def create(
        cls,
        evaluation_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        context_id:    Optional[str]              = None,
        policy_types:  Optional[Tuple[PolicyType, ...]] = None,
        priority_floor: PolicyPriority             = PolicyPriority.INFORMATIONAL,
        source:         str                        = "",
        correlation_id: str                        = "",
        metadata:       Optional[Dict[str, Any]]   = None,
    ) -> "RiskPolicyContext":
        return cls(
            context_id     = context_id or str(uuid.uuid4()),
            evaluation_id  = evaluation_id,
            portfolio_id   = portfolio_id,
            risk_id        = risk_id,
            policy_types   = tuple(policy_types or []),
            priority_floor = priority_floor,
            source         = source,
            correlation_id = correlation_id,
            metadata       = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "evaluation_id":     self.evaluation_id,
            "portfolio_id":      self.portfolio_id,
            "risk_id":           self.risk_id,
            "policy_types":      [pt.value for pt in self.policy_types],
            "priority_floor":    self.priority_floor.value,
            "source":            self.source,
            "correlation_id":    self.correlation_id,
            "framework_version": self.framework_version,
        }
