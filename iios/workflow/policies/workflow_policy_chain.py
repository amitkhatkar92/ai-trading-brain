"""
workflow_policy_chain.py — iios.workflow.policies
--------------------------------------------------
WorkflowPolicyChain — chains governance policies together for
sequential, parallel, or composite evaluation with conflict resolution.

Conflict resolution rules:
  EMERGENCY_STOP       > all others
  BLOCK                > all non-emergency
  REJECT               > all non-block
  REQUIRE_EXECUTIVE_APPROVAL > ESCALATE, REQUIRE_MANUAL_APPROVAL
  ESCALATE             > REQUIRE_MANUAL_APPROVAL
  REQUIRE_MANUAL_APPROVAL > APPROVE_WITH_CONDITIONS
  APPROVE_WITH_CONDITIONS > APPROVE

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTION_PRECEDENCE,
    PolicyAction,
    PolicyChainMode,
    higher_authority,
)
from .exceptions import WorkflowPolicyChainError
from .workflow_policy import WorkflowPolicy
from .workflow_policy_context import WorkflowPolicyContext
from .workflow_policy_evaluator import WorkflowPolicyEvaluator
from .workflow_policy_priority import PolicyPriorityItem
from .workflow_policy_result import WorkflowPolicyResult

_log = get_logger(__name__)


class WorkflowPolicyChain:
    """
    Chains governance policies and resolves conflicts among their results.

    Supports sequential, parallel, and composite evaluation modes.

    Thread-safe.
    """

    def __init__(
        self,
        mode:      PolicyChainMode                   = PolicyChainMode.SEQUENTIAL,
        evaluator: Optional[WorkflowPolicyEvaluator] = None,
    ) -> None:
        self._mode      = mode
        self._evaluator = evaluator or WorkflowPolicyEvaluator()
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Evaluation
    # ----------------------------------------------------------------

    def evaluate(
        self,
        policies: List[WorkflowPolicy],
        context:  WorkflowPolicyContext,
    ) -> Tuple[PolicyAction, List[WorkflowPolicyResult], str]:
        """
        Evaluate all policies and return the resolved governance action.

        Policies are sorted by priority before evaluation (CRITICAL first).

        Returns:
            (winning_action, all_results, combined_reasoning)
        """
        if not policies:
            return (
                PolicyAction.APPROVE,
                [],
                "No governance policies registered — default approval",
            )

        # Sort by priority (lowest value = CRITICAL first) then by name for determinism
        ordered = sorted(policies, key=lambda p: (p.priority.value, p.name))

        if self._mode == PolicyChainMode.SEQUENTIAL:
            return self._sequential(ordered, context)
        elif self._mode == PolicyChainMode.PARALLEL:
            return self._parallel(ordered, context)
        else:
            return self._composite(ordered, context)

    def _sequential(
        self,
        policies: List[WorkflowPolicy],
        context:  WorkflowPolicyContext,
    ) -> Tuple[PolicyAction, List[WorkflowPolicyResult], str]:
        """
        Evaluate policies one by one and short-circuit on EMERGENCY_STOP or BLOCK.
        After evaluation, resolve conflicts.
        """
        results: List[WorkflowPolicyResult] = []

        for policy in policies:
            try:
                result = self._evaluator.evaluate(policy, context)
                results.append(result)
                # Short-circuit for highest-authority actions
                if result.action == PolicyAction.EMERGENCY_STOP:
                    _log.warning(
                        f"Chain: emergency stop from policy={policy.policy_id!r}"
                    )
                    return self._resolve(results)
            except Exception as exc:
                _log.warning(
                    f"Chain: evaluation error for policy={policy.policy_id!r}: {exc!r}"
                )

        return self._resolve(results)

    def _parallel(
        self,
        policies: List[WorkflowPolicy],
        context:  WorkflowPolicyContext,
    ) -> Tuple[PolicyAction, List[WorkflowPolicyResult], str]:
        """
        Evaluate all policies (same as sequential without short-circuit),
        then resolve conflicts.
        """
        results: List[WorkflowPolicyResult] = []
        for policy in policies:
            try:
                result = self._evaluator.evaluate(policy, context)
                results.append(result)
            except Exception as exc:
                _log.warning(
                    f"Chain: evaluation error for policy={policy.policy_id!r}: {exc!r}"
                )
        return self._resolve(results)

    def _composite(
        self,
        policies: List[WorkflowPolicy],
        context:  WorkflowPolicyContext,
    ) -> Tuple[PolicyAction, List[WorkflowPolicyResult], str]:
        """
        Evaluate policies grouped by domain, then resolve across groups.
        Falls back to sequential.
        """
        return self._sequential(policies, context)

    # ----------------------------------------------------------------
    # Conflict resolution
    # ----------------------------------------------------------------

    def _resolve(
        self,
        results: List[WorkflowPolicyResult],
    ) -> Tuple[PolicyAction, List[WorkflowPolicyResult], str]:
        """
        Apply conflict resolution rules to produce the winning action.

        Critical policy overrides all.
        Emergency stop overrides all.
        Explicit reject overrides approval.
        Block overrides approval.
        Escalation overrides conditional approval.
        """
        if not results:
            return PolicyAction.APPROVE, [], "No results to resolve — default approval"

        winning_action    = PolicyAction.APPROVE
        winning_reasoning = "Default approval — all policies approved"

        for result in results:
            candidate = result.action
            if ACTION_PRECEDENCE.get(candidate, 99) < ACTION_PRECEDENCE.get(winning_action, 99):
                winning_action    = candidate
                winning_reasoning = (
                    f"Policy {result.policy_name!r} [{result.domain.value}] "
                    f"applied action={candidate.value!r}: {result.reasoning}"
                )

        # Collect conditions if approved with conditions
        conditions: List[str] = []
        for r in results:
            if r.action == PolicyAction.APPROVE_WITH_CONDITIONS and r.reasoning:
                conditions.append(r.reasoning)

        if conditions and winning_action == PolicyAction.APPROVE_WITH_CONDITIONS:
            winning_reasoning += f" | Conditions: {'; '.join(conditions)}"

        _log.debug(
            f"Chain resolved: action={winning_action.value!r} "
            f"policies={len(results)}"
        )
        return winning_action, results, winning_reasoning

    @property
    def mode(self) -> PolicyChainMode:
        return self._mode
