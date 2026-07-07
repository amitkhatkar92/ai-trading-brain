"""
iios/infrastructure/security/access_controller.py
===================================================
Unified RBAC + ABAC access control engine.
Combines role-based checks with policy evaluation.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .identity_manager import get_identity_manager
from .policy_manager import get_policy_manager
from .role_manager import get_role_manager
from .security_constants import AccessDecision, SYSTEM_PRINCIPAL_ID, SUPER_ADMIN_ROLE
from .security_models import AccessRequest, AccessResult

__all__ = ["AccessController", "get_access_controller", "reset_access_controller"]

_LOG = logging.getLogger("iios.security.access")
_mgr_lock = threading.Lock()
_controller: Optional["AccessController"] = None


class AccessController:
    """RBAC + ABAC access control engine.

    Decision flow:
    1. System principal → always PERMIT.
    2. Principal has super_admin role → PERMIT.
    3. Check RBAC: does any of the principal's roles include the permission?
    4. Check ABAC policies attached to the principal.
    5. NOT_APPLICABLE → configurable default (deny-by-default = True).

    Usage::

        ac = get_access_controller()
        result = ac.check("user:alice", "trade:execute", "RELIANCE")
        if not result.is_permitted:
            raise AccessDeniedError(...)
    """

    def __init__(self, deny_by_default: bool = True) -> None:
        self._deny_by_default = deny_by_default
        self._lock = threading.RLock()

    def check(
        self,
        principal_id: str,
        action: str,
        resource: str,
        attributes: Optional[dict[str, Any]] = None,
        environment: Optional[dict[str, Any]] = None,
    ) -> AccessResult:
        """Perform a full access control check.

        Returns an AccessResult with the final decision.
        """
        request = AccessRequest(
            principal_id=principal_id,
            action=action,
            resource=resource,
            attributes=attributes or {},
            environment=environment or {},
        )

        # System principal bypasses all checks
        if principal_id == SYSTEM_PRINCIPAL_ID:
            return AccessResult(
                decision=AccessDecision.PERMIT,
                principal_id=principal_id,
                action=action,
                resource=resource,
                reason="System principal — unrestricted",
            )

        # Resolve principal roles
        idm = get_identity_manager()
        principal = idm.get_optional(principal_id)
        if principal is None:
            return AccessResult(
                decision=AccessDecision.DENY,
                principal_id=principal_id,
                action=action,
                resource=resource,
                reason="Principal not found",
            )

        roles = list(getattr(principal, "_roles", [])) if hasattr(principal, "_roles") else []

        # RBAC check
        rbac_result = self._rbac_check(principal_id, roles, action)
        if rbac_result.decision == AccessDecision.DENY:
            return rbac_result
        if rbac_result.decision == AccessDecision.PERMIT:
            # RBAC granted — still check policies for DENY overrides
            policy_result = get_policy_manager().evaluate(request)
            if policy_result.decision == AccessDecision.DENY:
                return policy_result
            return rbac_result

        # ABAC policy check
        policy_result = get_policy_manager().evaluate(request)
        if policy_result.decision in (AccessDecision.PERMIT, AccessDecision.DENY):
            return policy_result

        # NOT_APPLICABLE — use default
        if self._deny_by_default:
            return AccessResult(
                decision=AccessDecision.DENY,
                principal_id=principal_id,
                action=action,
                resource=resource,
                reason="No rule matched — deny by default",
            )
        return AccessResult(
            decision=AccessDecision.PERMIT,
            principal_id=principal_id,
            action=action,
            resource=resource,
            reason="No rule matched — permit by default",
        )

    def _rbac_check(self, principal_id: str, roles: list[str], action: str) -> AccessResult:
        """Return PERMIT if any role grants action, DENY if any explicitly denies, else NOT_APPLICABLE."""
        rm = get_role_manager()

        for role_name in roles:
            if role_name == SUPER_ADMIN_ROLE or rm.has_permission(role_name, action):
                return AccessResult(
                    decision=AccessDecision.PERMIT,
                    principal_id=principal_id,
                    action=action,
                    matched_role=role_name,
                    reason=f"Permitted by role '{role_name}'",
                )

        return AccessResult(
            decision=AccessDecision.NOT_APPLICABLE,
            principal_id=principal_id,
            action=action,
            reason="No matching role",
        )

    def is_permitted(
        self,
        principal_id: str,
        action: str,
        resource: str,
        attributes: Optional[dict[str, Any]] = None,
        environment: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Convenience method — returns bool."""
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
        from .security_exceptions import AccessDeniedError
        result = self.check(principal_id, action, resource, attributes, environment)
        if not result.is_permitted:
            raise AccessDeniedError(
                f"Access denied: principal={principal_id} action={action} resource={resource}",
                code="SEC-AC-001",
                context={
                    "principal_id": principal_id,
                    "action": action,
                    "resource": resource,
                    "reason": result.reason,
                },
            )
        return result

    def reset(self) -> None:
        pass  # stateless — delegated to sub-managers


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_access_controller() -> AccessController:
    global _controller
    with _mgr_lock:
        if _controller is None:
            _controller = AccessController()
        return _controller


def reset_access_controller() -> None:
    global _controller
    with _mgr_lock:
        _controller = None
