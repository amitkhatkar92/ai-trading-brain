"""
portfolio_policy_context.py — iios.portfolio.policies
======================================================
Immutable evaluation context for a single policy evaluation run.

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


@dataclass(frozen=True)
class PolicyContext:
    """
    Immutable context attached to every portfolio policy evaluation.

    Fields
    ------
    context_id :       Unique identifier for this context instance.
    portfolio_id :     Portfolio being evaluated.
    policy_types :     Policy types to evaluate (empty = all active).
    priority :         Evaluation priority.
    source :           Identifier of the component that originated the request.
    correlation_id :   Optional trace correlation identifier.
    evaluation_id :    Optional pre-assigned evaluation run identifier.
    metadata :         Supplementary free-form data.
    framework_version: Framework version string.
    """
    context_id:        str
    portfolio_id:      str
    policy_types:      tuple  # Tuple[PolicyType, ...]
    priority:          PolicyPriority
    source:            str
    correlation_id:    str
    evaluation_id:     str
    metadata:          Dict[str, Any]
    framework_version: str

    @classmethod
    def create(
        cls,
        portfolio_id:   str,
        *,
        policy_types:   Optional[List[PolicyType]] = None,
        priority:       PolicyPriority = PolicyPriority.MEDIUM,
        source:         str = POLICY_SYSTEM_ID,
        correlation_id: str = "",
        evaluation_id:  str = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "PolicyContext":
        """Create a new PolicyContext with a generated context_id."""
        return cls(
            context_id        = str(uuid.uuid4()),
            portfolio_id      = portfolio_id,
            policy_types      = tuple(policy_types or []),
            priority          = priority,
            source            = source,
            correlation_id    = correlation_id,
            evaluation_id     = evaluation_id or str(uuid.uuid4()),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging or persistence."""
        return {
            "context_id":       self.context_id,
            "portfolio_id":     self.portfolio_id,
            "policy_types":     [pt.value for pt in self.policy_types],
            "priority":         self.priority.name,
            "source":           self.source,
            "correlation_id":   self.correlation_id,
            "evaluation_id":    self.evaluation_id,
            "metadata":         dict(self.metadata),
            "framework_version": self.framework_version,
        }
