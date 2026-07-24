"""
integration_policy_evaluator.py — iios.integration.policies
-------------------------------------------------------------
IntegrationPolicyEvaluator — evaluates a set of governance policies
against an IntegrationPolicyContext and resolves the final action.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from .constants import PolicyAction, PolicyDomain, PolicyType
from .integration_policy import IntegrationPolicy
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_priority import IntegrationPolicyPriority
from .integration_policy_result import GovernanceDecision, IntegrationPolicyResult


class IntegrationPolicyEvaluator:
    """
    Evaluates a list of governance policies against a context.

    Thread-safe (holds no mutable state).
    """

    def __init__(
        self,
        priority_resolver: Optional[IntegrationPolicyPriority] = None,
    ) -> None:
        self._resolver = priority_resolver or IntegrationPolicyPriority()

    def evaluate(
        self,
        policies:          List[IntegrationPolicy],
        policy_context:    IntegrationPolicyContext,
        requested_domains: Optional[List[PolicyDomain]] = None,
        requested_types:   Optional[List[PolicyType]]   = None,
    ) -> GovernanceDecision:
        """
        Evaluate all applicable policies and return a GovernanceDecision.

        Filtering:
        - Only enabled policies are evaluated.
        - If requested_domains is non-empty, only policies in those domains.
        - If requested_types  is non-empty, only policies of those types.
        """
        applicable = self._filter(policies, requested_domains, requested_types)
        context_data = policy_context.as_flat_dict()

        results:    List[IntegrationPolicyResult] = []
        conditions: List[str] = []
        reasons:    List[str] = []

        for policy in applicable:
            action = policy.evaluate(context_data)
            if action is None:
                action = PolicyAction.APPROVE

            result = IntegrationPolicyResult.create(
                policy_id   = policy.policy_id,
                policy_name = policy.name,
                action      = action,
                reason      = f"Policy '{policy.name}' produced action: {action.value}",
            )
            results.append(result)

            if action == PolicyAction.APPROVE_WITH_CONDITIONS:
                conditions.append(f"Conditions required by policy: {policy.name}")
            if result.is_blocking:
                reasons.append(f"Blocked by policy '{policy.name}': {action.value}")

        final_action = self._resolver.resolve(results, applicable)
        return GovernanceDecision.create(
            request_id     = policy_context.engine_request_id,
            final_action   = final_action,
            policy_results = results,
            conditions     = conditions,
            reasons        = reasons,
        )

    def evaluate_single(
        self,
        policy:         IntegrationPolicy,
        policy_context: IntegrationPolicyContext,
    ) -> IntegrationPolicyResult:
        """Evaluate a single policy and return its per-policy result."""
        context_data = policy_context.as_flat_dict()
        action       = policy.evaluate(context_data) or PolicyAction.APPROVE
        return IntegrationPolicyResult.create(
            policy_id   = policy.policy_id,
            policy_name = policy.name,
            action      = action,
            reason      = f"Policy '{policy.name}' produced action: {action.value}",
        )

    @staticmethod
    def _filter(
        policies:          List[IntegrationPolicy],
        requested_domains: Optional[List[PolicyDomain]],
        requested_types:   Optional[List[PolicyType]],
    ) -> List[IntegrationPolicy]:
        result = [p for p in policies if p.enabled]
        if requested_domains:
            result = [p for p in result if p.domain in requested_domains]
        if requested_types:
            result = [p for p in result if p.policy_type in requested_types]
        return result
