"""
iios/infrastructure/security/authentication_manager.py
=======================================================
Central authentication gateway — delegates to registered providers,
records login attempts, manages lockout, and issues sessions/tokens.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .authentication_provider import (
    AuthenticationProvider,
    PasswordAuthProvider,
    ApiKeyAuthProvider,
    TokenAuthProvider,
    SystemAuthProvider,
)
from .identity_manager import get_identity_manager
from .security_constants import (
    AuthMethod,
    AuthStatus,
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_DURATION_SECONDS,
)
from .security_exceptions import AccountLockedError, AuthenticationError
from .security_models import AuthResult
from .session_manager import get_session_manager
from .token_manager_new import get_token_manager
from .user_identity import UserIdentity

__all__ = ["AuthenticationManager", "get_authentication_manager", "reset_authentication_manager"]

_LOG = logging.getLogger("iios.security.auth")
_mgr_lock = threading.Lock()
_manager: Optional["AuthenticationManager"] = None


class AuthenticationManager:
    """Central authentication gateway.

    Registers authentication providers, delegates credential validation,
    enforces lockout, issues sessions and tokens on success.

    Usage::

        mgr = get_authentication_manager()
        result = mgr.authenticate({"principal_id": "user:alice", "password": "..."})
        if result.is_success:
            session_id = result.session_id
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: dict[AuthMethod, AuthenticationProvider] = {}

        # Register built-in providers
        for p in (PasswordAuthProvider(), ApiKeyAuthProvider(), TokenAuthProvider(), SystemAuthProvider()):
            self._providers[p.auth_method] = p

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: AuthenticationProvider, override: bool = False) -> None:
        with self._lock:
            if provider.auth_method in self._providers and not override:
                raise AuthenticationError(
                    f"Provider for {provider.auth_method.value} already registered",
                    code="SEC-AUTH-001",
                )
            self._providers[provider.auth_method] = provider

    def get_provider(self, method: AuthMethod) -> Optional[AuthenticationProvider]:
        with self._lock:
            return self._providers.get(method)

    # ── Main authenticate ─────────────────────────────────────────────────────

    def authenticate(
        self,
        credentials: dict[str, Any],
        method: Optional[AuthMethod] = None,
        issue_session: bool = True,
        issue_token: bool = False,
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuthResult:
        """Authenticate the given credentials.

        Automatically selects the method from credentials dict if not specified.
        On success optionally creates a session and/or issues a token.

        Args:
            credentials:  Dict with auth data (``password``, ``api_key``, ``token``, etc.)
            method:       Force a specific AuthMethod.
            issue_session: Create a session on success.
            issue_token:  Issue an access token on success.
            ip_address:   Source IP for the session.
            user_agent:   Client UA string for the session.
        """
        if method is None:
            method = self._detect_method(credentials)

        provider = self._providers.get(method)
        if provider is None:
            return AuthResult(
                status=AuthStatus.FAILED,
                message=f"No provider for method '{method.value}'",
            )

        # Check lockout BEFORE attempting authentication
        principal_id = credentials.get("principal_id", "")
        if principal_id:
            lock_result = self._check_lockout(principal_id)
            if lock_result is not None:
                return lock_result

        result = provider.authenticate(credentials)

        # Record success/failure on the identity
        if principal_id:
            self._record_attempt(result, principal_id)

        if not result.is_success:
            _LOG.warning("Authentication failed: method=%s principal=%s", method.value, principal_id or "?")
            return result

        _LOG.info("Authentication success: method=%s principal=%s", method.value, result.principal_id)

        # Issue session
        if issue_session and result.principal_id:
            session = get_session_manager().create(
                principal_id=result.principal_id,
                auth_method=method,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            result.session_id = session.session_id

        # Issue token
        if issue_token and result.principal_id:
            token_str = get_token_manager().issue(
                principal_id=result.principal_id,
                extra_claims={"method": method.value},
            )
            result.token = token_str

        return result

    # ── Logout ────────────────────────────────────────────────────────────────

    def logout(self, session_id: str, principal_id: Optional[str] = None) -> bool:
        """Terminate a session and revoke any associated tokens."""
        sess_mgr = get_session_manager()
        ok = sess_mgr.terminate(session_id)
        if principal_id:
            get_token_manager().revoke_all(principal_id)
        return ok

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _detect_method(self, credentials: dict[str, Any]) -> AuthMethod:
        if "api_key" in credentials:
            return AuthMethod.API_KEY
        if "token" in credentials:
            return AuthMethod.TOKEN
        if "password" in credentials:
            return AuthMethod.PASSWORD
        return AuthMethod.SYSTEM

    def _check_lockout(self, principal_id: str) -> Optional[AuthResult]:
        """Return a LOCKED AuthResult if the principal is locked, else None."""
        idm = get_identity_manager()
        p = idm.get_optional(principal_id)
        if p is not None and hasattr(p, "is_locked") and p.is_locked:
            raise AccountLockedError(
                f"Account '{principal_id}' is locked",
                code="SEC-AUTH-002",
                context={"principal_id": principal_id},
            )
        return None

    def _record_attempt(self, result: AuthResult, principal_id: str) -> None:
        """Update the UserIdentity with success/failure bookkeeping."""
        idm = get_identity_manager()
        p = idm.get_optional(principal_id)
        if p is None or not isinstance(p, UserIdentity):
            return
        if result.is_success:
            p.record_login()
        else:
            was_locked = p.record_failure(
                max_failures=MAX_LOGIN_ATTEMPTS,
                lockout_seconds=float(LOCKOUT_DURATION_SECONDS),
            )
            if was_locked:
                _LOG.warning("Account locked: %s after %d failures", principal_id, MAX_LOGIN_ATTEMPTS)

    def reset(self) -> None:
        with self._lock:
            self._providers.clear()
            for p in (PasswordAuthProvider(), ApiKeyAuthProvider(), TokenAuthProvider(), SystemAuthProvider()):
                self._providers[p.auth_method] = p


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_authentication_manager() -> AuthenticationManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = AuthenticationManager()
        return _manager


def reset_authentication_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
