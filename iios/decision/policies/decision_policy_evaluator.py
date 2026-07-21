"""
decision_policy_evaluator.py — iios.decision.policies
=======================================================
Safe, timed wrapper around :class:`DecisionPolicy.evaluate`.

The evaluator never raises; it captures evaluation errors and returns a
BLOCK result instead, ensuring the calling chain is never interrupted by
a buggy policy definition.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from iios.common.logging.logging_manager import get_logger

from .constants import PolicyAction
from .decision_policy         import DecisionPolicy
from .decision_policy_context import PolicyEvaluationContext
from .decision_policy_result  import SinglePolicyResult

_log = get_logger(__name__)


class DecisionPolicyEvaluator:
    """
    Safely evaluates a single :class:`DecisionPolicy` against a
    :class:`PolicyEvaluationContext`.

    All exceptions are caught and converted to a BLOCK result, so that
    the policy chain is never disrupted by malformed policy definitions.
    """

    def evaluate(
        self,
        policy:  DecisionPolicy,
        context: PolicyEvaluationContext,
    ) -> SinglePolicyResult:
        """
        Evaluate *policy* against *context*.

        Returns
        -------
        :class:`SinglePolicyResult` — On error, returns a synthetic BLOCK
        result with an explanatory reason string.
        """
        try:
            return policy.evaluate(context)
        except Exception as exc:
            _log.warning(
                f"DecisionPolicyEvaluator: error evaluating policy "
                f"{policy.policy_id!r} ({policy.name!r}): {exc}"
            )
            return SinglePolicyResult(
                result_id         = str(uuid.uuid4()),
                policy_id         = policy.policy_id,
                policy_name       = policy.name,
                policy_type       = policy.policy_type,
                priority          = policy.priority,
                action            = PolicyAction.BLOCK,
                conditions_met    = 0,
                conditions_total  = 0,
                rule_results      = (),
                reason            = f"Evaluation error: {exc}",
                evaluation_time_s = 0.0,
                evaluated_at      = datetime.now(timezone.utc),
            )
