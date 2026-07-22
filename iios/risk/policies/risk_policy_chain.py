"""
risk_policy_chain.py — iios.risk.policies
===========================================
Policy chain evaluator.

Evaluates a collection of policies according to an
:class:`~.constants.EvaluationMode` and returns a flat list of
:class:`~.risk_policy_result.RiskPolicyResult` objects.

Supported modes
---------------
SEQUENTIAL  — Evaluate in priority order; stop on first denial result.
PARALLEL    — Evaluate all policies; collect all results.
COMPOSITE   — Treat each result set as independent; combine.
WEIGHTED    — Evaluate all; scale each result by its policy's first-rule weight.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .constants import EvaluationMode, PolicyAction, PolicyPriority
from .risk_policy import RiskPolicy
from .risk_policy_evaluator import RiskPolicyEvaluator
from .risk_policy_priority import PolicyPriorityResolver
from .risk_policy_result import RiskPolicyResult


class RiskPolicyChain:
    """
    Orchestrates multi-policy evaluation according to a chosen
    :class:`~.constants.EvaluationMode`.

    The chain is stateless; the caller provides policies and inputs on each
    invocation.  The chain never modifies policies or inputs.
    """

    def __init__(self, evaluator: Optional[RiskPolicyEvaluator] = None) -> None:
        self._evaluator = evaluator or RiskPolicyEvaluator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        policies: List[RiskPolicy],
        inputs:   Dict,
        mode:     EvaluationMode = EvaluationMode.SEQUENTIAL,
    ) -> List[RiskPolicyResult]:
        """
        Evaluate *policies* against *inputs* using *mode*.

        Returns
        -------
        List of :class:`RiskPolicyResult` — one per policy that was evaluated.
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
        # NESTED / CONDITIONAL treated as PARALLEL
        return self._parallel(enabled, inputs)

    # ------------------------------------------------------------------
    # Evaluation strategies
    # ------------------------------------------------------------------

    def _sequential(
        self,
        policies: List[RiskPolicy],
        inputs:   Dict,
    ) -> List[RiskPolicyResult]:
        """
        Evaluate in ascending priority order (CRITICAL first).
        Stop immediately when a denial result is encountered.
        """
        from .constants import DENY_ACTIONS

        sorted_policies = sorted(policies, key=lambda p: p.priority.value)
        results: List[RiskPolicyResult] = []
        for policy in sorted_policies:
            result = self._evaluator.evaluate_policy(policy, inputs)
            results.append(result)
            if result.action in DENY_ACTIONS:
                break
        return results

    def _parallel(
        self,
        policies: List[RiskPolicy],
        inputs:   Dict,
    ) -> List[RiskPolicyResult]:
        """Evaluate all policies; return all results."""
        return [self._evaluator.evaluate_policy(p, inputs) for p in policies]

    def _composite(
        self,
        policies: List[RiskPolicy],
        inputs:   Dict,
    ) -> List[RiskPolicyResult]:
        """
        Each policy is treated as an independent sub-policy evaluation.
        All policies are evaluated; their results are returned as-is.
        """
        return self._parallel(policies, inputs)

    def _weighted(
        self,
        policies: List[RiskPolicy],
        inputs:   Dict,
    ) -> List[RiskPolicyResult]:
        """
        Evaluate all policies.  The final dominant result is determined by
        weighting each result's action severity by the sum of weights of the
        first rule in the matching policy.

        Because RiskPolicyResult is immutable, the weighting logic influences
        which result is considered dominant — the actual result objects are
        returned unchanged.  The manager / engine layer will re-select the
        dominant from this list using PolicyPriorityResolver.
        """
        results = self._parallel(policies, inputs)
        if not results:
            return results

        # Build a weight mapping from policy_id → weight (first rule weight)
        weight_map: Dict[str, float] = {}
        for p in policies:
            if p.rules:
                weight_map[p.policy_id] = p.rules[0].weight
            else:
                weight_map[p.policy_id] = 1.0

        # Re-order results by (action_severity * weight) descending so the
        # manager's standard resolver picks the correctly weighted winner
        from .constants import ACTION_SEVERITY

        results.sort(
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0) * weight_map.get(r.policy_id, 1.0),
                -r.priority.value,
            ),
            reverse=True,
        )
        return results
