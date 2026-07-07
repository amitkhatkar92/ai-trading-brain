"""
iios/infrastructure/security/authorization_manager.py
======================================================
Authorization façade combining RBAC, ABAC, and policy evaluation.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .access_controller import get_access_controller
from .permission_manager import get_permission_manager
from .policy_manager import get_policy_manager
from .role_manager import get_role_manager
from .security_constants import AccessDecision
from .security_exceptions import AccessDeniedError
from .security_models import AccessRequest, AccessResult, PolicyRecord, PolicyStatement
from .security_constants import PolicyEffect

__all__ = ["AuthorizationManager", "get_authorization_manager", "reset_authorization_manager"]

_LOG = logging.getLogger("iios.security.authz")
_mgr_lock = threading.Lock()
_manager: Optional["AuthorizationManager"] = None


class AuthorizationManager:
    """High-level authorization façade.

    Provides the primary API for all authorization checks in IIOS.
    Wraps AccessController, RoleManager, PermissionManager, and PolicyManager.

    Usage::

        authz = get_authorization_manager()
        authz.grant_role("user:alice", "trader")
        authz.require("user:alice", "trade:execute", "RELIANCE")  # raises on deny
        ok = authz.is_permitted("user:alice", "risk:override", "*")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    # ── Role assignment ───────────────────────────────────────────────────────

    def grant_role(self, principal_id: str, role_name: str) -> None:
        """Grant *role_name* to a principal."""
        from .identity_manager import get_identity_manager
        rm = get_role_manager()
        rm.get(role_name)  # validate role exists

        idm = get_identity_manager()
        p = idm.get(principal_id)
        if hasattr(p, "add_role"):
            p.add_role(role_name)
            _LOG.info("Granted role '%s' to %s", role_name, principal_id)
        else:
            _LOG.warning("Cannot grant role to principal type %s", type(p).__name__)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        """Revoke *role_name* from a principal."""
        from .identity_manager import get_identity_manager
        idm = get_identity_manager()
        p = idm.get(principal_id)
        if hasattr(p, "remove_role"):
            p.remove_role(role_name)
            _LOG.info("Revoked role '%s' from %s", role_name, principal_id)

    def get_roles(self, principal_id: str) -> list[str]:
        """Return the roles assigned to *principal_id*."""
        from .identity_manager import get_identity_manager
        p = get_identity_manager().get(principal_id)
        return list(getattr(p, "_roles", []))

    # ── Permission checks ─────────────────────────────────────────────────────

    def check(
        self,
        principal_id: str,
        action: str,
        resource: str,
        attributes: Optional[dict[str, Any]] = None,
        environment: Optional[dict[str, Any]] = None,
    ) -> AccessResult:
        """Return an AccessResult for the given request."""
        result = get_access_controller().check(
            principal_id, action, resource, attributes, environment
        )
        if result.decision == AccessDecision.DENY:
            _LOG.warning("Access DENIED: %s → %s on %s (%s)", principal_id, action, resource, result.reason)
        else:
            _LOG.debug("Access PERMIT: %s → %s on %s", principal_id, action, resource)
        return result

    def is_permitted(
        self,
        principal_id: str,
        action: str,
        resource: str,
        attributes: Optional[dict[str, Any]] = None,
        environment: Optional[dict[str, Any]] = None,
    ) -> bool:
        return self.check(principal_id, action, resource, attributes, environment).is_permitted

    def require(
        self,
        principal_id: str,
        action: str,
        resource: str,
        attributes: Optional[dict[str, Any]] = None,
        environment: Optional[dict[str, Any]] = None,
    ) -> AccessResult:
        """Like check(), but raises AccessDeniedError if denied."""
        result = self.check(principal_id, action, resource, attributes, environment)
        if not result.is_permitted:
            raise AccessDeniedError(
                f"Access denied: {principal_id} → {action} on {resource}",
                code="SEC-AUTHZ-001",
                context={
                    "principal_id": principal_id,
                    "action": action,
                    "resource": resource,
                    "reason": result.reason,
                },
            )
        return result

    # ── Policy helpers ────────────────────────────────────────────────────────

    def create_allow_policy(
        self,
        name: str,
        actions: list[str],
        resources: list[str],
        conditions: Optional[dict[str, Any]] = None,
    ) -> PolicyRecord:
        """Create and register a simple ALLOW policy."""
        policy = PolicyRecord(
            name=name,
            statements=[
                PolicyStatement(
                    effect=PolicyEffect.ALLOW,
                    actions=actions,
                    resources=resources,
                    conditions=conditions or {},
                )
            ],
        )
        get_policy_manager().register(policy)
        return policy

    def attach_policy(self, principal_id: str, policy_name: str) -> None:
        get_policy_manager().attach(principal_id, policy_name)

    def detach_policy(self, principal_id: str, policy_name: str) -> bool:
        return get_policy_manager().detach(principal_id, policy_name)

    # ── Summary ───────────────────────────────────────────────────────────────

    def effective_permissions(self, principal_id: str) -> set[str]:
        """Return the union of all permissions from all assigned roles."""
        from .identity_manager import get_identity_manager
        p = get_identity_manager().get_optional(principal_id)
        if p is None:
            return set()
        roles = list(getattr(p, "_roles", []))
        rm = get_role_manager()
        perms: set[str] = set()
        for role_name in roles:
            perms |= rm.resolve_permissions(role_name)
        return perms

    def reset(self) -> None:
        pass  # stateless — delegates to sub-managers


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_authorization_manager() -> AuthorizationManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = AuthorizationManager()
        return _manager


def reset_authorization_manager() -> None:
    global _manager
    with _mgr_lock:
        _manager = None
