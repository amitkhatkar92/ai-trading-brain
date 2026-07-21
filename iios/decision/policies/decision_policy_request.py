"""
decision_policy_request.py — iios.decision.policies
=====================================================
Input request to the Decision Policy Framework.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .constants import (
    VERSION,
    ConflictResolutionStrategy,
    PolicyChainMode,
    PolicyType,
)
from .decision_policy_context import PolicyEvaluationContext


@dataclass(frozen=True)
class PolicyEvaluationRequest:
    """
    Describes what should be evaluated and how.

    Parameters
    ----------
    request_id :          Unique request identifier.
    context :             Full evaluation context.
    policy_ids :          Specific policy IDs to evaluate (``None`` = all active).
    policy_types :        Filter by policy types (``None`` = all types).
    chain_mode :          How policies are chained during evaluation.
    conflict_strategy :   How conflicting results are resolved.
    metadata :            Arbitrary metadata.
    created_at :          Creation timestamp.
    framework_version :   Framework version string.
    """

    request_id:          str
    context:             PolicyEvaluationContext
    policy_ids:          Optional[List[str]]         = field(default=None)
    policy_types:        Optional[List[PolicyType]]  = field(default=None)
    chain_mode:          PolicyChainMode              = PolicyChainMode.SEQUENTIAL
    conflict_strategy:   ConflictResolutionStrategy   = ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES
    metadata:            dict                         = field(default_factory=dict)
    created_at:          datetime                     = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version:   str                          = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        context:            PolicyEvaluationContext,
        *,
        request_id:         Optional[str]                   = None,
        policy_ids:         Optional[List[str]]             = None,
        policy_types:       Optional[List[PolicyType]]      = None,
        chain_mode:         PolicyChainMode                  = PolicyChainMode.SEQUENTIAL,
        conflict_strategy:  ConflictResolutionStrategy       = ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
        metadata:           Optional[dict]                   = None,
    ) -> "PolicyEvaluationRequest":
        """Create a new :class:`PolicyEvaluationRequest`."""
        return cls(
            request_id        = request_id or str(uuid.uuid4()),
            context           = context,
            policy_ids        = policy_ids,
            policy_types      = policy_types,
            chain_mode        = chain_mode,
            conflict_strategy = conflict_strategy,
            metadata          = metadata or {},
        )
