"""
workflow_policy_factory.py — iios.workflow.policies
----------------------------------------------------
WorkflowPolicyFactory — fluent factory for creating standard
governance policy objects with sensible defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    PolicyAction,
    PolicyDomain,
    PolicyPriorityLevel,
    PolicyType,
)
from .workflow_policy import WorkflowPolicy
from .workflow_policy_context import WorkflowPolicyContext
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_rule import PolicyRule


class WorkflowPolicyFactory:
    """
    Factory for creating well-formed governance policy objects.

    All returned objects are valid and ready to register.
    """

    # ----------------------------------------------------------------
    # Policy factories
    # ----------------------------------------------------------------

    @staticmethod
    def create_approve_all_policy(
        name: str,
        *,
        policy_type:  PolicyType       = PolicyType.WORKFLOW_GOVERNANCE,
        domain:       PolicyDomain     = PolicyDomain.WORKFLOW_GOVERNANCE,
        priority:     PolicyPriorityLevel = PolicyPriorityLevel.LOW,
        description:  str              = "Approve-all fallback policy",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicy:
        """Create a policy that always approves (no rules; default APPROVE)."""
        return WorkflowPolicy.create(
            name           = name,
            policy_type    = policy_type,
            domain         = domain,
            priority       = priority,
            rules          = [],
            default_action = PolicyAction.APPROVE,
            description    = description,
            metadata       = metadata or {},
        )

    @staticmethod
    def create_reject_all_policy(
        name: str,
        *,
        policy_type:  PolicyType       = PolicyType.WORKFLOW_GOVERNANCE,
        domain:       PolicyDomain     = PolicyDomain.WORKFLOW_GOVERNANCE,
        priority:     PolicyPriorityLevel = PolicyPriorityLevel.CRITICAL,
        description:  str              = "Reject-all lock-down policy",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicy:
        """Create a policy that always rejects (no rules; default REJECT)."""
        return WorkflowPolicy.create(
            name           = name,
            policy_type    = policy_type,
            domain         = domain,
            priority       = priority,
            rules          = [],
            default_action = PolicyAction.REJECT,
            description    = description,
            metadata       = metadata or {},
        )

    @staticmethod
    def create_security_policy(
        name:  str,
        *,
        rules: Optional[List[PolicyRule]] = None,
        priority: PolicyPriorityLevel     = PolicyPriorityLevel.HIGH,
        description: str                  = "Security governance policy",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicy:
        """Create a security-domain governance policy."""
        return WorkflowPolicy.create(
            name           = name,
            policy_type    = PolicyType.SECURITY,
            domain         = PolicyDomain.SECURITY_GOVERNANCE,
            priority       = priority,
            rules          = rules or [],
            default_action = PolicyAction.APPROVE,
            description    = description,
            metadata       = metadata or {},
        )

    @staticmethod
    def create_compliance_policy(
        name:  str,
        *,
        rules: Optional[List[PolicyRule]] = None,
        priority: PolicyPriorityLevel     = PolicyPriorityLevel.HIGH,
        description: str                  = "Compliance governance policy",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicy:
        """Create a compliance-domain governance policy."""
        return WorkflowPolicy.create(
            name           = name,
            policy_type    = PolicyType.COMPLIANCE,
            domain         = PolicyDomain.COMPLIANCE_GOVERNANCE,
            priority       = priority,
            rules          = rules or [],
            default_action = PolicyAction.APPROVE,
            description    = description,
            metadata       = metadata or {},
        )

    @staticmethod
    def create_risk_policy(
        name:  str,
        *,
        rules: Optional[List[PolicyRule]] = None,
        priority: PolicyPriorityLevel     = PolicyPriorityLevel.CRITICAL,
        description: str                  = "Risk governance policy",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicy:
        """Create a risk-domain governance policy."""
        return WorkflowPolicy.create(
            name           = name,
            policy_type    = PolicyType.RISK,
            domain         = PolicyDomain.RISK_GOVERNANCE,
            priority       = priority,
            rules          = rules or [],
            default_action = PolicyAction.APPROVE,
            description    = description,
            metadata       = metadata or {},
        )

    # ----------------------------------------------------------------
    # Context factory
    # ----------------------------------------------------------------

    @staticmethod
    def create_context(
        workflow_id:   str,
        workflow_type: str                     = "sequential",
        *,
        enterprise_id:       str               = "",
        environment:         str               = "production",
        security_context:    Optional[Dict[str, Any]] = None,
        compliance_context:  Optional[Dict[str, Any]] = None,
        resource_context:    Optional[Dict[str, Any]] = None,
        platform_context:    Optional[Dict[str, Any]] = None,
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> WorkflowPolicyContext:
        """Create a WorkflowPolicyContext with sensible defaults."""
        return WorkflowPolicyContext.create(
            workflow_id         = workflow_id,
            workflow_type       = workflow_type,
            enterprise_id       = enterprise_id,
            environment         = environment,
            security_context    = security_context or {},
            compliance_context  = compliance_context or {},
            resource_context    = resource_context or {},
            platform_context    = platform_context or {},
            metadata            = metadata or {},
        )

    # ----------------------------------------------------------------
    # Request factory
    # ----------------------------------------------------------------

    @staticmethod
    def create_request(
        workflow_id: str,
        context:     Optional[WorkflowPolicyContext] = None,
        *,
        policy_types:  Optional[List[PolicyType]]   = None,
        policy_domains: Optional[List[PolicyDomain]] = None,
        metadata:       Optional[Dict[str, Any]]    = None,
    ) -> WorkflowPolicyRequest:
        """Create a WorkflowPolicyRequest.  Auto-creates context if not provided."""
        if context is None:
            context = WorkflowPolicyFactory.create_context(workflow_id)
        return WorkflowPolicyRequest.create(
            workflow_id    = workflow_id,
            context        = context,
            policy_types   = policy_types or [],
            policy_domains = policy_domains or [],
            metadata       = metadata or {},
        )
