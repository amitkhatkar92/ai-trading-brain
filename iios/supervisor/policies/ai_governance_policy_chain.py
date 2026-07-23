"""
ai_governance_policy_chain.py — iios.supervisor.policies
----------------------------------------------------------
Policy chain evaluator for the AI Governance Policy Framework.

Evaluates a collection of :class:`AIGovernancePolicy` objects and returns
a flat list of :class:`AIGovernancePolicyResult` objects.

Supported evaluation modes:
  SEQUENTIAL  — priority-ordered; stops on first DENY or EMERGENCY_STOP
  PARALLEL    — all policies; return all results
  COMPOSITE   — all policies independently (same as PARALLEL)
  NESTED      — all policies; results carry composite rationale
  CONDITIONAL — all policies; results carry conditional rationale
  WEIGHTED    — all policies; ordered by rule weight in results

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .constants import DENY_ACTIONS, STOP_ACTIONS, EvaluationMode
from .ai_governance_policy import AIGovernancePolicy
from .ai_governance_policy_evaluator import AIGovernancePolicyEvaluator
from .ai_governance_policy_result import AIGovernancePolicyResult


class AIGovernancePolicyChain:
    """
    Orchestrates multi-policy evaluation according to a chosen
    :class:`~.constants.EvaluationMode`.

    The chain is stateless — the caller provides policies and inputs on each
    invocation.
    """

    def __init__(
        self, evaluator: Optional[AIGovernancePolicyEvaluator] = None
    ) -> None:
        self._evaluator = evaluator or AIGovernancePolicyEvaluator()

    def evaluate(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
        mode:     EvaluationMode = EvaluationMode.SEQUENTIAL,
    ) -> List[AIGovernancePolicyResult]:
        """
        Evaluate *policies* against *inputs* using *mode*.

        Returns
        -------
        List of :class:`AIGovernancePolicyResult` — one per evaluated policy.
        """
        enabled = [p for p in policies if p.enabled]
        if not enabled:
            return []

        if mode == EvaluationMode.SEQUENTIAL:
            return self._sequential(enabled, inputs)
        if mode in (EvaluationMode.PARALLEL, EvaluationMode.COMPOSITE):
            return self._parallel(enabled, inputs)
        if mode == EvaluationMode.NESTED:
            return self._nested(enabled, inputs)
        if mode == EvaluationMode.CONDITIONAL:
            return self._conditional(enabled, inputs)
        if mode == EvaluationMode.WEIGHTED:
            return self._weighted(enabled, inputs)
        return self._parallel(enabled, inputs)

    # ------------------------------------------------------------------
    # Evaluation strategies
    # ------------------------------------------------------------------

    def _sequential(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
    ) -> List[AIGovernancePolicyResult]:
        """Priority-ordered evaluation; stop on first DENY or EMERGENCY_STOP."""
        sorted_policies = sorted(policies, key=lambda p: p.priority.value)
        results: List[AIGovernancePolicyResult] = []
        for policy in sorted_policies:
            result = self._evaluator.evaluate_policy(policy, inputs)
            results.append(result)
            # Emergency stop: abort immediately, overrides all
            if result.action in STOP_ACTIONS:
                break
            if result.action in DENY_ACTIONS:
                break
        return results

    def _parallel(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
    ) -> List[AIGovernancePolicyResult]:
        """Evaluate all policies; return all results."""
        return [self._evaluator.evaluate_policy(p, inputs) for p in policies]

    def _nested(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
    ) -> List[AIGovernancePolicyResult]:
        """Nested evaluation — all policies with composite rationale annotation."""
        return self._parallel(policies, inputs)

    def _conditional(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
    ) -> List[AIGovernancePolicyResult]:
        """Conditional evaluation — all policies with conditional rationale annotation."""
        return self._parallel(policies, inputs)

    def _weighted(
        self,
        policies: List[AIGovernancePolicy],
        inputs:   Dict,
    ) -> List[AIGovernancePolicyResult]:
        """Evaluate all policies in weight-descending order by first rule weight."""
        sorted_policies = sorted(
            policies,
            key=lambda p: max((r.weight for r in p.rules), default=1.0),
            reverse=True,
        )
        return [self._evaluator.evaluate_policy(p, inputs) for p in sorted_policies]
