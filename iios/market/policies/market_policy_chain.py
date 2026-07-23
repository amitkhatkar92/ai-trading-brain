"""
market_policy_chain.py — iios.market.policies
===============================================
Policy chain evaluator.

Evaluates a collection of market policies according to an
:class:`~.constants.EvaluationMode` and returns a flat list of
:class:`~.market_policy_result.MarketPolicyResult` objects.

Supported modes
---------------
SEQUENTIAL  — Evaluate in priority order; stop on first denial result.
PARALLEL    — Evaluate all policies; collect all results.
COMPOSITE   — Each policy treated independently; all results combined.
WEIGHTED    — Evaluate all; scale each result by its policy's first-rule weight.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .constants import DENY_ACTIONS, EvaluationMode
from .market_policy import MarketPolicy
from .market_policy_evaluator import MarketPolicyEvaluator
from .market_policy_result import MarketPolicyResult


class MarketPolicyChain:
    """
    Orchestrates multi-policy evaluation according to a chosen
    :class:`~.constants.EvaluationMode`.

    The chain is stateless; the caller provides policies and inputs on each
    invocation.  The chain never modifies policies or inputs.
    """

    def __init__(self, evaluator: Optional[MarketPolicyEvaluator] = None) -> None:
        self._evaluator = evaluator or MarketPolicyEvaluator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        policies: List[MarketPolicy],
        inputs:   Dict,
        mode:     EvaluationMode = EvaluationMode.SEQUENTIAL,
    ) -> List[MarketPolicyResult]:
        """
        Evaluate *policies* against *inputs* using *mode*.

        Returns
        -------
        List of :class:`MarketPolicyResult` — one per policy that was evaluated.
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
        policies: List[MarketPolicy],
        inputs:   Dict,
    ) -> List[MarketPolicyResult]:
        """
        Evaluate in ascending priority order (CRITICAL first).
        Stop immediately when a denial result is encountered.
        """
        sorted_policies = sorted(policies, key=lambda p: p.priority.value)
        results: List[MarketPolicyResult] = []
        for policy in sorted_policies:
            result = self._evaluator.evaluate_policy(policy, inputs)
            results.append(result)
            if result.action in DENY_ACTIONS:
                break
        return results

    def _parallel(
        self,
        policies: List[MarketPolicy],
        inputs:   Dict,
    ) -> List[MarketPolicyResult]:
        """Evaluate all policies; return all results."""
        return [self._evaluator.evaluate_policy(p, inputs) for p in policies]

    def _composite(
        self,
        policies: List[MarketPolicy],
        inputs:   Dict,
    ) -> List[MarketPolicyResult]:
        """Each policy treated independently; all results returned."""
        return self._parallel(policies, inputs)

    def _weighted(
        self,
        policies: List[MarketPolicy],
        inputs:   Dict,
    ) -> List[MarketPolicyResult]:
        """
        Evaluate all policies; re-order by (action_severity × weight) so that
        the manager's standard resolver picks the correctly weighted winner.
        """
        results = self._parallel(policies, inputs)
        if not results:
            return results

        weight_map: Dict[str, float] = {}
        for p in policies:
            if p.rules:
                weight_map[p.policy_id] = p.rules[0].weight
            else:
                weight_map[p.policy_id] = 1.0

        from .constants import ACTION_SEVERITY

        results.sort(
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0) * weight_map.get(r.policy_id, 1.0),
                -r.priority.value,
            ),
            reverse=True,
        )
        return results
