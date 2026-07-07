"""
iios/infrastructure/security/__init__.py
=========================================
IIOS Security Framework — complete public API.
"""

from __future__ import annotations

# ── Legacy exports (preserved) ──────────────────────────────────────────────
from .token_manager import TokenManager
from .encryption import SymmetricEncryption, generate_key

# ── Constants ────────────────────────────────────────────────────────────────
from .security_constants import (
    PrincipalType, IdentityStatus, AuthMethod, AuthStatus,
    TokenType, TokenStatus, SessionStatus, CredentialType,
    PermissionEffect, PolicyEffect, PolicyType, AccessDecision,
    EncryptionAlgorithm, HashAlgorithm, KeyType, KeyStatus,
    SecretType, SecretStatus, AuditEventType, AuditSeverity,
    TLSVersion, CertificateType,
    DEFAULT_TOKEN_TTL, DEFAULT_SESSION_TTL, DEFAULT_KEY_ROTATION_DAYS,
    MAX_LOGIN_ATTEMPTS, MIN_PASSWORD_LENGTH, API_KEY_LENGTH_BYTES,
    SYSTEM_PRINCIPAL_ID, ANONYMOUS_PRINCIPAL_ID, SUPER_ADMIN_ROLE,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .security_exceptions import (
    SecurityError, TokenError, EncryptionError,
    IdentityError, IdentityNotFoundError, IdentityAlreadyExistsError,
    IdentityLockedError, IdentityExpiredError, IdentityInvalidError,
    AuthenticationError, AuthenticationFailedError, InvalidCredentialError,
    CredentialExpiredError, AccountLockedError, MFARequiredError,
    SessionError, SessionNotFoundError, SessionExpiredError, SessionInvalidError,
    AuthorizationError, AccessDeniedError, PermissionNotFoundError,
    RoleNotFoundError, RoleAlreadyExistsError, PolicyError,
    PolicyNotFoundError, PolicyEvaluationError,
    KeyError_, KeyNotFoundError, KeyRotationError, KeyRevocationError,
    SignatureError, SignatureInvalidError,
    CertificateError, CertificateExpiredError, CertificateInvalidError,
    SecretError, SecretNotFoundError, SecretAlreadyExistsError,
    SecretAccessDeniedError, SecretRotationError,
    IntegrityError, TamperDetectedError, ChecksumMismatchError,
    AuditError, AuditWriteError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .security_models import (
    PrincipalRecord, TokenRecord, SessionRecord, CredentialRecord, AuthResult,
    PermissionRecord, RoleRecord, PolicyStatement, PolicyRecord,
    AccessRequest, AccessResult,
    KeyRecord, CertificateRecord, SignedPayload, IntegrityChecksum,
    SecretRecord, SecretVersion,
    AuditRecord, SecurityEvent,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .security_context import (
    SecurityContext, get_security_context, reset_security_context,
    current_principal_id, current_session_id, security_scope, system_scope,
)

# ── Identity ──────────────────────────────────────────────────────────────────
from .principal import Principal, AnonymousPrincipal, ANONYMOUS
from .user_identity import UserIdentity
from .service_identity import ServiceIdentity
from .system_identity import SystemIdentity, get_system_identity
from .identity_provider import IdentityProvider, InMemoryIdentityProvider
from .identity_manager import IdentityManager, get_identity_manager, reset_identity_manager

# ── Authentication ────────────────────────────────────────────────────────────
from .authentication_provider import (
    AuthenticationProvider, PasswordAuthProvider, ApiKeyAuthProvider,
    TokenAuthProvider, SystemAuthProvider,
)
from .credential_manager import CredentialManager, get_credential_manager, reset_credential_manager
from .session_manager import SessionManager, get_session_manager, reset_session_manager
from .token_manager_new import SecurityTokenManager, get_token_manager, reset_token_manager
from .authentication_manager import AuthenticationManager, get_authentication_manager, reset_authentication_manager

# ── Authorization ─────────────────────────────────────────────────────────────
from .permission_manager import PermissionManager, get_permission_manager, reset_permission_manager
from .role_manager import RoleManager, get_role_manager, reset_role_manager
from .policy_manager import PolicyManager, get_policy_manager, reset_policy_manager
from .access_controller import AccessController, get_access_controller, reset_access_controller
from .authorization_manager import AuthorizationManager, get_authorization_manager, reset_authorization_manager

# ── Encryption ────────────────────────────────────────────────────────────────
from .crypto_provider import CryptoProvider, StdlibCryptoProvider, FernetCryptoProvider, get_crypto_provider, reset_crypto_provider
from .key_manager import KeyManager, get_key_manager, reset_key_manager
from .certificate_manager import CertificateManager, get_certificate_manager, reset_certificate_manager
from .encryption_manager import EncryptionManager, get_encryption_manager, reset_encryption_manager

# ── Secrets ───────────────────────────────────────────────────────────────────
from .secret_store import SecretStore
from .vault_provider import VaultProvider, InMemoryVaultProvider, EnvironmentVaultProvider
from .secret_manager import SecretManager, get_secret_manager, reset_secret_manager

# ── Integrity & Audit ─────────────────────────────────────────────────────────
from .tamper_detector import TamperDetector, get_tamper_detector, reset_tamper_detector
from .audit_recorder import AuditRecorder, get_audit_recorder, reset_audit_recorder
from .audit_manager import AuditManager, get_audit_manager, reset_audit_manager
from .integrity_manager import IntegrityManager, get_integrity_manager, reset_integrity_manager

# ── Registry & Master Façade ──────────────────────────────────────────────────
from .security_registry import SecurityRegistry, get_security_registry, reset_security_registry
from .security_manager import SecurityManager, get_security_manager, reset_security_manager

__all__ = [
    # Legacy
    "TokenManager", "SymmetricEncryption", "generate_key",
    # Constants
    "PrincipalType", "IdentityStatus", "AuthMethod", "AuthStatus",
    "TokenType", "TokenStatus", "SessionStatus", "CredentialType",
    "PermissionEffect", "PolicyEffect", "PolicyType", "AccessDecision",
    "EncryptionAlgorithm", "HashAlgorithm", "KeyType", "KeyStatus",
    "SecretType", "SecretStatus", "AuditEventType", "AuditSeverity",
    "TLSVersion", "CertificateType",
    "DEFAULT_TOKEN_TTL", "DEFAULT_SESSION_TTL", "DEFAULT_KEY_ROTATION_DAYS",
    "MAX_LOGIN_ATTEMPTS", "MIN_PASSWORD_LENGTH", "API_KEY_LENGTH_BYTES",
    "SYSTEM_PRINCIPAL_ID", "ANONYMOUS_PRINCIPAL_ID", "SUPER_ADMIN_ROLE",
    # Exceptions
    "SecurityError", "TokenError", "EncryptionError",
    "IdentityError", "IdentityNotFoundError", "IdentityAlreadyExistsError",
    "IdentityLockedError", "IdentityExpiredError", "IdentityInvalidError",
    "AuthenticationError", "AuthenticationFailedError", "InvalidCredentialError",
    "CredentialExpiredError", "AccountLockedError", "MFARequiredError",
    "SessionError", "SessionNotFoundError", "SessionExpiredError", "SessionInvalidError",
    "AuthorizationError", "AccessDeniedError", "PermissionNotFoundError",
    "RoleNotFoundError", "RoleAlreadyExistsError", "PolicyError",
    "PolicyNotFoundError", "PolicyEvaluationError",
    "KeyError_", "KeyNotFoundError", "KeyRotationError", "KeyRevocationError",
    "SignatureError", "SignatureInvalidError",
    "CertificateError", "CertificateExpiredError", "CertificateInvalidError",
    "SecretError", "SecretNotFoundError", "SecretAlreadyExistsError",
    "SecretAccessDeniedError", "SecretRotationError",
    "IntegrityError", "TamperDetectedError", "ChecksumMismatchError",
    "AuditError", "AuditWriteError",
    # Models
    "PrincipalRecord", "TokenRecord", "SessionRecord", "CredentialRecord", "AuthResult",
    "PermissionRecord", "RoleRecord", "PolicyStatement", "PolicyRecord",
    "AccessRequest", "AccessResult",
    "KeyRecord", "CertificateRecord", "SignedPayload", "IntegrityChecksum",
    "SecretRecord", "SecretVersion",
    "AuditRecord", "SecurityEvent",
    # Context
    "SecurityContext", "get_security_context", "reset_security_context",
    "current_principal_id", "current_session_id", "security_scope", "system_scope",
    # Identity
    "Principal", "AnonymousPrincipal", "ANONYMOUS",
    "UserIdentity", "ServiceIdentity", "SystemIdentity", "get_system_identity",
    "IdentityProvider", "InMemoryIdentityProvider",
    "IdentityManager", "get_identity_manager", "reset_identity_manager",
    # Authentication
    "AuthenticationProvider", "PasswordAuthProvider", "ApiKeyAuthProvider",
    "TokenAuthProvider", "SystemAuthProvider",
    "CredentialManager", "get_credential_manager", "reset_credential_manager",
    "SessionManager", "get_session_manager", "reset_session_manager",
    "SecurityTokenManager", "get_token_manager", "reset_token_manager",
    "AuthenticationManager", "get_authentication_manager", "reset_authentication_manager",
    # Authorization
    "PermissionManager", "get_permission_manager", "reset_permission_manager",
    "RoleManager", "get_role_manager", "reset_role_manager",
    "PolicyManager", "get_policy_manager", "reset_policy_manager",
    "AccessController", "get_access_controller", "reset_access_controller",
    "AuthorizationManager", "get_authorization_manager", "reset_authorization_manager",
    # Encryption
    "CryptoProvider", "StdlibCryptoProvider", "FernetCryptoProvider",
    "get_crypto_provider", "reset_crypto_provider",
    "KeyManager", "get_key_manager", "reset_key_manager",
    "CertificateManager", "get_certificate_manager", "reset_certificate_manager",
    "EncryptionManager", "get_encryption_manager", "reset_encryption_manager",
    # Secrets
    "SecretStore", "VaultProvider", "InMemoryVaultProvider", "EnvironmentVaultProvider",
    "SecretManager", "get_secret_manager", "reset_secret_manager",
    # Integrity & Audit
    "TamperDetector", "get_tamper_detector", "reset_tamper_detector",
    "AuditRecorder", "get_audit_recorder", "reset_audit_recorder",
    "AuditManager", "get_audit_manager", "reset_audit_manager",
    "IntegrityManager", "get_integrity_manager", "reset_integrity_manager",
    # Registry & Façade
    "SecurityRegistry", "get_security_registry", "reset_security_registry",
    "SecurityManager", "get_security_manager", "reset_security_manager",
]
