"""
iios/infrastructure/security/policy_manager.py
===============================================
Policy-based authorization rules (RBAC and ABAC statement evaluation).
"""

from __future__ import annotations

import fnmatch
import logging
import threading
from typing import Any, Optional

from .security_constants import PolicyEffect, PolicyType, AccessDecision
from .security_exceptions import PolicyNotFoundError, PolicyEvaluationError
from .security_models import PolicyRecord, PolicyStatement, AccessRequest, AccessResult

__all__ = ["PolicyManager", "get_policy_manager", "reset_policy_manager"]

_LOG = logging.getLogger("iios.security.policy")
_mgr_lock = threading.Lock()
_manager: Optional["PolicyManager"] = None


class PolicyManager:
    """Thread-safe policy registry and evaluator.

    Supports RBAC (role-assignment-based) and ABAC (attribute-condition) policies.
    Evaluation follows a DENY-OVERRIDES model: any DENY statement wins.

    Usage::

        pm = get_policy_manager()
        pm.register(PolicyRecord(name="trader_policy", ...))
        result = pm.evaluate(AccessRequest(principal_id=..., action="trade:execute", resource="RELIANCE"))
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._policies: dict[str, PolicyRecord] = {}
        # principal_id → list of policy names
        self._principal_policies: dict[str, list[str]] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, policy: PolicyRecord, allow_override: bool = True) -> None:
        with self._lock:
            self._policies[policy.name] = policy
        _LOG.debug("Registered policy: %s", policy.name)

    def get(self, name: str) -> PolicyRecord:
        p = self.get_optional(name)
        if p is None:
            raise PolicyNotFoundError(
                f"Policy '{name}' not found",
                code="SEC-POL-001",
                context={"name": name},
            )
        return p

    def get_optional(self, name: str) -> Optional[PolicyRecord]:
        with self._lock:
            return self._policies.get(name)

    def delete(self, name: str) -> bool:
        with self._lock:
            return self._policies.pop(name, None) is not None

    def list_all(self) -> list[PolicyRecord]:
        with self._lock:
            return list(self._policies.values())

    # ── Policy attachment ─────────────────────────────────────────────────────

    def attach(self, principal_id: str, policy_name: str) -> None:
        """Attach a policy to a principal (user, service, etc.)."""
        self.get(policy_name)  # validate it exists
        with self._lock:
            policies = self._principal_policies.setdefault(principal_id, [])
            if policy_name not in policies:
                policies.append(policy_name)

    def detach(self, principal_id: str, policy_name: str) -> bool:
        with self._lock:
            policies = self._principal_policies.get(principal_id, [])
            if policy_name in policies:
                policies.remove(policy_name)
                return True
        return False

    def get_attached(self, principal_id: str) -> list[str]:
        with self._lock:
            return list(self._principal_policies.get(principal_id, []))

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, request: AccessRequest) -> AccessResult:
        """Evaluate policies attached to *request.principal_id*.

        Returns PERMIT if at least one ALLOW statement matches and no DENY matches.
        Returns DENY if any DENY statement matches.
        Returns NOT_APPLICABLE if no statements match.
        """
        with self._lock:
            policy_names = list(self._principal_policies.get(request.principal_id, []))
            policies = [self._policies[n] for n in policy_names if n in self._policies]

        if not policies:
            return AccessResult(
                decision=AccessDecision.NOT_APPLICABLE,
                principal_id=request.principal_id,
                action=request.action,
                resource=request.resource,
                reason="No policies attached",
            )

        allow_matched = False
        for policy in policies:
            for stmt in policy.statements:
                if not self._statement_matches(stmt, request):
                    continue
                if stmt.effect == PolicyEffect.DENY:
                    return AccessResult(
                        decision=AccessDecision.DENY,
                        principal_id=request.principal_id,
                        action=request.action,
                        resource=request.resource,
                        matched_policy=policy.name,
                        reason=f"Denied by policy '{policy.name}'",
                    )
                if stmt.effect == PolicyEffect.ALLOW:
                    allow_matched = True

        if allow_matched:
            return AccessResult(
                decision=AccessDecision.PERMIT,
                principal_id=request.principal_id,
                action=request.action,
                resource=request.resource,
                reason="Permitted by policy",
            )

        return AccessResult(
            decision=AccessDecision.NOT_APPLICABLE,
            principal_id=request.principal_id,
            action=request.action,
            resource=request.resource,
            reason="No matching statements",
        )

    def _statement_matches(self, stmt: PolicyStatement, request: AccessRequest) -> bool:
        """Return True if the statement's actions+resources match the request."""
        action_matches = any(
            self._glob_match(request.action, pattern)
            for pattern in stmt.actions
        )
        if not action_matches:
            return False

        resource_matches = any(
            self._glob_match(request.resource, pattern)
            for pattern in stmt.resources
        )
        if not resource_matches:
            return False

        # ABAC conditions
        if stmt.conditions:
            return self._evaluate_conditions(stmt.conditions, request)
        return True

    @staticmethod
    def _glob_match(value: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        return fnmatch.fnmatch(value, pattern)

    @staticmethod
    def _evaluate_conditions(conditions: dict[str, Any], request: AccessRequest) -> bool:
        """Simple ABAC condition evaluation.

        Supported operators: ``eq``, ``ne``, ``in``, ``not_in``.
        Keys are dotted paths like ``environment.time_of_day``.
        """
        for key, rule in conditions.items():
            value = PolicyManager._resolve_path(key, request)
            if isinstance(rule, dict):
                op = rule.get("op", "eq")
                expected = rule.get("value")
                if op == "eq" and value != expected:
                    return False
                elif op == "ne" and value == expected:
                    return False
                elif op == "in" and value not in expected:
                    return False
                elif op == "not_in" and value in expected:
                    return False
            else:
                # Simple equality
                if value != rule:
                    return False
        return True

    @staticmethod
    def _resolve_path(path: str, request: AccessRequest) -> Any:
        """Resolve dotted path against request attributes or environment."""
        parts = path.split(".", 1)
        namespace = parts[0]
        key = parts[1] if len(parts) > 1 else ""

        if namespace == "environment":
            return request.environment.get(key)
        if namespace == "attributes":
            return request.attributes.get(key)
        return None

    def reset(self) -> None:
        with self._lock:
            self._policies.clear()
            self._principal_policies.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_policy_manager() -> PolicyManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = PolicyManager()
        return _manager


def reset_policy_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
