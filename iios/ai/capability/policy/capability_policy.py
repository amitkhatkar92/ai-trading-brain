"""
capability_policy.py -- iios.ai.capability.policy
===================================================
:class:`CapabilityPolicy`       — immutable allow/deny policy.
:class:`CapabilityPolicyEngine` — evaluates policies for a (principal, capability) pair.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import fnmatch
import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from ..exceptions.capability_exceptions import AICapabilityPolicyViolationError


class PolicyEffect(str, Enum):
    ALLOW   = "allow"
    DENY    = "deny"


@dataclass(frozen=True)
class CapabilityPolicy:
    """
    Immutable allow/deny policy matched by principal and capability patterns.

    Priority is evaluated in descending order (higher = evaluated first).
    The first matching DENY or ALLOW wins; default is ALLOW if no match.
    """

    policy_id:           str
    name:                str
    principal_pattern:   str   # fnmatch pattern, e.g. "agent_*", "*"
    capability_pattern:  str   # fnmatch pattern, e.g. "broker.*", "*"
    effect:              PolicyEffect
    priority:            int

    @classmethod
    def create(
        cls,
        name:                str,
        principal_pattern:   str         = "*",
        capability_pattern:  str         = "*",
        effect:              PolicyEffect = PolicyEffect.ALLOW,
        priority:            int          = 100,
    ) -> "CapabilityPolicy":
        return cls(
            policy_id          = str(uuid.uuid4()),
            name               = name,
            principal_pattern  = principal_pattern,
            capability_pattern = capability_pattern,
            effect             = effect,
            priority           = priority,
        )

    def matches(self, principal_id: str, capability_id: str) -> bool:
        """Return True if both patterns match."""
        return (
            fnmatch.fnmatch(principal_id,  self.principal_pattern)
            and fnmatch.fnmatch(capability_id, self.capability_pattern)
        )


class CapabilityPolicyEngine:
    """
    Thread-safe policy evaluation engine.

    Policies are evaluated by descending priority; the first match wins.
    When no policy matches the default result is ALLOW.
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock              = threading.Lock()
        self._policies: Dict[str, CapabilityPolicy] = {}

    def add_policy(self, policy: CapabilityPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy

    def remove_policy(self, policy_id: str) -> None:
        with self._lock:
            self._policies.pop(policy_id, None)

    def list_policies(self) -> List[CapabilityPolicy]:
        with self._lock:
            return sorted(self._policies.values(), key=lambda p: -p.priority)

    def evaluate(self, principal_id: str, capability_id: str) -> bool:
        """
        Return True if the (principal, capability) pair is allowed.

        Raises :class:`AICapabilityPolicyViolationError` on explicit DENY.
        """
        for policy in self.list_policies():
            if policy.matches(principal_id, capability_id):
                if policy.effect == PolicyEffect.DENY:
                    raise AICapabilityPolicyViolationError(
                        f"Policy '{policy.name}' denies access for principal "
                        f"'{principal_id}' to capability '{capability_id}'"
                    )
                return True
        return True   # default allow

    def policy_count(self) -> int:
        with self._lock:
            return len(self._policies)
