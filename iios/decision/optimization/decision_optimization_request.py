"""
decision_optimization_request.py — iios.decision.optimization
==============================================================
Input request to the Decision Optimization Framework.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .constants import DEFAULT_STRATEGY_ID, VERSION, OptimizationStrategyType
from .decision_candidate import DecisionCandidate
from .decision_optimization_context import DecisionOptimizationContext


@dataclass(frozen=True)
class DecisionOptimizationRequest:
    """
    Describes what to optimize and how.

    Parameters
    ----------
    request_id :      Unique request identifier.
    context :         Full optimization context.
    candidates :      Policy-approved candidate decisions to optimize over.
    strategy_id :     ID of the strategy to use (default = weighted score).
    objective_ids :   IDs of objectives to apply (``None`` = all registered).
    constraint_ids :  IDs of constraints to check (``None`` = all registered).
    metadata :        Arbitrary metadata.
    created_at :      Creation timestamp.
    framework_version : Framework version.
    """

    request_id:        str
    context:           DecisionOptimizationContext
    candidates:        List[DecisionCandidate]
    strategy_id:       str                     = DEFAULT_STRATEGY_ID
    objective_ids:     Optional[List[str]]     = field(default=None)
    constraint_ids:    Optional[List[str]]     = field(default=None)
    metadata:          dict                    = field(default_factory=dict)
    created_at:        datetime                = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str                     = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        context:        DecisionOptimizationContext,
        candidates:     List[DecisionCandidate],
        *,
        request_id:     Optional[str]          = None,
        strategy_id:    str                    = DEFAULT_STRATEGY_ID,
        objective_ids:  Optional[List[str]]    = None,
        constraint_ids: Optional[List[str]]    = None,
        metadata:       Optional[dict]          = None,
    ) -> "DecisionOptimizationRequest":
        return cls(
            request_id     = request_id or str(uuid.uuid4()),
            context        = context,
            candidates     = list(candidates),
            strategy_id    = strategy_id,
            objective_ids  = objective_ids,
            constraint_ids = constraint_ids,
            metadata       = metadata or {},
        )
