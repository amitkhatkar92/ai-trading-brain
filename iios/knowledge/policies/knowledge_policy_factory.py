"""
knowledge_policy_factory.py — iios.knowledge.policies
-------------------------------------------------------
KnowledgePolicyFactory — creates governance value objects and domain objects.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_GOVERNANCE,
    ConditionOperator,
    PolicyAction,
    PolicyChainMode,
    PolicyDomain,
    PolicyPriority,
    PolicyType,
)
from .knowledge_policy import KnowledgePolicy
from .knowledge_policy_chain import KnowledgePolicyChain
from .knowledge_policy_condition import PolicyCondition
from .knowledge_policy_request import KnowledgePolicyRequest
from .knowledge_policy_rule import PolicyRule


class KnowledgePolicyFactory:
    """
    Factory for creating governance policy objects.

    All objects are properly initialized with sane defaults.
    """

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def create_request(
        self,
        knowledge_id:   str,
        subsystem_id:   str,
        *,
        actor:          str                         = ACTOR_GOVERNANCE,
        priority:       PolicyPriority              = PolicyPriority.MEDIUM,
        policy_types:   Optional[List[PolicyType]]  = None,
        policy_domains: Optional[List[PolicyDomain]] = None,
        artifacts:      Optional[Dict[str, Any]]    = None,
        metadata:       Optional[Dict[str, Any]]    = None,
    ) -> KnowledgePolicyRequest:
        return KnowledgePolicyRequest.create(
            knowledge_id   = knowledge_id,
            subsystem_id   = subsystem_id,
            actor          = actor,
            priority       = priority,
            policy_types   = policy_types,
            policy_domains = policy_domains,
            artifacts      = artifacts,
            metadata       = metadata,
        )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def create_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        domain:      PolicyDomain,
        *,
        description: str                           = "",
        priority:    PolicyPriority                = PolicyPriority.MEDIUM,
        rules:       Optional[List[PolicyRule]]    = None,
        version:     str                           = "1.0",
        author:      str                           = ACTOR_GOVERNANCE,
        metadata:    Optional[Dict[str, Any]]      = None,
        activate:    bool                          = True,
    ) -> KnowledgePolicy:
        """Create a KnowledgePolicy, optionally activating it immediately."""
        policy = KnowledgePolicy(
            name        = name,
            description = description,
            policy_type = policy_type,
            domain      = domain,
            priority    = priority,
            rules       = rules,
            version     = version,
            author      = author,
            metadata    = metadata,
        )
        if activate:
            policy.activate()
        return policy

    # ------------------------------------------------------------------
    # Rule
    # ------------------------------------------------------------------

    def create_rule(
        self,
        name:         str,
        action:       PolicyAction,
        *,
        description:  str                            = "",
        conditions:   Optional[List[PolicyCondition]] = None,
        priority:     PolicyPriority                 = PolicyPriority.MEDIUM,
        is_mandatory: bool                           = False,
        metadata:     Optional[Dict[str, Any]]       = None,
    ) -> PolicyRule:
        return PolicyRule.create(
            name         = name,
            action       = action,
            description  = description,
            conditions   = conditions,
            priority     = priority,
            is_mandatory = is_mandatory,
            metadata     = metadata,
        )

    # ------------------------------------------------------------------
    # Condition
    # ------------------------------------------------------------------

    def create_condition(
        self,
        name:           str,
        field_path:     str,
        operator:       ConditionOperator,
        expected_value: Any = None,
        *,
        description:    str = "",
    ) -> PolicyCondition:
        return PolicyCondition.create(
            name           = name,
            field_path     = field_path,
            operator       = operator,
            expected_value = expected_value,
            description    = description,
        )

    # ------------------------------------------------------------------
    # Chain
    # ------------------------------------------------------------------

    def create_chain(
        self,
        name:     str,
        mode:     PolicyChainMode           = PolicyChainMode.SEQUENTIAL,
        *,
        policies: Optional[List[KnowledgePolicy]] = None,
        metadata: Optional[Dict[str, Any]]        = None,
    ) -> KnowledgePolicyChain:
        return KnowledgePolicyChain(
            name     = name,
            mode     = mode,
            policies = policies,
            metadata = metadata,
        )
