"""
policy_engine.py -- iios.ai.governance.policy
===============================================
:class:`PolicyEngine` — evaluates GovernanceContext against registered policies.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from ..core.governance_context  import GovernanceContext
from ..core.governance_decision import GovernanceDecision, GovernanceDecisionType
from ..core.governance_policy   import GovernancePolicy, PolicyEffect
from ..exceptions.governance_exceptions import AIPolicyEvaluationError
from .policy_registry import PolicyRegistry
from .policy_rule     import PolicyEvaluation, PolicyViolation


class PolicyEngine:
    """
    Evaluates a :class:`GovernanceContext` against all registered policies
    and returns an authoritative :class:`GovernanceDecision`.

    Evaluation order: policies are processed by descending priority.
    First matching policy with DENY or ESCALATE effect short-circuits.
    If no policy matches, default is ALLOW.
    """

    def __init__(self, registry: Optional[PolicyRegistry] = None) -> None:
        self._registry:   PolicyRegistry = registry or PolicyRegistry()
        self._lock:       threading.Lock = threading.Lock()
        self._violations: List[PolicyViolation] = []

    @property
    def registry(self) -> PolicyRegistry:
        return self._registry

    # ── evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, context: GovernanceContext) -> GovernanceDecision:
        """
        Evaluate all active policies against ``context`` and return a decision.

        :raises AIPolicyEvaluationError: if evaluation itself fails unexpectedly.
        """
        try:
            policies = self._registry.list_policies(active_only=True)
        except Exception as exc:
            raise AIPolicyEvaluationError(
                f"Failed to load policies: {exc}"
            ) from exc

        evaluations: List[PolicyEvaluation] = []
        matched_deny:    Optional[GovernancePolicy] = None
        matched_escalate: Optional[GovernancePolicy] = None

        for policy in policies:
            if not policy.matches_action(context.action):
                continue
            if not policy.matches_principal(context.principal_id):
                continue

            eval_result = PolicyEvaluation.build(
                policy_id = policy.policy_id,
                matched   = True,
                effect    = policy.effect,
            )
            evaluations.append(eval_result)

            if policy.effect == PolicyEffect.DENY:
                matched_deny = policy
                break
            if policy.effect == PolicyEffect.ESCALATE and matched_escalate is None:
                matched_escalate = policy

        # Determine final decision
        if matched_deny:
            violation = PolicyViolation.create(
                policy_id    = matched_deny.policy_id,
                principal_id = context.principal_id,
                action       = context.action,
                resource     = context.resource,
                description  = f"Denied by policy {matched_deny.name!r}",
            )
            with self._lock:
                self._violations.append(violation)
            return GovernanceDecision.deny(
                context    = context,
                rationale  = f"Denied by policy {matched_deny.name!r}",
                policy_ids = frozenset({matched_deny.policy_id}),
            )

        if matched_escalate:
            return GovernanceDecision.escalate(
                context    = context,
                rationale  = f"Escalation required by policy {matched_escalate.name!r}",
                policy_ids = frozenset({matched_escalate.policy_id}),
            )

        matched_policy_ids = frozenset(e.policy_id for e in evaluations)
        return GovernanceDecision.allow(
            context    = context,
            rationale  = "Allowed — no blocking policies matched",
            policy_ids = matched_policy_ids,
        )

    # ── violation history ─────────────────────────────────────────────────────

    def violations(self, limit: int = 100) -> List[PolicyViolation]:
        with self._lock:
            return list(self._violations[-limit:])

    def violation_count(self) -> int:
        with self._lock:
            return len(self._violations)

    def clear_violations(self) -> None:
        with self._lock:
            self._violations.clear()
