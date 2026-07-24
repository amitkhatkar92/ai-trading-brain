"""
integration_policy_factory.py — iios.integration.policies
----------------------------------------------------------
IntegrationPolicyFactory — creates well-formed governance policy objects.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .constants import (
    ConditionOperator,
    PolicyAction,
    PolicyChainMode,
    PolicyDomain,
    PolicyEvaluationMode,
    PolicyPriority,
    PolicyType,
)
from .integration_policy import IntegrationPolicy
from .integration_policy_chain import IntegrationPolicyChain
from .integration_policy_condition import IntegrationPolicyCondition
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_request import IntegrationPolicyRequest
from .integration_policy_result import GovernanceDecision, IntegrationPolicyResult
from .integration_policy_rule import IntegrationPolicyRule


class IntegrationPolicyFactory:
    """Creates all policy framework objects from plain parameters."""

    # ── conditions ────────────────────────────────────────────────────

    def create_condition(
        self,
        name:           str,
        field_path:     str,
        operator:       ConditionOperator,
        expected_value: Any = None,
        *,
        description:    str = "",
    ) -> IntegrationPolicyCondition:
        return IntegrationPolicyCondition.create(
            name, field_path, operator, expected_value, description=description
        )

    # ── rules ─────────────────────────────────────────────────────────

    def create_rule(
        self,
        name:            str,
        action:          PolicyAction,
        conditions:      Optional[List[IntegrationPolicyCondition]] = None,
        evaluation_mode: PolicyEvaluationMode = PolicyEvaluationMode.ALL_MUST_PASS,
        *,
        description:     str = "",
        reason_template: str = "",
    ) -> IntegrationPolicyRule:
        return IntegrationPolicyRule.create(
            name, action, conditions, evaluation_mode,
            description=description, reason_template=reason_template,
        )

    # ── policies ──────────────────────────────────────────────────────

    def create_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        domain:      PolicyDomain       = PolicyDomain.ENTERPRISE,
        priority:    PolicyPriority     = PolicyPriority.MEDIUM,
        rules:       Optional[List[IntegrationPolicyRule]] = None,
        *,
        description: str  = "",
        enabled:     bool = True,
    ) -> IntegrationPolicy:
        return IntegrationPolicy.create(
            name, policy_type, domain, priority, rules,
            description=description, enabled=enabled,
        )

    # ── chains ────────────────────────────────────────────────────────

    def create_chain(
        self,
        name:      str              = "default-chain",
        mode:      PolicyChainMode  = PolicyChainMode.SEQUENTIAL,
        policies:  Optional[List[IntegrationPolicy]] = None,
        condition: Optional[Callable[[IntegrationPolicyContext], bool]] = None,
    ) -> IntegrationPolicyChain:
        return IntegrationPolicyChain(
            name=name, mode=mode, policies=policies, condition=condition
        )

    # ── context ───────────────────────────────────────────────────────

    def create_context(
        self,
        engine_request_id: str,
        engine_session_id: str,
        connector_type:    str,
        adapter_type:      str = "",
        protocol_type:     str = "",
        **kwargs: Any,
    ) -> IntegrationPolicyContext:
        return IntegrationPolicyContext.create(
            engine_request_id, engine_session_id,
            connector_type, adapter_type, protocol_type,
            **kwargs,
        )

    # ── request ───────────────────────────────────────────────────────

    def create_request(
        self,
        policy_context:    IntegrationPolicyContext,
        requested_domains: Optional[List[PolicyDomain]] = None,
        requested_types:   Optional[List[PolicyType]]   = None,
    ) -> IntegrationPolicyRequest:
        return IntegrationPolicyRequest.create(
            policy_context, requested_domains, requested_types
        )

    # ── pre-built convenience policies ────────────────────────────────

    def create_approve_all_policy(
        self,
        name:     str             = "Allow All",
        priority: PolicyPriority  = PolicyPriority.LOW,
    ) -> IntegrationPolicy:
        """A policy with a single unconditional APPROVE rule."""
        rule = self.create_rule("Approve All", PolicyAction.APPROVE)
        return self.create_policy(
            name, PolicyType.ENTERPRISE_INTEGRATION,
            domain=PolicyDomain.ENTERPRISE, priority=priority, rules=[rule],
        )

    def create_reject_all_policy(
        self,
        name:     str             = "Deny All",
        priority: PolicyPriority  = PolicyPriority.CRITICAL,
    ) -> IntegrationPolicy:
        """A policy with a single unconditional REJECT rule."""
        rule = self.create_rule("Reject All", PolicyAction.REJECT)
        return self.create_policy(
            name, PolicyType.ENTERPRISE_INTEGRATION,
            domain=PolicyDomain.ENTERPRISE, priority=priority, rules=[rule],
        )

    def create_emergency_stop_policy(
        self,
        name:          str = "Emergency Stop",
        field_path:    str = "environment",
        trigger_value: Any = "emergency",
    ) -> IntegrationPolicy:
        """A policy that triggers an emergency stop when a field matches a value."""
        condition = self.create_condition(
            "Emergency Trigger",
            field_path,
            ConditionOperator.EQUALS,
            trigger_value,
        )
        rule = self.create_rule(
            "Emergency Stop Rule",
            PolicyAction.EMERGENCY_STOP,
            [condition],
        )
        return self.create_policy(
            name, PolicyType.ENTERPRISE_INTEGRATION,
            domain=PolicyDomain.ENTERPRISE,
            priority=PolicyPriority.CRITICAL,
            rules=[rule],
        )

    def create_security_approval_policy(
        self,
        name:            str              = "Security Approval Required",
        field_path:      str              = "security_config.requires_approval",
        expected_value:  Any              = True,
        priority:        PolicyPriority   = PolicyPriority.HIGH,
    ) -> IntegrationPolicy:
        """A policy that requires security approval for flagged requests."""
        condition = self.create_condition(
            "Requires Security Approval",
            field_path,
            ConditionOperator.EQUALS,
            expected_value,
        )
        rule = self.create_rule(
            "Require Security Approval",
            PolicyAction.REQUIRE_SECURITY_APPROVAL,
            [condition],
        )
        return self.create_policy(
            name, PolicyType.AUTHENTICATION,
            domain=PolicyDomain.SECURITY, priority=priority, rules=[rule],
        )
