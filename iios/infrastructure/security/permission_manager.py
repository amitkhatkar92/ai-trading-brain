"""
iios/infrastructure/security/permission_manager.py
===================================================
Registry and validation for named permissions (resource:action pairs).
"""

from __future__ import annotations

import fnmatch
import logging
import threading
from typing import Optional

from .security_constants import PermissionEffect
from .security_exceptions import PermissionNotFoundError
from .security_models import PermissionRecord

__all__ = ["PermissionManager", "get_permission_manager", "reset_permission_manager"]

_LOG = logging.getLogger("iios.security.permission")
_mgr_lock = threading.Lock()
_manager: Optional["PermissionManager"] = None


class PermissionManager:
    """Thread-safe registry of named permissions.

    Permission names follow the ``resource:action`` convention.
    Wildcard matching (``orders:*``, ``*:read``) is supported in checks.

    Usage::

        pm = get_permission_manager()
        pm.register(PermissionRecord(name="orders:read", resource="orders", action="read"))
        pm.has("orders:read")   # True
        pm.matches("orders:read", "orders:*")  # True
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._permissions: dict[str, PermissionRecord] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            ("*", "*", "*"),
            ("iios:admin", "iios", "admin"),
            ("iios:read", "iios", "read"),
            ("iios:write", "iios", "write"),
            ("trade:execute", "trade", "execute"),
            ("trade:read", "trade", "read"),
            ("risk:read", "risk", "read"),
            ("risk:override", "risk", "override"),
            ("orders:read", "orders", "read"),
            ("orders:write", "orders", "write"),
            ("orders:cancel", "orders", "cancel"),
            ("portfolio:read", "portfolio", "read"),
            ("portfolio:write", "portfolio", "write"),
            ("secrets:read", "secrets", "read"),
            ("secrets:write", "secrets", "write"),
            ("audit:read", "audit", "read"),
        ]
        for name, resource, action in defaults:
            self._permissions[name] = PermissionRecord(
                name=name, resource=resource, action=action,
                effect=PermissionEffect.ALLOW,
            )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, perm: PermissionRecord, allow_override: bool = True) -> None:
        with self._lock:
            self._permissions[perm.name] = perm
        _LOG.debug("Registered permission: %s", perm.name)

    def get(self, name: str) -> PermissionRecord:
        p = self.get_optional(name)
        if p is None:
            raise PermissionNotFoundError(
                f"Permission '{name}' not found",
                code="SEC-PERM-001",
                context={"name": name},
            )
        return p

    def get_optional(self, name: str) -> Optional[PermissionRecord]:
        with self._lock:
            return self._permissions.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._permissions

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._permissions.pop(name, None) is not None

    def list_all(self) -> list[PermissionRecord]:
        with self._lock:
            return list(self._permissions.values())

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._permissions.keys())

    # ── Pattern matching ──────────────────────────────────────────────────────

    def matches(self, permission_name: str, pattern: str) -> bool:
        """Return True if *permission_name* matches *pattern* (fnmatch wildcard)."""
        if pattern == "*":
            return True
        return fnmatch.fnmatch(permission_name, pattern)

    def find_matching(self, pattern: str) -> list[PermissionRecord]:
        """Return all permissions matching *pattern*."""
        with self._lock:
            return [p for n, p in self._permissions.items() if self.matches(n, pattern)]

    def reset(self) -> None:
        with self._lock:
            self._permissions.clear()
            self._register_defaults()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_permission_manager() -> PermissionManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = PermissionManager()
        return _manager


def reset_permission_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
