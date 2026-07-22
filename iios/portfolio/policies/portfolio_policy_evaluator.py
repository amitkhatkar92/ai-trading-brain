"""
portfolio_policy_evaluator.py — iios.portfolio.policies
========================================================
Core policy evaluation engine.

PortfolioPolicyEvaluator accepts a PortfolioPolicyRequest and a list of
PortfolioPolicy objects, evaluates every applicable policy, resolves
conflicts, and returns a PortfolioPolicyResult.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    VERSION,
    PolicyAction,
    PolicyConflictResolution,
    PolicyType,
)
from .portfolio_policy import PolicyOutcome, PortfolioPolicy
from .portfolio_policy_priority import PolicyPriorityResolver
from .portfolio_policy_request import PortfolioPolicyRequest
from .portfolio_policy_result import (
    PortfolioPolicyResult,
    PolicyEvaluationSummary,
    _build_summary,
)


class PortfolioPolicyEvaluator:
    """
    Core evaluation engine for the Portfolio Policy Framework.

    Filters applicable policies from a supplied list, evaluates each
    one against the request inputs, resolves conflicts between outcomes,
    and returns a PortfolioPolicyResult.

    Parameters
    ----------
    resolver : PolicyPriorityResolver used for conflict resolution.
               Defaults to DENY_OVERRIDES strategy if not supplied.
    """

    def __init__(
        self,
        resolver: Optional[PolicyPriorityResolver] = None,
    ) -> None:
        self._resolver = resolver or PolicyPriorityResolver(
            PolicyConflictResolution.DENY_OVERRIDES
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def resolver(self) -> PolicyPriorityResolver:
        return self._resolver

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def evaluate(
        self,
        request:  PortfolioPolicyRequest,
        policies: List[PortfolioPolicy],
    ) -> PortfolioPolicyResult:
        """
        Evaluate all applicable policies and return a full result.

        Steps
        -----
        1. Filter to active, applicable policies.
        2. Sort by priority (CRITICAL first).
        3. Evaluate each policy.
        4. Resolve conflicts via the priority resolver.
        5. Build and return the result.

        If no policies are applicable the result is APPROVE (pass-through).

        Parameters
        ----------
        request :  The policy evaluation request carrying inputs.
        policies : Complete list of candidate policies.

        Returns
        -------
        PortfolioPolicyResult
        """
        start          = time.monotonic()
        evaluation_id  = str(uuid.uuid4())

        # 1 — Filter
        applicable = self._filter_applicable(request, policies)

        # 2 — Sort by priority
        applicable.sort(key=lambda p: int(p.priority))

        # 3 — Evaluate
        outcomes: List[PolicyOutcome] = []
        for policy in applicable:
            try:
                outcome = policy.evaluate(request.inputs)
                outcomes.append(outcome)
            except Exception:
                # A policy that raises unexpectedly is treated as BLOCK
                # so that the evaluation is never silently permissive.
                from .portfolio_policy import PolicyOutcome as _PO
                outcomes.append(_PO(
                    policy_id         = policy.policy_id,
                    policy_name       = policy.name,
                    policy_type       = policy.policy_type,
                    action            = PolicyAction.BLOCK,
                    priority          = policy.priority,
                    rules_evaluated   = 0,
                    conditions_passed = 0,
                    conditions_failed = 0,
                    reason            = "policy raised unexpected exception",
                    rule_results      = (),
                    elapsed_s         = 0.0,
                    evaluated_at      = time.time(),
                ))

        # 4 — Resolve conflicts
        final_action = self._resolver.resolve(outcomes)

        # 5 — Build result
        elapsed = time.monotonic() - start
        summary = _build_summary(
            evaluation_id, request.portfolio_id, final_action, outcomes, elapsed
        )
        return PortfolioPolicyResult(
            result_id         = str(uuid.uuid4()),
            evaluation_id     = evaluation_id,
            portfolio_id      = request.portfolio_id,
            final_action      = final_action,
            outcomes          = tuple(outcomes),
            summary           = summary,
            elapsed_s         = elapsed,
            evaluated_at      = time.time(),
            framework_version = VERSION,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filter_applicable(
        self,
        request:  PortfolioPolicyRequest,
        policies: List[PortfolioPolicy],
    ) -> List[PortfolioPolicy]:
        """
        Return active policies applicable to the request.

        If request.policy_types is non-empty, only policies whose type
        appears in that tuple are included.  Otherwise all active
        policies are returned.
        """
        active = [p for p in policies if p.is_active]
        if request.policy_types:
            requested_types = set(request.policy_types)
            return [p for p in active if p.policy_type in requested_types]
        return active
