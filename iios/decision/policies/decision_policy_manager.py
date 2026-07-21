"""
decision_policy_manager.py — iios.decision.policies
=====================================================
Orchestrates the complete policy evaluation workflow.

Workflow
--------
1. Load active policies from the registry (filtered by policy_ids /
   policy_types from the request).
2. Validate each policy configuration (log warnings; don't fail).
3. Create a :class:`DecisionPolicyChain` for the requested chain mode.
4. Evaluate the chain → list of :class:`SinglePolicyResult`.
5. Resolve conflicts using :class:`PolicyPriorityResolver`.
6. Extract conditions for APPROVE_WITH_CONDITIONS outcomes.
7. Compute per-action counts and coverage fraction.
8. Build :class:`PolicyEvaluationSummary` and :class:`PolicyAuditReport`.
9. Return both.

Zero-policy behaviour
---------------------
When no policies are registered (or none match the filter), the manager
returns APPROVE with 0 policies evaluated.  This is the safe default for
a system that has not yet loaded any institutional policies.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import (
    APPROVAL_ACTIONS,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyType,
)
from .decision_policy_audit     import PolicyAuditReport, build_audit_report
from .decision_policy_chain     import DecisionPolicyChain
from .decision_policy_evaluator import DecisionPolicyEvaluator
from .decision_policy_priority  import PolicyPriorityResolver
from .decision_policy_registry  import DecisionPolicyRegistry
from .decision_policy_request   import PolicyEvaluationRequest
from .decision_policy_result    import PolicyEvaluationSummary, SinglePolicyResult
from .decision_policy_validator import DecisionPolicyValidator

_log = get_logger(__name__)


class DecisionPolicyManager:
    """
    Orchestrates policy loading, chaining, evaluation, conflict resolution,
    and result aggregation.

    Parameters
    ----------
    registry :  Shared :class:`DecisionPolicyRegistry`.
    evaluator : :class:`DecisionPolicyEvaluator` (safe wrapper).
    validator : :class:`DecisionPolicyValidator` for config checks.
    """

    def __init__(
        self,
        registry:  DecisionPolicyRegistry,
        evaluator: DecisionPolicyEvaluator,
        validator: DecisionPolicyValidator,
    ) -> None:
        self._registry  = registry
        self._evaluator = evaluator
        self._validator = validator
        self._resolver  = PolicyPriorityResolver()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        request: PolicyEvaluationRequest,
    ) -> Tuple[PolicyEvaluationSummary, PolicyAuditReport]:
        """
        Execute the full evaluation workflow and return
        ``(PolicyEvaluationSummary, PolicyAuditReport)``.
        """
        t_start = time.time()

        # 1 — load applicable policies
        policies = self._load_policies(request)

        # 2 — validate each policy (warn, never fail)
        for policy in policies:
            vr = self._validator.validate_policy(policy)
            if not vr.is_valid:
                _log.warning(
                    f"DecisionPolicyManager: policy {policy.policy_id!r} "
                    f"({policy.name!r}) failed validation: "
                    f"{vr.error_messages}"
                )

        # 3 — create chain and evaluate
        chain = DecisionPolicyChain.create(
            name     = f"chain-{request.request_id[:8]}",
            mode     = request.chain_mode,
            policies = policies,
        )
        policy_results: List[SinglePolicyResult] = chain.evaluate(request.context)

        # 4 — zero-policy default
        if not policy_results:
            return self._zero_policy_result(request, time.time() - t_start)

        # 5 — resolve conflicts
        final_action, conflict_applied = self._resolver.resolve(
            policy_results,
            request.conflict_strategy,
        )

        # 6 — extract conditions for APPROVE_WITH_CONDITIONS
        conditions = self._extract_conditions(policy_results, final_action)

        # 7 — counts
        action_counts = self._count_by_action(policy_results)

        # 8 — coverage
        total_registered = self._registry.active_count()
        coverage = len(policy_results) / max(total_registered, 1)

        elapsed = time.time() - t_start

        summary = PolicyEvaluationSummary(
            summary_id                   = str(uuid.uuid4()),
            request_id                   = request.request_id,
            decision_id                  = request.context.decision_id,
            final_action                 = final_action,
            policy_results               = tuple(policy_results),
            total_evaluated              = len(policy_results),
            approved_count               = action_counts.get("approved", 0),
            rejected_count               = action_counts.get("rejected", 0),
            blocked_count                = action_counts.get("blocked",  0),
            escalated_count              = action_counts.get("escalated", 0),
            deferred_count               = action_counts.get("deferred",  0),
            manual_review_count          = action_counts.get("manual_review", 0),
            conditions                   = tuple(conditions),
            conflict_resolution_applied  = conflict_applied,
            conflict_resolution_strategy = request.conflict_strategy,
            evaluation_time_s            = elapsed,
            coverage                     = coverage,
            evaluated_at                 = datetime.now(timezone.utc),
        )

        audit = build_audit_report(
            request_id       = request.request_id,
            decision_id      = request.context.decision_id,
            results          = policy_results,
            final_action     = final_action,
            conflict_applied = conflict_applied,
        )

        return summary, audit

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_policies(self, request: PolicyEvaluationRequest):
        """Load applicable policies from the registry."""
        if request.policy_ids:
            policies = []
            for pid in request.policy_ids:
                p = self._registry.find(pid)
                if p and p.is_active():
                    policies.append(p)
            return policies

        if request.policy_types:
            result = []
            for pt in request.policy_types:
                result.extend(self._registry.policies_by_type(pt))
            # deduplicate preserving order
            seen = set()
            deduped = []
            for p in result:
                if p.policy_id not in seen:
                    seen.add(p.policy_id)
                    deduped.append(p)
            return deduped

        return self._registry.active_policies()

    def _extract_conditions(
        self,
        results:      List[SinglePolicyResult],
        final_action: PolicyAction,
    ) -> List[str]:
        """
        Collect condition strings from approve-with-conditions results.
        """
        if final_action != PolicyAction.APPROVE_WITH_CONDITIONS:
            return []
        conds: List[str] = []
        for r in results:
            if r.action == PolicyAction.APPROVE_WITH_CONDITIONS:
                conds.append(r.reason)
        return conds

    def _count_by_action(
        self,
        results: List[SinglePolicyResult],
    ) -> dict:
        counts: dict = {
            "approved":      0,
            "rejected":      0,
            "blocked":       0,
            "escalated":     0,
            "deferred":      0,
            "manual_review": 0,
        }
        for r in results:
            if r.action in APPROVAL_ACTIONS:
                counts["approved"]  += 1
            elif r.action == PolicyAction.REJECT:
                counts["rejected"]  += 1
            elif r.action == PolicyAction.BLOCK:
                counts["blocked"]   += 1
            elif r.action == PolicyAction.ESCALATE:
                counts["escalated"] += 1
            elif r.action == PolicyAction.DEFER:
                counts["deferred"]  += 1
            elif r.action == PolicyAction.REQUIRE_MANUAL_REVIEW:
                counts["manual_review"] += 1
        return counts

    def _zero_policy_result(
        self,
        request: PolicyEvaluationRequest,
        elapsed: float,
    ) -> Tuple[PolicyEvaluationSummary, PolicyAuditReport]:
        """Return default APPROVE when no policies are registered / matched."""
        final_action = PolicyAction.APPROVE
        summary = PolicyEvaluationSummary(
            summary_id                   = str(uuid.uuid4()),
            request_id                   = request.request_id,
            decision_id                  = request.context.decision_id,
            final_action                 = final_action,
            policy_results               = (),
            total_evaluated              = 0,
            approved_count               = 0,
            rejected_count               = 0,
            blocked_count                = 0,
            escalated_count              = 0,
            deferred_count               = 0,
            manual_review_count          = 0,
            conditions                   = (),
            conflict_resolution_applied  = False,
            conflict_resolution_strategy = request.conflict_strategy,
            evaluation_time_s            = elapsed,
            coverage                     = 0.0,
            evaluated_at                 = datetime.now(timezone.utc),
        )
        audit = build_audit_report(
            request_id       = request.request_id,
            decision_id      = request.context.decision_id,
            results          = [],
            final_action     = final_action,
            conflict_applied = False,
        )
        return summary, audit
