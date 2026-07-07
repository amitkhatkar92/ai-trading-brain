"""
iios/infrastructure/security/authentication_provider.py
=======================================================
Abstract authentication provider interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .security_constants import AuthMethod
from .security_models import AuthResult

__all__ = [
    "AuthenticationProvider",
    "PasswordAuthProvider",
    "ApiKeyAuthProvider",
    "TokenAuthProvider",
    "SystemAuthProvider",
]


class AuthenticationProvider(ABC):
    """Abstract interface for pluggable authentication mechanisms."""

    @property
    @abstractmethod
    def auth_method(self) -> AuthMethod:
        """The authentication method this provider handles."""

    @abstractmethod
    def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """Authenticate using the given credentials dict.

        Returns an AuthResult indicating success or failure.
        Never raises on auth failure — always returns AuthResult.FAILED.
        May raise on internal errors (infrastructure failures).
        """

    def supports(self, credentials: dict[str, Any]) -> bool:
        """Return True if this provider can handle the given credentials."""
        return self.auth_method.value in credentials or "method" in credentials


class PasswordAuthProvider(AuthenticationProvider):
    """Authenticates username+password credentials."""

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.PASSWORD

    def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        from .security_constants import AuthStatus
        from .credential_manager import get_credential_manager
        from .identity_manager import get_identity_manager
        from .security_exceptions import CredentialExpiredError, IdentityNotFoundError

        principal_id = credentials.get("principal_id", "")
        password = credentials.get("password", "")

        if not principal_id or not password:
            return AuthResult(
                status=AuthStatus.FAILED,
                message="principal_id and password are required",
            )

        try:
            identity_mgr = get_identity_manager()
            principal = identity_mgr.get_optional(principal_id)
            if principal is None:
                return AuthResult(status=AuthStatus.FAILED, message="Principal not found")
            if not principal.is_active:
                return AuthResult(status=AuthStatus.FAILED, message=f"Identity is {principal.status.value}")

            cred_mgr = get_credential_manager()
            ok = cred_mgr.verify_password(principal_id, password)
            if ok:
                return AuthResult(status=AuthStatus.SUCCESS, principal_id=principal_id)
            return AuthResult(status=AuthStatus.FAILED, message="Invalid credentials")

        except CredentialExpiredError:
            return AuthResult(status=AuthStatus.EXPIRED, principal_id=principal_id, message="Password expired")
        except Exception:
            return AuthResult(status=AuthStatus.FAILED, message="Authentication error")


class ApiKeyAuthProvider(AuthenticationProvider):
    """Authenticates API key credentials."""

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.API_KEY

    def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        from .security_constants import AuthStatus
        from .credential_manager import get_credential_manager

        api_key = credentials.get("api_key", "")
        if not api_key:
            return AuthResult(status=AuthStatus.FAILED, message="api_key is required")

        try:
            cred_mgr = get_credential_manager()
            principal_id = cred_mgr.verify_api_key(api_key)
            if principal_id:
                return AuthResult(status=AuthStatus.SUCCESS, principal_id=principal_id)
            return AuthResult(status=AuthStatus.FAILED, message="Invalid API key")
        except Exception:
            return AuthResult(status=AuthStatus.FAILED, message="API key verification error")


class TokenAuthProvider(AuthenticationProvider):
    """Authenticates HMAC-signed token credentials."""

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.TOKEN

    def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        from .security_constants import AuthStatus
        from .token_manager import get_token_manager

        token_str = credentials.get("token", "")
        if not token_str:
            return AuthResult(status=AuthStatus.FAILED, message="token is required")

        try:
            tmgr = get_token_manager()
            claims = tmgr.validate_raw(token_str)
            principal_id = claims.get("sub", "")
            if not principal_id:
                return AuthResult(status=AuthStatus.FAILED, message="Token missing subject")
            return AuthResult(status=AuthStatus.SUCCESS, principal_id=principal_id)
        except Exception as exc:
            return AuthResult(status=AuthStatus.FAILED, message=str(exc))


class SystemAuthProvider(AuthenticationProvider):
    """Internal system-to-system authentication (no credentials needed)."""

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.SYSTEM

    def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        from .security_constants import AuthStatus, SYSTEM_PRINCIPAL_ID
        return AuthResult(status=AuthStatus.SUCCESS, principal_id=SYSTEM_PRINCIPAL_ID)
