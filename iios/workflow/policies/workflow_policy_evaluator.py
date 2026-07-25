"""
workflow_policy_evaluator.py — iios.workflow.policies
------------------------------------------------------
WorkflowPolicyEvaluator — evaluates a single WorkflowPolicy against a
WorkflowPolicyContext and produces a WorkflowPolicyResult.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger

from .workflow_policy import WorkflowPolicy
from .workflow_policy_context import WorkflowPolicyContext
from .workflow_policy_result import WorkflowPolicyResult

_log = get_logger(__name__)


class WorkflowPolicyEvaluator:
    """
    Evaluates a single governance policy against a context.

    Thread-safe — stateless.
    """

    def evaluate(
        self,
        policy:  WorkflowPolicy,
        context: WorkflowPolicyContext,
    ) -> WorkflowPolicyResult:
        """
        Evaluate ``policy`` against ``context``.

        Returns:
            WorkflowPolicyResult with the resulting action and reasoning.
        """
        _log.debug(
            f"Evaluator: evaluating policy={policy.policy_id!r} "
            f"name={policy.name!r} type={policy.policy_type.value!r}"
        )
        action, reasoning, matched_rule_id = policy.evaluate(context)
        conditions_met = matched_rule_id is not None

        result = WorkflowPolicyResult.create(
            policy_id       = policy.policy_id,
            policy_name     = policy.name,
            policy_type     = policy.policy_type,
            domain          = policy.domain,
            priority        = policy.priority,
            action          = action,
            reasoning       = reasoning,
            matched_rule_id = matched_rule_id,
            conditions_met  = conditions_met,
        )
        _log.debug(
            f"Evaluator: result={action.value!r} "
            f"policy={policy.policy_id!r} rule={matched_rule_id!r}"
        )
        return result
