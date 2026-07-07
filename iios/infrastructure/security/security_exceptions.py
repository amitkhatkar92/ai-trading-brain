"""
iios/infrastructure/security/security_exceptions.py
=====================================================
Security exception hierarchy for the IIOS Security Framework.
Extends the base SecurityError from infrastructure_exceptions.
"""

from __future__ import annotations

from ..infrastructure_exceptions import SecurityError, TokenError, EncryptionError

__all__ = [
    # Re-exports from infrastructure
    "SecurityError",
    "TokenError",
    "EncryptionError",
    # Identity
    "IdentityError",
    "IdentityNotFoundError",
    "IdentityAlreadyExistsError",
    "IdentityLockedError",
    "IdentityExpiredError",
    "IdentityInvalidError",
    # Authentication
    "AuthenticationError",
    "AuthenticationFailedError",
    "InvalidCredentialError",
    "CredentialExpiredError",
    "AccountLockedError",
    "MFARequiredError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "SessionInvalidError",
    # Authorization
    "AuthorizationError",
    "AccessDeniedError",
    "PermissionNotFoundError",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PolicyError",
    "PolicyNotFoundError",
    "PolicyEvaluationError",
    # Encryption
    "KeyError_",
    "KeyNotFoundError",
    "KeyRotationError",
    "KeyRevocationError",
    "SignatureError",
    "SignatureInvalidError",
    "CertificateError",
    "CertificateExpiredError",
    "CertificateInvalidError",
    # Secrets
    "SecretError",
    "SecretNotFoundError",
    "SecretAlreadyExistsError",
    "SecretAccessDeniedError",
    "SecretRotationError",
    # Integrity
    "IntegrityError",
    "TamperDetectedError",
    "ChecksumMismatchError",
    # Audit
    "AuditError",
    "AuditWriteError",
]


# ── Identity ──────────────────────────────────────────────────────────────────

class IdentityError(SecurityError):
    """General identity management error."""

class IdentityNotFoundError(IdentityError):
    """Principal identity not found in registry."""

class IdentityAlreadyExistsError(IdentityError):
    """Principal with this ID already registered."""

class IdentityLockedError(IdentityError):
    """Identity is locked (too many failed attempts)."""

class IdentityExpiredError(IdentityError):
    """Identity has expired."""

class IdentityInvalidError(IdentityError):
    """Identity is malformed or in an invalid state."""


# ── Authentication ────────────────────────────────────────────────────────────

class AuthenticationError(SecurityError):
    """General authentication failure."""

class AuthenticationFailedError(AuthenticationError):
    """Credentials valid but authentication denied by policy."""

class InvalidCredentialError(AuthenticationError):
    """Provided credentials are incorrect."""

class CredentialExpiredError(AuthenticationError):
    """Credentials have expired and must be renewed."""

class AccountLockedError(AuthenticationError):
    """Account locked after too many failed attempts."""

class MFARequiredError(AuthenticationError):
    """Multi-factor authentication step required."""

class SessionError(SecurityError):
    """General session error."""

class SessionNotFoundError(SessionError):
    """Session ID not found."""

class SessionExpiredError(SessionError):
    """Session has timed out."""

class SessionInvalidError(SessionError):
    """Session is invalid or tampered."""


# ── Authorization ─────────────────────────────────────────────────────────────

class AuthorizationError(SecurityError):
    """General authorisation failure."""

class AccessDeniedError(AuthorizationError):
    """Principal does not have permission to perform the action."""

class PermissionNotFoundError(AuthorizationError):
    """Permission descriptor not found in registry."""

class RoleNotFoundError(AuthorizationError):
    """Role not found in registry."""

class RoleAlreadyExistsError(AuthorizationError):
    """Role with this name already registered."""

class PolicyError(AuthorizationError):
    """General policy error."""

class PolicyNotFoundError(PolicyError):
    """Policy not found in registry."""

class PolicyEvaluationError(PolicyError):
    """Policy evaluation raised an unexpected error."""


# ── Encryption / Keys ─────────────────────────────────────────────────────────

# Renamed to avoid shadowing built-in KeyError
class KeyError_(SecurityError):           # noqa: N818
    """General encryption key error."""

class KeyNotFoundError(KeyError_):
    """Encryption key with given ID not found."""

class KeyRotationError(KeyError_):
    """Key rotation operation failed."""

class KeyRevocationError(KeyError_):
    """Key revocation operation failed."""

class SignatureError(SecurityError):
    """General digital signature error."""

class SignatureInvalidError(SignatureError):
    """Signature verification failed — data may be tampered."""

class CertificateError(SecurityError):
    """General certificate error."""

class CertificateExpiredError(CertificateError):
    """Certificate has expired."""

class CertificateInvalidError(CertificateError):
    """Certificate is invalid or untrusted."""


# ── Secrets ───────────────────────────────────────────────────────────────────

class SecretError(SecurityError):
    """General secrets management error."""

class SecretNotFoundError(SecretError):
    """Secret with given path/name not found."""

class SecretAlreadyExistsError(SecretError):
    """Secret with this name already registered."""

class SecretAccessDeniedError(SecretError):
    """Caller does not have access to this secret."""

class SecretRotationError(SecretError):
    """Secret rotation failed."""


# ── Integrity ─────────────────────────────────────────────────────────────────

class IntegrityError(SecurityError):
    """General integrity verification error."""

class TamperDetectedError(IntegrityError):
    """Data has been tampered — checksum/signature mismatch."""

class ChecksumMismatchError(IntegrityError):
    """Checksum does not match the expected value."""


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditError(SecurityError):
    """General audit subsystem error."""

class AuditWriteError(AuditError):
    """Failed to persist an audit record."""
