"""
iios/infrastructure/security/identity_manager.py
=================================================
Central identity registry — manages all principals (users, services, systems).
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Optional

from .identity_provider import IdentityProvider, InMemoryIdentityProvider
from .principal import Principal, ANONYMOUS
from .security_constants import (
    IdentityStatus,
    PrincipalType,
    SYSTEM_PRINCIPAL_ID,
    ANONYMOUS_PRINCIPAL_ID,
)
from .security_exceptions import (
    IdentityNotFoundError,
    IdentityAlreadyExistsError,
    IdentityLockedError,
    IdentityInvalidError,
)
from .security_models import PrincipalRecord
from .system_identity import SystemIdentity, get_system_identity
from .user_identity import UserIdentity
from .service_identity import ServiceIdentity

__all__ = ["IdentityManager", "get_identity_manager", "reset_identity_manager"]

_LOG = logging.getLogger("iios.security.identity")
_mgr_lock = threading.Lock()
_manager: Optional["IdentityManager"] = None


class IdentityManager:
    """Thread-safe registry for all principal identities.

    Maintains an in-memory provider by default and supports additional
    pluggable providers (LDAP, database, etc.).

    Usage::

        mgr = get_identity_manager()
        user = mgr.create_user("alice", email="alice@example.com", roles=["trader"])
        found = mgr.get("user:alice-id")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._default_provider = InMemoryIdentityProvider("default")
        self._providers: list[IdentityProvider] = [self._default_provider]

        # Always register the system and anonymous principals
        self._default_provider.register(get_system_identity())
        self._default_provider.register(ANONYMOUS)

    # ── Provider management ───────────────────────────────────────────────────

    def add_provider(self, provider: IdentityProvider) -> None:
        with self._lock:
            self._providers.append(provider)

    def remove_provider(self, provider_name: str) -> bool:
        with self._lock:
            before = len(self._providers)
            self._providers = [p for p in self._providers if p.provider_name != provider_name]
            return len(self._providers) < before

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, principal: Principal, allow_override: bool = False) -> None:
        """Register a principal. Raises IdentityAlreadyExistsError if duplicate."""
        with self._lock:
            if not allow_override and self._default_provider.exists(principal.principal_id):
                raise IdentityAlreadyExistsError(
                    f"Principal '{principal.principal_id}' already registered",
                    code="SEC-ID-001",
                    context={"principal_id": principal.principal_id},
                )
            self._default_provider.register(principal)
            _LOG.debug("Registered principal %s (%s)", principal.principal_id, principal.principal_type.value)

    def get(self, principal_id: str) -> Principal:
        """Return the principal for *principal_id*; raises IdentityNotFoundError."""
        p = self.get_optional(principal_id)
        if p is None:
            raise IdentityNotFoundError(
                f"Principal '{principal_id}' not found",
                code="SEC-ID-002",
                context={"principal_id": principal_id},
            )
        return p

    def get_optional(self, principal_id: str) -> Optional[Principal]:
        with self._lock:
            for provider in reversed(self._providers):
                p = provider.find(principal_id)
                if p is not None:
                    return p
        return None

    def find_by_name(self, name: str, principal_type: Optional[PrincipalType] = None) -> Optional[Principal]:
        with self._lock:
            for provider in reversed(self._providers):
                p = provider.find_by_name(name, principal_type)
                if p is not None:
                    return p
        return None

    def exists(self, principal_id: str) -> bool:
        return self.get_optional(principal_id) is not None

    def unregister(self, principal_id: str) -> bool:
        """Remove a principal from the default provider."""
        if principal_id in (SYSTEM_PRINCIPAL_ID, ANONYMOUS_PRINCIPAL_ID):
            raise IdentityInvalidError(
                "Cannot unregister built-in principals",
                code="SEC-ID-003",
                context={"principal_id": principal_id},
            )
        with self._lock:
            return self._default_provider.unregister(principal_id)

    def list_all(self, principal_type: Optional[PrincipalType] = None) -> list[Principal]:
        with self._lock:
            seen: set[str] = set()
            result: list[Principal] = []
            for provider in self._providers:
                for p in provider.list_principals(principal_type):
                    if p.principal_id not in seen:
                        seen.add(p.principal_id)
                        result.append(p)
            return result

    # ── Factory helpers ────────────────────────────────────────────────────────

    def create_user(
        self,
        name: str,
        email: str = "",
        roles: Optional[list[str]] = None,
        principal_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> UserIdentity:
        """Create and register a new UserIdentity."""
        user = UserIdentity(
            principal_id=principal_id,
            name=name,
            email=email,
            roles=roles,
            attributes=attributes,
        )
        self.register(user)
        _LOG.info("Created user identity: %s (%s)", name, user.principal_id)
        return user

    def create_service(
        self,
        name: str,
        service_name: str = "",
        version: str = "1.0",
        roles: Optional[list[str]] = None,
        principal_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> ServiceIdentity:
        """Create and register a new ServiceIdentity."""
        svc = ServiceIdentity(
            principal_id=principal_id,
            name=name,
            service_name=service_name,
            version=version,
            roles=roles,
            attributes=attributes,
        )
        self.register(svc)
        _LOG.info("Created service identity: %s (%s)", name, svc.principal_id)
        return svc

    def create_system(
        self,
        extra_roles: Optional[list[str]] = None,
    ) -> SystemIdentity:
        """Return the process system identity (always the same singleton)."""
        return get_system_identity()

    # ── Locking ───────────────────────────────────────────────────────────────

    def lock_principal(self, principal_id: str, lockout_seconds: float = 900) -> None:
        p = self.get(principal_id)
        if isinstance(p, UserIdentity):
            import time
            p.status = IdentityStatus.LOCKED
            p.locked_until = time.time() + lockout_seconds
            _LOG.warning("Locked principal %s for %.0fs", principal_id, lockout_seconds)
        else:
            raise IdentityInvalidError(
                "Only UserIdentity can be locked",
                code="SEC-ID-004",
                context={"principal_id": principal_id},
            )

    def unlock_principal(self, principal_id: str) -> None:
        p = self.get(principal_id)
        if isinstance(p, UserIdentity):
            p.unlock()
            _LOG.info("Unlocked principal %s", principal_id)
        else:
            raise IdentityInvalidError(
                "Only UserIdentity can be unlocked",
                code="SEC-ID-005",
                context={"principal_id": principal_id},
            )

    # ── Count ─────────────────────────────────────────────────────────────────

    def count(self, principal_type: Optional[PrincipalType] = None) -> int:
        return len(self.list_all(principal_type))

    def reset(self) -> None:
        with self._lock:
            self._default_provider.clear()
            self._providers = [self._default_provider]
            self._default_provider.register(get_system_identity())
            self._default_provider.register(ANONYMOUS)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_identity_manager() -> IdentityManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = IdentityManager()
        return _manager


def reset_identity_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
