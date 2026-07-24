"""
knowledge_policy_evaluator.py — iios.knowledge.policies
---------------------------------------------------------
KnowledgePolicyEvaluator — evaluates a KnowledgePolicy against artifacts.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import GovernanceDecision, PolicyAction
from .knowledge_policy import KnowledgePolicy
from .knowledge_policy_context import GovernancePolicyContext
from .knowledge_policy_result import PolicyEvaluationResult, PolicyRuleResult

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Action → Decision mapping (single-policy level)
# ---------------------------------------------------------------------------
_ACTION_TO_DECISION: Dict[PolicyAction, GovernanceDecision] = {
    PolicyAction.APPROVE:                  GovernanceDecision.APPROVED,
    PolicyAction.APPROVE_WITH_CONDITIONS:  GovernanceDecision.APPROVED_WITH_CONDITIONS,
    PolicyAction.REJECT:                   GovernanceDecision.REJECTED,
    PolicyAction.BLOCK:                    GovernanceDecision.BLOCKED,
    PolicyAction.ESCALATE:                 GovernanceDecision.ESCALATED,
    PolicyAction.REQUIRE_MANUAL_REVIEW:    GovernanceDecision.MANUAL_REVIEW,
    PolicyAction.REQUIRE_STEWARD_APPROVAL: GovernanceDecision.STEWARD_APPROVAL,
    PolicyAction.ARCHIVE:                  GovernanceDecision.ARCHIVED,
}


class KnowledgePolicyEvaluator:
    """
    Evaluates a single KnowledgePolicy against a set of knowledge artifacts.

    Each rule is evaluated in turn.  Triggered rules (all conditions met)
    contribute their action.  The highest-severity triggered action is chosen
    as the policy decision.

    Severity order (highest → lowest):
        BLOCK > REJECT > ESCALATE > MANUAL_REVIEW > STEWARD_APPROVAL
        > APPROVE_WITH_CONDITIONS > APPROVE > ARCHIVE
    """

    _SEVERITY: List[PolicyAction] = [
        PolicyAction.BLOCK,
        PolicyAction.REJECT,
        PolicyAction.ESCALATE,
        PolicyAction.REQUIRE_MANUAL_REVIEW,
        PolicyAction.REQUIRE_STEWARD_APPROVAL,
        PolicyAction.APPROVE_WITH_CONDITIONS,
        PolicyAction.APPROVE,
        PolicyAction.ARCHIVE,
    ]

    def evaluate(
        self,
        policy:    KnowledgePolicy,
        artifacts: Dict[str, Any],
        context:   GovernancePolicyContext,
    ) -> PolicyEvaluationResult:
        """
        Evaluate all rules in *policy* against *artifacts*.

        Returns PolicyEvaluationResult.  Never raises.
        """
        try:
            rule_results: List[PolicyRuleResult] = []
            triggered_actions: List[PolicyAction] = []

            for rule in policy.rules:
                result = rule.evaluate(artifacts)
                rule_results.append(result)
                if result.passed:
                    triggered_actions.append(result.action)
                    _log.debug(
                        f"Rule triggered: rule_id={rule.rule_id!r} "
                        f"action={result.action.value!r}"
                    )

            decision, reason = self._resolve(triggered_actions)

            return PolicyEvaluationResult.create(
                policy_id    = policy.policy_id,
                policy_name  = policy.name,
                policy_type  = policy.policy_type,
                domain       = policy.domain,
                decision     = decision,
                passed       = decision in (
                    GovernanceDecision.APPROVED,
                    GovernanceDecision.APPROVED_WITH_CONDITIONS,
                ),
                rule_results = rule_results,
                reason       = reason,
            )
        except Exception as exc:
            _log.warning(
                f"Policy evaluation error: policy_id={policy.policy_id!r} error={exc!r}"
            )
            return PolicyEvaluationResult.create(
                policy_id    = policy.policy_id,
                policy_name  = policy.name,
                policy_type  = policy.policy_type,
                domain       = policy.domain,
                decision     = GovernanceDecision.REJECTED,
                passed       = False,
                reason       = f"Evaluation error: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal: single-policy conflict resolution
    # ------------------------------------------------------------------

    def _resolve(
        self,
        triggered: List[PolicyAction],
    ) -> tuple:  # (GovernanceDecision, str)
        if not triggered:
            return GovernanceDecision.APPROVED, "No rules triggered — approved by default"

        for action in self._SEVERITY:
            if action in triggered:
                return _ACTION_TO_DECISION[action], f"Highest-severity action: {action.value!r}"

        return GovernanceDecision.APPROVED, "Approved"
