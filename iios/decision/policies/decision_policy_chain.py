"""
decision_policy_chain.py — iios.decision.policies
===================================================
A chain of policies evaluated in a configured mode.

Chain modes
-----------
SEQUENTIAL  — Policies are evaluated in priority order (lowest int first).
              Evaluation stops early when a BLOCK is encountered.
PARALLEL    — All policies are evaluated; all results are returned.
COMPOSITE   — All policies evaluated (alias for PARALLEL; reserved for
              sub-chain composition in future versions).
NESTED      — All policies evaluated (alias for PARALLEL; reserved for
              recursive chain nesting in future versions).
CONDITIONAL — All policies evaluated (alias for PARALLEL; reserved for
              predicate-driven branching in future versions).
WEIGHTED    — All policies evaluated; result weights are carried forward
              to the priority resolver for weighted aggregation.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PolicyAction, PolicyChainMode
from .decision_policy          import DecisionPolicy
from .decision_policy_context  import PolicyEvaluationContext
from .decision_policy_evaluator import DecisionPolicyEvaluator
from .decision_policy_result   import SinglePolicyResult

_log = get_logger(__name__)


@dataclass
class DecisionPolicyChain:
    """
    An ordered collection of :class:`DecisionPolicy` objects evaluated as
    a unit.

    Parameters
    ----------
    chain_id :  Unique identifier.
    name :      Human-readable name.
    mode :      Evaluation mode (see module docstring).
    policies :  Ordered list of policies.
    weights :   Overriding policy weights keyed by policy_id.
                If absent, the policy's own ``weight`` attribute is used.
    """

    chain_id:  str
    name:      str
    mode:      PolicyChainMode
    policies:  List[DecisionPolicy]            = field(default_factory=list)
    weights:   Dict[str, float]                = field(default_factory=dict)
    _evaluator: DecisionPolicyEvaluator        = field(
        default_factory=DecisionPolicyEvaluator, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, context: PolicyEvaluationContext) -> List[SinglePolicyResult]:
        """
        Evaluate all applicable policies and return a list of
        :class:`SinglePolicyResult` objects.

        Parameters
        ----------
        context : Evaluation context.
        """
        if not self.policies:
            return []

        if self.mode == PolicyChainMode.SEQUENTIAL:
            return self._evaluate_sequential(context)

        # PARALLEL, COMPOSITE, NESTED, CONDITIONAL, WEIGHTED — evaluate all
        return self._evaluate_all(context)

    def _evaluate_sequential(
        self,
        context: PolicyEvaluationContext,
    ) -> List[SinglePolicyResult]:
        """
        Priority-sorted sequential evaluation with early exit on BLOCK.
        """
        ordered = sorted(self.policies, key=lambda p: int(p.priority))
        results: List[SinglePolicyResult] = []

        for policy in ordered:
            result = self._evaluator.evaluate(policy, context)
            results.append(result)

            if result.action == PolicyAction.BLOCK:
                _log.debug(
                    f"DecisionPolicyChain: BLOCK from '{policy.name}' "
                    f"— stopping sequential chain"
                )
                break

        return results

    def _evaluate_all(
        self,
        context: PolicyEvaluationContext,
    ) -> List[SinglePolicyResult]:
        """Evaluate every policy, collecting all results."""
        return [self._evaluator.evaluate(p, context) for p in self.policies]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:      str,
        mode:      PolicyChainMode,
        policies:  List[DecisionPolicy],
        *,
        chain_id:  Optional[str]      = None,
        weights:   Optional[Dict[str, float]] = None,
    ) -> "DecisionPolicyChain":
        """Create a new :class:`DecisionPolicyChain`."""
        return cls(
            chain_id = chain_id or str(uuid.uuid4()),
            name     = name,
            mode     = mode,
            policies = list(policies),
            weights  = weights or {},
        )
