"""
iios/infrastructure/security/security_registry.py
==================================================
Central registry of security components — single place to resolve any
security manager or provider within the IIOS framework.
"""

from __future__ import annotations

import threading
from typing import Any, Optional, Type, TypeVar

from .security_exceptions import SecurityError

__all__ = ["SecurityRegistry", "get_security_registry", "reset_security_registry"]

_T = TypeVar("_T")

_reg_lock = threading.Lock()
_registry: Optional["SecurityRegistry"] = None


class SecurityRegistry:
    """Central registry for all security subsystem components.

    Provides a single place to look up any security manager, provider, or
    configuration object registered with the framework.

    Usage::

        reg = get_security_registry()
        reg.register("identity_manager", get_identity_manager())
        idm = reg.resolve("identity_manager")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._components: dict[str, Any] = {}
        self._auto_register_defaults()

    def _auto_register_defaults(self) -> None:
        """Register all standard security managers lazily (on first resolve)."""
        # Lazy registration: store factory callables for on-demand creation
        from .identity_manager import get_identity_manager
        from .authentication_manager import get_authentication_manager
        from .authorization_manager import get_authorization_manager
        from .credential_manager import get_credential_manager
        from .session_manager import get_session_manager
        from .token_manager_new import get_token_manager
        from .permission_manager import get_permission_manager
        from .role_manager import get_role_manager
        from .policy_manager import get_policy_manager
        from .access_controller import get_access_controller
        from .encryption_manager import get_encryption_manager
        from .key_manager import get_key_manager
        from .certificate_manager import get_certificate_manager
        from .crypto_provider import get_crypto_provider
        from .secret_manager import get_secret_manager
        from .audit_manager import get_audit_manager
        from .audit_recorder import get_audit_recorder
        from .integrity_manager import get_integrity_manager
        from .tamper_detector import get_tamper_detector
        from .security_context import get_security_context

        self._factories: dict[str, Any] = {
            "identity_manager": get_identity_manager,
            "authentication_manager": get_authentication_manager,
            "authorization_manager": get_authorization_manager,
            "credential_manager": get_credential_manager,
            "session_manager": get_session_manager,
            "token_manager": get_token_manager,
            "permission_manager": get_permission_manager,
            "role_manager": get_role_manager,
            "policy_manager": get_policy_manager,
            "access_controller": get_access_controller,
            "encryption_manager": get_encryption_manager,
            "key_manager": get_key_manager,
            "certificate_manager": get_certificate_manager,
            "crypto_provider": get_crypto_provider,
            "secret_manager": get_secret_manager,
            "audit_manager": get_audit_manager,
            "audit_recorder": get_audit_recorder,
            "integrity_manager": get_integrity_manager,
            "tamper_detector": get_tamper_detector,
            "security_context": get_security_context,
        }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, name: str, component: Any, override: bool = True) -> None:
        with self._lock:
            if not override and name in self._components:
                raise SecurityError(
                    f"Component '{name}' already registered",
                    code="SEC-REG-001",
                    context={"name": name},
                )
            self._components[name] = component

    def resolve(self, name: str) -> Any:
        """Resolve a component by name. Auto-creates from factory if not yet instantiated."""
        with self._lock:
            if name in self._components:
                return self._components[name]
            factory = self._factories.get(name)
            if factory is not None:
                instance = factory()
                self._components[name] = instance
                return instance
        raise SecurityError(
            f"Security component '{name}' not registered",
            code="SEC-REG-002",
            context={"name": name},
        )

    def resolve_typed(self, name: str, expected_type: Type[_T]) -> _T:
        """Resolve and type-check a component."""
        component = self.resolve(name)
        if not isinstance(component, expected_type):
            raise SecurityError(
                f"Component '{name}' is {type(component).__name__}, expected {expected_type.__name__}",
                code="SEC-REG-003",
            )
        return component

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._components or name in self._factories

    def list_registered(self) -> list[str]:
        with self._lock:
            return list(set(list(self._components.keys()) + list(self._factories.keys())))

    def unregister(self, name: str) -> bool:
        with self._lock:
            removed = self._components.pop(name, None) is not None
            self._factories.pop(name, None)
            return removed

    def reset(self) -> None:
        with self._lock:
            self._components.clear()
            self._auto_register_defaults()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_security_registry() -> SecurityRegistry:
    global _registry
    with _reg_lock:
        if _registry is None:
            _registry = SecurityRegistry()
        return _registry


def reset_security_registry() -> None:
    global _registry
    with _reg_lock:
        if _registry is not None:
            _registry.reset()
        _registry = None
