"""
governance_policy.py -- iios.ai.governance.core
=================================================
:class:`PolicyEffect`     — ALLOW or DENY.
:class:`PolicyPriority`   — numeric priority ordering.
:class:`GovernancePolicy` — immutable governance policy definition.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class PolicyEffect(str, Enum):
    """Outcome when a policy rule matches."""
    ALLOW    = "allow"
    DENY     = "deny"
    ESCALATE = "escalate"
    MONITOR  = "monitor"


class PolicyScope(str, Enum):
    """Scope of a governance policy."""
    GLOBAL      = "global"       # applies to all agents/models
    AGENT       = "agent"        # applies to a specific agent class
    MODEL       = "model"        # applies to a specific model
    SESSION     = "session"      # applies for a session lifetime
    ROLE        = "role"         # applies to a permission role


@dataclass(frozen=True)
class GovernancePolicy:
    """
    Immutable governance policy definition.

    ``conditions`` — frozenset of ``(condition_name, condition_value)`` tuples
                     that must all be satisfied for the policy to match.
    ``priority``   — higher number = evaluated first; default 100.
    ``is_active``  — inactive policies are skipped during evaluation.
    """

    policy_id:   str
    name:        str
    description: str
    scope:       PolicyScope
    effect:      PolicyEffect
    actions:     FrozenSet[str]       # glob-style action patterns, e.g. "model.*"
    resources:   FrozenSet[str]       # resource patterns
    principals:  FrozenSet[str]       # principal patterns ("*" = all)
    conditions:  FrozenSet[Tuple[str, Any]]
    priority:    int
    is_active:   bool
    created_at:  float
    tags:        FrozenSet[str]

    @classmethod
    def create(
        cls,
        name:        str,
        scope:       PolicyScope,
        effect:      PolicyEffect,
        actions:     FrozenSet[str]    = frozenset({"*"}),
        resources:   FrozenSet[str]    = frozenset({"*"}),
        principals:  FrozenSet[str]    = frozenset({"*"}),
        description: str               = "",
        priority:    int               = 100,
        is_active:   bool              = True,
        tags:        FrozenSet[str]    = frozenset(),
        **conditions: Any,
    ) -> "GovernancePolicy":
        return cls(
            policy_id   = str(uuid.uuid4()),
            name        = name,
            description = description,
            scope       = scope,
            effect      = effect,
            actions     = frozenset(actions),
            resources   = frozenset(resources),
            principals  = frozenset(principals),
            conditions  = frozenset(conditions.items()),
            priority    = priority,
            is_active   = is_active,
            created_at  = time.time(),
            tags        = frozenset(tags),
        )

    def matches_action(self, action: str) -> bool:
        """Return True if the given action matches any action pattern in this policy."""
        import fnmatch
        return any(fnmatch.fnmatch(action, pat) for pat in self.actions)

    def matches_principal(self, principal: str) -> bool:
        import fnmatch
        return any(fnmatch.fnmatch(principal, pat) for pat in self.principals)
