"""
ai_governance_policy_factory.py — iios.supervisor.policies
------------------------------------------------------------
Object factory for the AI Governance Policy Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    AIGovernancePolicyAction,
    AIGovernancePolicyType,
    ConditionOperator,
    EvaluationMode,
    LogicalOperator,
    PolicyPriority,
)
from .ai_governance_policy import AIGovernancePolicy
from .ai_governance_policy_condition import AIGovernancePolicyCondition
from .ai_governance_policy_context import AIGovernancePolicyContext
from .ai_governance_policy_request import AIGovernancePolicyRequest
from .ai_governance_policy_rule import AIGovernancePolicyRule


class AIGovernancePolicyFactory:
    """
    Convenience factory for building governance objects in tests,
    configuration helpers, and policy initialisation code.
    """

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def create_condition(
        self,
        name:       str,
        field_path: str,
        operator:   ConditionOperator,
        threshold:  Any = None,
        *,
        description: str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> AIGovernancePolicyCondition:
        return AIGovernancePolicyCondition.create(
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
        conditions:       List[AIGovernancePolicyCondition],
        logical_operator: LogicalOperator,
        action:           AIGovernancePolicyAction,
        *,
        weight:      float = 1.0,
        description: str   = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> AIGovernancePolicyRule:
        return AIGovernancePolicyRule.create(
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
        policy_type: AIGovernancePolicyType,
        priority:    PolicyPriority,
        rules:       List[AIGovernancePolicyRule],
        *,
        version:          str                           = "1.0.0",
        evaluation_mode:  EvaluationMode                = EvaluationMode.SEQUENTIAL,
        default_action:   AIGovernancePolicyAction      = AIGovernancePolicyAction.APPROVE,
        enabled:          bool                          = True,
        description:      str                           = "",
        tags:             Optional[List[str]]           = None,
        metadata:         Optional[Dict[str, Any]]      = None,
    ) -> AIGovernancePolicy:
        return AIGovernancePolicy.create(
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
        workflow_type:  str                                     = "test-workflow",
        inputs:         Optional[Dict[str, Any]]                = None,
        policy_types:   Optional[List[AIGovernancePolicyType]]  = None,
        context:        Optional[AIGovernancePolicyContext]      = None,
        metadata:       Optional[Dict[str, Any]]                = None,
    ) -> AIGovernancePolicyRequest:
        return AIGovernancePolicyRequest.create(
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            inputs         = inputs or {},
            policy_types   = policy_types or [],
            context        = context,
            metadata       = metadata or {},
        )

    # ------------------------------------------------------------------
    # Domain-specific convenience methods
    # ------------------------------------------------------------------

    def create_ai_safety_threshold_policy(
        self,
        name:       str,
        field_path: str,
        threshold:  float,
        *,
        action_if_unsafe: AIGovernancePolicyAction = AIGovernancePolicyAction.EMERGENCY_STOP,
        priority:         PolicyPriority            = PolicyPriority.CRITICAL,
    ) -> AIGovernancePolicy:
        """
        Create an AI Safety policy that triggers EMERGENCY_STOP when
        *field_path* < *threshold*.
        """
        cond = self.create_condition(
            name       = f"{name} safety condition",
            field_path = field_path,
            operator   = ConditionOperator.LT,
            threshold  = threshold,
        )
        rule = self.create_rule(
            name             = f"{name} safety rule",
            conditions       = [cond],
            logical_operator = LogicalOperator.ALL,
            action           = action_if_unsafe,
        )
        return self.create_policy(
            name        = name,
            policy_type = AIGovernancePolicyType.AI_SAFETY,
            priority    = priority,
            rules       = [rule],
        )

    def create_human_oversight_policy(
        self,
        name:       str,
        field_path: str,
        threshold:  float,
        *,
        operator:  ConditionOperator = ConditionOperator.GT,
        priority:  PolicyPriority    = PolicyPriority.HIGH,
    ) -> AIGovernancePolicy:
        """
        Create a Human Oversight policy that requires human approval when
        *field_path* > *threshold* (e.g. risk score exceeds tolerance).
        """
        cond = self.create_condition(
            name       = f"{name} oversight condition",
            field_path = field_path,
            operator   = operator,
            threshold  = threshold,
        )
        rule = self.create_rule(
            name             = f"{name} oversight rule",
            conditions       = [cond],
            logical_operator = LogicalOperator.ALL,
            action           = AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL,
        )
        return self.create_policy(
            name        = name,
            policy_type = AIGovernancePolicyType.HUMAN_OVERSIGHT,
            priority    = priority,
            rules       = [rule],
        )

    def create_compliance_block_policy(
        self,
        name:       str,
        field_path: str,
        threshold:  Any,
        *,
        operator:   ConditionOperator = ConditionOperator.EQ,
        priority:   PolicyPriority    = PolicyPriority.CRITICAL,
    ) -> AIGovernancePolicy:
        """
        Create a Compliance policy that BLOCKS when the field matches the
        threshold (e.g. market is ``"halt"``).
        """
        cond = self.create_condition(
            name       = f"{name} compliance condition",
            field_path = field_path,
            operator   = operator,
            threshold  = threshold,
        )
        rule = self.create_rule(
            name             = f"{name} compliance rule",
            conditions       = [cond],
            logical_operator = LogicalOperator.ALL,
            action           = AIGovernancePolicyAction.BLOCK,
        )
        return self.create_policy(
            name        = name,
            policy_type = AIGovernancePolicyType.COMPLIANCE,
            priority    = priority,
            rules       = [rule],
        )

    def create_autonomous_operation_policy(
        self,
        name:             str,
        field_path:       str,
        threshold:        float,
        *,
        operator:         ConditionOperator            = ConditionOperator.GT,
        action_if_over:   AIGovernancePolicyAction     = AIGovernancePolicyAction.ESCALATE,
        priority:         PolicyPriority               = PolicyPriority.HIGH,
    ) -> AIGovernancePolicy:
        """
        Create an Autonomous Operation policy that ESCALATES when
        *field_path* > *threshold*.
        """
        cond = self.create_condition(
            name       = f"{name} autonomy condition",
            field_path = field_path,
            operator   = operator,
            threshold  = threshold,
        )
        rule = self.create_rule(
            name             = f"{name} autonomy rule",
            conditions       = [cond],
            logical_operator = LogicalOperator.ALL,
            action           = action_if_over,
        )
        return self.create_policy(
            name        = name,
            policy_type = AIGovernancePolicyType.AUTONOMOUS_OPERATION,
            priority    = priority,
            rules       = [rule],
        )
