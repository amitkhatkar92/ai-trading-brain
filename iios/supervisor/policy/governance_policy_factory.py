"""
governance_policy_factory.py — iios.supervisor.policy
-------------------------------------------------------
Factory helpers for governance policy objects.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    ConditionOperator,
    EvaluationMode,
    GovernancePolicyType,
    LogicalOperator,
    PolicyAction,
    PolicyPriority,
)
from .governance_policy import GovernancePolicy
from .governance_policy_condition import GovernancePolicyCondition
from .governance_policy_request import GovernancePolicyRequest
from .governance_policy_rule import GovernancePolicyRule


class GovernancePolicyFactory:
    """
    Convenience factory for building governance policy objects in tests and
    configuration helpers.
    """

    def create_condition(
        self,
        name:       str,
        field_path: str,
        operator:   ConditionOperator,
        threshold:  Any = None,
        *,
        description: str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> GovernancePolicyCondition:
        return GovernancePolicyCondition.create(
            name        = name,
            field_path  = field_path,
            operator    = operator,
            threshold   = threshold,
            description = description,
            metadata    = metadata or {},
        )

    def create_rule(
        self,
        name:             str,
        conditions:       List[GovernancePolicyCondition],
        logical_operator: LogicalOperator,
        action:           PolicyAction,
        *,
        weight:      float = 1.0,
        description: str   = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> GovernancePolicyRule:
        return GovernancePolicyRule.create(
            name             = name,
            conditions       = conditions,
            logical_operator = logical_operator,
            action           = action,
            weight           = weight,
            description      = description,
            metadata         = metadata or {},
        )

    def create_policy(
        self,
        name:        str,
        policy_type: GovernancePolicyType,
        priority:    PolicyPriority,
        rules:       List[GovernancePolicyRule],
        *,
        version:          str                      = "1.0.0",
        evaluation_mode:  EvaluationMode           = EvaluationMode.SEQUENTIAL,
        default_action:   PolicyAction             = PolicyAction.APPROVE,
        enabled:          bool                     = True,
        description:      str                      = "",
        tags:             Optional[List[str]]      = None,
        metadata:         Optional[Dict[str, Any]] = None,
    ) -> GovernancePolicy:
        return GovernancePolicy.create(
            name            = name,
            policy_type     = policy_type,
            priority        = priority,
            rules           = rules,
            version         = version,
            evaluation_mode = evaluation_mode,
            default_action  = default_action,
            enabled         = enabled,
            description     = description,
            tags            = tags or [],
            metadata        = metadata or {},
        )

    def create_request(
        self,
        supervision_id: str,
        subsystem_id:   str = "test-subsystem",
        *,
        workflow_type: str                         = "test-workflow",
        inputs:        Optional[Dict[str, Any]]   = None,
        policy_types:  Optional[List[GovernancePolicyType]] = None,
        metadata:      Optional[Dict[str, Any]]   = None,
    ) -> GovernancePolicyRequest:
        return GovernancePolicyRequest.create(
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            inputs         = inputs or {},
            policy_types   = policy_types or [],
            metadata       = metadata or {},
        )

    def create_health_threshold_policy(
        self,
        name:       str,
        field_path: str,
        threshold:  float,
        *,
        priority:   PolicyPriority    = PolicyPriority.HIGH,
        action_if_below: PolicyAction = PolicyAction.BLOCK,
    ) -> GovernancePolicy:
        """Create a ready-made health threshold policy that blocks when value < threshold."""
        cond = self.create_condition(
            name       = f"{name} threshold condition",
            field_path = field_path,
            operator   = ConditionOperator.LT,
            threshold  = threshold,
        )
        rule = self.create_rule(
            name             = f"{name} threshold rule",
            conditions       = [cond],
            logical_operator = LogicalOperator.ALL,
            action           = action_if_below,
        )
        return self.create_policy(
            name        = name,
            policy_type = GovernancePolicyType.HEALTH_GOVERNANCE,
            priority    = priority,
            rules       = [rule],
        )
