"""
decision_policy_factory.py — iios.decision.policies
=====================================================
Stateless factory for creating all policy-related objects.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyChainMode,
    PolicyConditionOperator,
    PolicyPriority,
    PolicyRuleLogic,
    PolicyStatus,
    PolicyType,
)
from .decision_policy           import DecisionPolicy
from .decision_policy_chain     import DecisionPolicyChain
from .decision_policy_condition import PolicyCondition
from .decision_policy_context   import PolicyEvaluationContext
from .decision_policy_request   import PolicyEvaluationRequest
from .decision_policy_rule      import PolicyRule


class DecisionPolicyFactory:
    """
    Stateless factory for constructing policy framework objects.

    All methods are instance methods for consistency and to allow
    subclassing with custom ID generation strategies.
    """

    # ------------------------------------------------------------------
    # Condition
    # ------------------------------------------------------------------

    def create_condition(
        self,
        name:        str,
        field_path:  str,
        operator:    PolicyConditionOperator,
        threshold:   Any                              = None,
        *,
        condition_id: Optional[str]                  = None,
        description: str                              = "",
        weight:      float                            = 1.0,
        custom_evaluator: Optional[Callable[[dict], bool]] = None,
    ) -> PolicyCondition:
        """Create a :class:`PolicyCondition`."""
        return PolicyCondition.create(
            name             = name,
            field_path       = field_path,
            operator         = operator,
            threshold        = threshold,
            condition_id     = condition_id,
            description      = description,
            weight           = weight,
            custom_evaluator = custom_evaluator,
        )

    # ------------------------------------------------------------------
    # Rule
    # ------------------------------------------------------------------

    def create_rule(
        self,
        name:        str,
        conditions:  List[PolicyCondition],
        action:      PolicyAction,
        *,
        rule_id:     Optional[str]     = None,
        logic:       PolicyRuleLogic   = PolicyRuleLogic.AND,
        description: str               = "",
        weight:      float             = 1.0,
    ) -> PolicyRule:
        """Create a :class:`PolicyRule`."""
        return PolicyRule.create(
            name        = name,
            conditions  = conditions,
            action      = action,
            rule_id     = rule_id,
            logic       = logic,
            description = description,
            weight      = weight,
        )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def create_policy(
        self,
        name:           str,
        policy_type:    PolicyType,
        priority:       PolicyPriority,
        default_action: PolicyAction,
        *,
        policy_id:      Optional[str]            = None,
        description:    str                       = "",
        version:        str                       = "1.0.0",
        status:         PolicyStatus              = PolicyStatus.ACTIVE,
        rules:          Optional[List[PolicyRule]] = None,
        tags:           Optional[List[str]]        = None,
        metadata:       Optional[dict]             = None,
        weight:         float                      = 1.0,
    ) -> DecisionPolicy:
        """Create a :class:`DecisionPolicy`."""
        return DecisionPolicy.create(
            name           = name,
            policy_type    = policy_type,
            priority       = priority,
            default_action = default_action,
            policy_id      = policy_id,
            description    = description,
            version        = version,
            status         = status,
            rules          = rules,
            tags           = tags,
            metadata       = metadata,
            weight         = weight,
        )

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def create_context(
        self,
        *,
        context_id:  Optional[str] = None,
        request_id:  str            = "",
        decision_id: str            = "",
        session_id:  str            = "",
        pipeline_id: str            = "",
        inputs:      Optional[Dict] = None,
        snapshots:   Optional[Dict] = None,
        metadata:    Optional[Dict] = None,
    ) -> PolicyEvaluationContext:
        """Create a :class:`PolicyEvaluationContext`."""
        return PolicyEvaluationContext.create(
            context_id  = context_id,
            request_id  = request_id,
            decision_id = decision_id,
            session_id  = session_id,
            pipeline_id = pipeline_id,
            inputs      = inputs,
            snapshots   = snapshots,
            metadata    = metadata,
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def create_request(
        self,
        context:           PolicyEvaluationContext,
        *,
        request_id:        Optional[str]                 = None,
        policy_ids:        Optional[List[str]]           = None,
        policy_types:      Optional[List[PolicyType]]    = None,
        chain_mode:        PolicyChainMode                = PolicyChainMode.SEQUENTIAL,
        conflict_strategy: ConflictResolutionStrategy     = ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
        metadata:          Optional[dict]                 = None,
    ) -> PolicyEvaluationRequest:
        """Create a :class:`PolicyEvaluationRequest`."""
        return PolicyEvaluationRequest.create(
            context           = context,
            request_id        = request_id,
            policy_ids        = policy_ids,
            policy_types      = policy_types,
            chain_mode        = chain_mode,
            conflict_strategy = conflict_strategy,
            metadata          = metadata,
        )

    # ------------------------------------------------------------------
    # Chain
    # ------------------------------------------------------------------

    def create_chain(
        self,
        name:      str,
        mode:      PolicyChainMode,
        policies:  List[DecisionPolicy],
        *,
        chain_id:  Optional[str]               = None,
        weights:   Optional[Dict[str, float]]  = None,
    ) -> DecisionPolicyChain:
        """Create a :class:`DecisionPolicyChain`."""
        return DecisionPolicyChain.create(
            name     = name,
            mode     = mode,
            policies = policies,
            chain_id = chain_id,
            weights  = weights,
        )
