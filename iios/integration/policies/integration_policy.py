"""
integration_policy.py — iios.integration.policies
---------------------------------------------------
IntegrationPolicy — immutable governance policy descriptor.

A policy contains one or more rules, a type, a domain, a priority,
and metadata.  Policies are versioned and fully auditable.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    ACTION_PRECEDENCE,
    PolicyAction,
    PolicyDomain,
    PolicyPriority,
    PolicyType,
)
from .integration_policy_rule import IntegrationPolicyRule


@dataclass(frozen=True)
class IntegrationPolicy:
    """
    Immutable enterprise governance policy.

    Holds one or more rules evaluated against an integration context.
    The highest-precedence action from all fired rules is the result
    of policy evaluation.
    """

    policy_id:   str
    name:        str
    policy_type: PolicyType
    domain:      PolicyDomain
    priority:    PolicyPriority
    version:     str
    rules:       Tuple[IntegrationPolicyRule, ...]
    enabled:     bool
    description: str
    metadata:    Dict[str, Any]
    created_at:  str
    updated_at:  str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:        str,
        policy_type: PolicyType,
        domain:      PolicyDomain           = PolicyDomain.ENTERPRISE,
        priority:    PolicyPriority         = PolicyPriority.MEDIUM,
        rules:       Optional[List[IntegrationPolicyRule]] = None,
        *,
        version:     str                       = "1.0.0",
        enabled:     bool                      = True,
        description: str                       = "",
        metadata:    Optional[Dict[str, Any]]  = None,
        policy_id:   Optional[str]             = None,
    ) -> "IntegrationPolicy":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            policy_id   = policy_id or f"pol-{uuid.uuid4().hex[:12]}",
            name        = name,
            policy_type = (
                PolicyType(policy_type) if isinstance(policy_type, str) else policy_type
            ),
            domain      = (
                PolicyDomain(domain) if isinstance(domain, str) else domain
            ),
            priority    = (
                PolicyPriority(priority) if isinstance(priority, str) else priority
            ),
            version     = version,
            rules       = tuple(rules or []),
            enabled     = enabled,
            description = description,
            metadata    = dict(metadata or {}),
            created_at  = now,
            updated_at  = now,
        )

    # ── evaluation ────────────────────────────────────────────────────

    def evaluate(self, context_data: Dict[str, Any]) -> Optional[PolicyAction]:
        """
        Evaluate all rules and return the highest-precedence action.

        Returns None when the policy is disabled or no rules fire.
        """
        if not self.enabled:
            return None

        fired: List[PolicyAction] = []
        for rule in self.rules:
            action = rule.evaluate(context_data)
            if action is not None:
                fired.append(action)

        if not fired:
            return None

        # Return the highest-precedence action from the conflict table
        return max(fired, key=lambda a: ACTION_PRECEDENCE.index(a))

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "domain":      self.domain.value,
            "priority":    self.priority.value,
            "version":     self.version,
            "rules":       [r.to_dict() for r in self.rules],
            "enabled":     self.enabled,
            "description": self.description,
            "metadata":    self.metadata,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }
