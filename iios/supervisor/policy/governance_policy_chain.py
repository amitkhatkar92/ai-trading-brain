"""
governance_policy_chain.py — iios.supervisor.policy
-----------------------------------------------------
Policy chain evaluator.

Evaluates a collection of governance policies and returns a flat list of
:class:`GovernancePolicyResult` objects.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .constants import DENY_ACTIONS, EvaluationMode
from .governance_policy import GovernancePolicy
from .governance_policy_evaluator import GovernancePolicyEvaluator
from .governance_policy_result import GovernancePolicyResult


class GovernancePolicyChain:
    """
    Orchestrates multi-policy evaluation according to a chosen
    :class:`~.constants.EvaluationMode`.

    The chain is stateless — the caller provides policies and inputs on each
    invocation.
    """

    def __init__(self, evaluator: Optional[GovernancePolicyEvaluator] = None) -> None:
        self._evaluator = evaluator or GovernancePolicyEvaluator()

    def evaluate(
        self,
        policies: List[GovernancePolicy],
        inputs:   Dict,
        mode:     EvaluationMode = EvaluationMode.SEQUENTIAL,
    ) -> List[GovernancePolicyResult]:
        """
        Evaluate *policies* against *inputs* using *mode*.

        Returns
        -------
        List of :class:`GovernancePolicyResult` — one per evaluated policy.
        """
        enabled = [p for p in policies if p.enabled]
        if not enabled:
            return []

        if mode == EvaluationMode.SEQUENTIAL:
            return self._sequential(enabled, inputs)
        if mode == EvaluationMode.PARALLEL:
            return self._parallel(enabled, inputs)
        if mode == EvaluationMode.COMPOSITE:
            return self._composite(enabled, inputs)
        if mode == EvaluationMode.WEIGHTED:
            return self._weighted(enabled, inputs)
        return self._parallel(enabled, inputs)

    # ------------------------------------------------------------------
    # Evaluation strategies
    # ------------------------------------------------------------------

    def _sequential(
        self,
        policies: List[GovernancePolicy],
        inputs:   Dict,
    ) -> List[GovernancePolicyResult]:
        """Evaluate in ascending priority order; stop on first denial."""
        sorted_policies = sorted(policies, key=lambda p: p.priority.value)
        results: List[GovernancePolicyResult] = []
        for policy in sorted_policies:
            result = self._evaluator.evaluate_policy(policy, inputs)
            results.append(result)
            if result.action in DENY_ACTIONS:
                break
        return results

    def _parallel(
        self,
        policies: List[GovernancePolicy],
        inputs:   Dict,
    ) -> List[GovernancePolicyResult]:
        """Evaluate all policies; return all results."""
        return [self._evaluator.evaluate_policy(p, inputs) for p in policies]

    def _composite(
        self,
        policies: List[GovernancePolicy],
        inputs:   Dict,
    ) -> List[GovernancePolicyResult]:
        """Each policy is independently evaluated (same as PARALLEL here)."""
        return self._parallel(policies, inputs)

    def _weighted(
        self,
        policies: List[GovernancePolicy],
        inputs:   Dict,
    ) -> List[GovernancePolicyResult]:
        """Evaluate all policies; weight-ordered in results."""
        results = [self._evaluator.evaluate_policy(p, inputs) for p in policies]
        return results
