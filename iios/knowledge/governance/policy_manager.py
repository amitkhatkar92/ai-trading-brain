"""
iios/knowledge/governance/policy_manager.py
============================================
PolicyManager — stores and evaluates governance policies.

Policies are stored in priority order (highest first).  When evaluating
a record, policies are tested until one matches and dictates the action
(AUTO_APPROVE, AUTO_REJECT, REQUIRE_MANUAL, BLOCK).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .governance_constants import (
    GovernanceAction,
    MAX_POLICIES,
    PolicyType,
    SYSTEM_GOVERNANCE_ACTOR,
)
from .governance_exceptions import PolicyAlreadyExistsError, PolicyNotFoundError
from .models.policy import GovernancePolicy

__all__ = ["PolicyManager", "get_policy_manager", "reset_policy_manager"]

_LOG = logging.getLogger("iios.knowledge.governance.policy")
_lock = threading.Lock()
_manager: Optional["PolicyManager"] = None


class PolicyManager:
    """Thread-safe store and evaluator for governance policies."""

    def __init__(self, max_policies: int = MAX_POLICIES) -> None:
        self._lock       = threading.RLock()
        self._max        = max_policies
        self._policies: dict[str, GovernancePolicy] = {}
        self._load_defaults()

    # ── Default policies ──────────────────────────────────────────────────────

    def _load_defaults(self) -> None:
        """Install default policies for the governance engine."""
        # Auto-approve high-quality records
        p1 = GovernancePolicy(
            name        = "AutoApproveHighQuality",
            description = "Auto-approve records with KQI ≥ 0.75",
            policy_type = PolicyType.AUTO_APPROVE,
            action      = GovernanceAction.AUTO_APPROVE,
            priority    = 80,
        )
        p1.add_condition("kqi", ">=", 0.75)
        p1.add_condition("has_critical_violations", "==", False)

        # Block compliance records (must go through manual review)
        p2 = GovernancePolicy(
            name        = "ManualReviewForCompliance",
            description = "Compliance-domain records always require manual review",
            policy_type = PolicyType.REQUIRE_MANUAL,
            action      = GovernanceAction.REVIEW,
            priority    = 90,  # checked before auto-approve
        )
        p2.add_condition("domain", "in", ["compliance", "risk"])

        # Auto-reject critically violated records
        p3 = GovernancePolicy(
            name        = "AutoRejectCriticalViolations",
            description = "Auto-reject records with critical violations",
            policy_type = PolicyType.AUTO_REJECT,
            action      = GovernanceAction.REJECT,
            priority    = 95,  # highest priority — checked first
        )
        p3.add_condition("has_critical_violations", "==", True)

        for p in (p1, p2, p3):
            self._policies[p.policy_id] = p

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_policy(self, policy: GovernancePolicy) -> GovernancePolicy:
        with self._lock:
            if len(self._policies) >= self._max:
                raise PolicyAlreadyExistsError(
                    f"Maximum policy count ({self._max}) reached.", code="GE-202"
                )
            if policy.policy_id in self._policies:
                raise PolicyAlreadyExistsError(
                    f"Policy '{policy.policy_id}' already exists.", code="GE-202"
                )
            self._policies[policy.policy_id] = policy
        _LOG.info("Policy added: '%s' (%s)", policy.name, policy.policy_id[:8])
        return policy

    def get(self, policy_id: str) -> GovernancePolicy:
        with self._lock:
            p = self._policies.get(policy_id)
        if p is None:
            raise PolicyNotFoundError(
                f"Policy '{policy_id}' not found.", code="GE-201"
            )
        return p

    def remove(self, policy_id: str) -> GovernancePolicy:
        with self._lock:
            p = self._policies.pop(policy_id, None)
        if p is None:
            raise PolicyNotFoundError(
                f"Policy '{policy_id}' not found.", code="GE-201"
            )
        return p

    def update(self, policy: GovernancePolicy) -> GovernancePolicy:
        with self._lock:
            if policy.policy_id not in self._policies:
                raise PolicyNotFoundError(
                    f"Policy '{policy.policy_id}' not found.", code="GE-201"
                )
            self._policies[policy.policy_id] = policy
        return policy

    def list_all(self, active_only: bool = False) -> list[GovernancePolicy]:
        with self._lock:
            policies = list(self._policies.values())
        if active_only:
            policies = [p for p in policies if p.is_active]
        return sorted(policies, key=lambda p: p.priority, reverse=True)

    def exists(self, policy_id: str) -> bool:
        with self._lock:
            return policy_id in self._policies

    # ── Evaluation ────────────────────────────────────────────────────────────

    def get_applicable(
        self,
        context: dict[str, Any],
    ) -> list[GovernancePolicy]:
        """Return policies that match *context*, sorted by priority (desc)."""
        with self._lock:
            policies = list(self._policies.values())
        matched = [p for p in policies if p.is_active and p.matches(context)]
        return sorted(matched, key=lambda p: p.priority, reverse=True)

    def evaluate(
        self,
        context: dict[str, Any],
    ) -> tuple[Optional[GovernanceAction], str, list[str]]:
        """Evaluate all policies and return the dominant action.

        Returns (action, reason, applied_policy_ids).

        Action may be None if no policy matches (→ default to REQUIRE_MANUAL).
        """
        applicable = self.get_applicable(context)
        if not applicable:
            return None, "No applicable policy — default: require manual review", []

        # Return action of first (highest-priority) matching policy
        dominant = applicable[0]
        applied_ids = [p.policy_id for p in applicable]
        return dominant.action, dominant.name, applied_ids

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total  = len(self._policies)
            active = sum(1 for p in self._policies.values() if p.is_active)
            by_type: dict[str, int] = {}
            for p in self._policies.values():
                k = p.policy_type.value
                by_type[k] = by_type.get(k, 0) + 1
        return {
            "total_policies":  total,
            "active_policies": active,
            "by_type":         by_type,
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_policy_manager() -> PolicyManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = PolicyManager()
    return _manager


def reset_policy_manager() -> None:
    global _manager
    with _lock:
        _manager = None
