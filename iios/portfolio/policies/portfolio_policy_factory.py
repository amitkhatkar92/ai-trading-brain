"""
portfolio_policy_factory.py — iios.portfolio.policies
======================================================
Factory for creating Portfolio Policy Framework objects.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    PolicyAction,
    PolicyChainMode,
    PolicyPriority,
    PolicyType,
)
from .portfolio_policy import PortfolioPolicy
from .portfolio_policy_chain import PolicyChain
from .portfolio_policy_condition import PolicyCondition
from .portfolio_policy_request import PortfolioPolicyRequest
from .portfolio_policy_rule import PolicyRule


class PortfolioPolicyFactory:
    """
    Convenience factory for creating Portfolio Policy Framework objects.

    Provides helpers for creating requests, policies, rules, conditions,
    and chains — the building blocks of the policy evaluation pipeline.
    """

    # ------------------------------------------------------------------
    # Request creation
    # ------------------------------------------------------------------

    def create_request(
        self,
        portfolio_id:  str,
        policy_types:  Optional[List[PolicyType]] = None,
        *,
        priority: PolicyPriority = PolicyPriority.MEDIUM,
        inputs:   Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PortfolioPolicyRequest:
        """Create a PortfolioPolicyRequest."""
        return PortfolioPolicyRequest.create(
            portfolio_id,
            policy_types,
            priority = priority,
            inputs   = inputs,
            metadata = metadata,
        )

    # ------------------------------------------------------------------
    # Policy building blocks
    # ------------------------------------------------------------------

    def create_condition(
        self,
        name:        str,
        fn:          Callable[[Dict[str, Any]], bool],
        *,
        threshold:   Any = None,
        description: str = "",
    ) -> PolicyCondition:
        """Create a PolicyCondition from a callable."""
        return PolicyCondition(name, fn, threshold=threshold, description=description)

    def create_rule(
        self,
        name:           str,
        conditions:     List[PolicyCondition],
        action_on_pass: PolicyAction = PolicyAction.APPROVE,
        action_on_fail: PolicyAction = PolicyAction.REJECT,
        *,
        rule_id:  str = "",
        priority: int = 0,
    ) -> PolicyRule:
        """Create a PolicyRule."""
        return PolicyRule(
            rule_id or str(uuid.uuid4()),
            name,
            conditions,
            action_on_pass,
            action_on_fail,
            priority = priority,
        )

    def create_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        rules:       Optional[List[PolicyRule]] = None,
        *,
        policy_id: str = "",
        priority:  PolicyPriority = PolicyPriority.MEDIUM,
        version:   str = "1.0.0",
        description: str = "",
    ) -> PortfolioPolicy:
        """Create a PortfolioPolicy."""
        return PortfolioPolicy(
            policy_id   = policy_id or str(uuid.uuid4()),
            name        = name,
            policy_type = policy_type,
            priority    = priority,
            rules       = rules or [],
            version     = version,
            description = description,
        )

    # ------------------------------------------------------------------
    # Standard policies
    # ------------------------------------------------------------------

    def create_permissive_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        *,
        policy_id: str = "",
        priority:  PolicyPriority = PolicyPriority.LOW,
    ) -> PortfolioPolicy:
        """
        Create a policy with one rule that always returns APPROVE.

        Useful as a default / pass-through policy in test or staging
        environments.
        """
        condition = self.create_condition("always_pass", lambda _: True)
        rule      = self.create_rule("always_approve", [condition], PolicyAction.APPROVE)
        return self.create_policy(
            name,
            policy_type,
            [rule],
            policy_id = policy_id,
            priority  = priority,
        )

    def create_restrictive_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        *,
        policy_id: str = "",
        priority:  PolicyPriority = PolicyPriority.HIGH,
        action:    PolicyAction = PolicyAction.BLOCK,
    ) -> PortfolioPolicy:
        """
        Create a policy with one rule that always returns the given
        blocking action (default: BLOCK).

        Useful for testing conflict resolution or hard governance stops.
        """
        condition = self.create_condition("always_fail", lambda _: False)
        rule      = self.create_rule(
            "always_block", [condition],
            action_on_pass = PolicyAction.APPROVE,
            action_on_fail = action,
        )
        return self.create_policy(
            name,
            policy_type,
            [rule],
            policy_id = policy_id,
            priority  = priority,
        )

    # ------------------------------------------------------------------
    # Chain creation
    # ------------------------------------------------------------------

    def create_chain(
        self,
        name: str = "",
        *,
        chain_id:     str = "",
        mode:         PolicyChainMode = PolicyChainMode.SEQUENTIAL,
        stop_on_block: bool = True,
    ) -> PolicyChain:
        """Create a PolicyChain."""
        return PolicyChain(
            chain_id      = chain_id,
            name          = name,
            mode          = mode,
            stop_on_block = stop_on_block,
        )
