"""
iios/infrastructure/security/security_constants.py
====================================================
Enumerations and numeric constants for the IIOS Security Framework.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Final

__all__ = [
    # Principal / Identity
    "PrincipalType",
    "IdentityStatus",
    # Authentication
    "AuthMethod",
    "AuthStatus",
    "TokenType",
    "TokenStatus",
    "SessionStatus",
    "CredentialType",
    # Authorization
    "PermissionEffect",
    "PolicyEffect",
    "PolicyType",
    "AccessDecision",
    # Encryption
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "KeyType",
    "KeyStatus",
    # Secrets
    "SecretType",
    "SecretStatus",
    # Audit
    "AuditEventType",
    "AuditSeverity",
    # TLS
    "TLSVersion",
    "CertificateType",
    # Numeric defaults
    "DEFAULT_TOKEN_TTL",
    "DEFAULT_SESSION_TTL",
    "DEFAULT_KEY_ROTATION_DAYS",
    "DEFAULT_SECRET_TTL",
    "MAX_LOGIN_ATTEMPTS",
    "LOCKOUT_DURATION_SECONDS",
    "MAX_AUDIT_HISTORY",
    "DEFAULT_HASH_ROUNDS",
    "MIN_PASSWORD_LENGTH",
    "API_KEY_LENGTH_BYTES",
    "SESSION_ID_LENGTH_BYTES",
    "SECRET_ID_LENGTH_BYTES",
    # Namespace
    "SYSTEM_PRINCIPAL_ID",
    "ANONYMOUS_PRINCIPAL_ID",
    "SUPER_ADMIN_ROLE",
    "AUDIT_SOURCE",
]


# ── Principal / Identity ─────────────────────────────────────────────────────

class PrincipalType(str, Enum):
    USER    = "user"
    SERVICE = "service"
    SYSTEM  = "system"
    MACHINE = "machine"
    BOT     = "bot"
    ANONYMOUS = "anonymous"


class IdentityStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    LOCKED    = "locked"
    SUSPENDED = "suspended"
    EXPIRED   = "expired"
    PENDING   = "pending"


# ── Authentication ────────────────────────────────────────────────────────────

class AuthMethod(str, Enum):
    PASSWORD    = "password"
    API_KEY     = "api_key"
    TOKEN       = "token"
    SESSION     = "session"
    CERTIFICATE = "certificate"
    OAUTH       = "oauth"
    MFA         = "mfa"
    SYSTEM      = "system"   # internal system-to-system


class AuthStatus(str, Enum):
    SUCCESS         = "success"
    FAILED          = "failed"
    LOCKED          = "locked"
    EXPIRED         = "expired"
    MFA_REQUIRED    = "mfa_required"
    PASSWORD_CHANGE = "password_change_required"


class TokenType(str, Enum):
    ACCESS  = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE = "service"
    SYSTEM  = "system"


class TokenStatus(str, Enum):
    ACTIVE    = "active"
    REVOKED   = "revoked"
    EXPIRED   = "expired"


class SessionStatus(str, Enum):
    ACTIVE    = "active"
    EXPIRED   = "expired"
    TERMINATED = "terminated"
    IDLE      = "idle"


class CredentialType(str, Enum):
    PASSWORD   = "password"
    API_KEY    = "api_key"
    TOTP       = "totp"
    CERTIFICATE = "certificate"


# ── Authorization ─────────────────────────────────────────────────────────────

class PermissionEffect(str, Enum):
    ALLOW = "allow"
    DENY  = "deny"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY  = "deny"


class PolicyType(str, Enum):
    RBAC   = "rbac"    # Role-Based
    ABAC   = "abac"    # Attribute-Based
    STATIC = "static"  # Hard-coded rules


class AccessDecision(str, Enum):
    PERMIT        = "permit"
    DENY          = "deny"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


# ── Encryption ────────────────────────────────────────────────────────────────

class EncryptionAlgorithm(str, Enum):
    AES_256_CBC = "aes-256-cbc"
    AES_256_GCM = "aes-256-gcm"
    AES_128_CBC = "aes-128-cbc"
    RSA_2048    = "rsa-2048"
    RSA_4096    = "rsa-4096"
    FERNET      = "fernet"     # Fernet (AES-128-CBC + HMAC-SHA256)


class HashAlgorithm(str, Enum):
    SHA256  = "sha256"
    SHA512  = "sha512"
    SHA3_256 = "sha3_256"
    BLAKE2B = "blake2b"
    BCRYPT  = "bcrypt"
    PBKDF2  = "pbkdf2"


class KeyType(str, Enum):
    SYMMETRIC   = "symmetric"
    RSA_PRIVATE = "rsa_private"
    RSA_PUBLIC  = "rsa_public"
    HMAC        = "hmac"


class KeyStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    ROTATED  = "rotated"
    REVOKED  = "revoked"
    EXPIRED  = "expired"


# ── Secrets ───────────────────────────────────────────────────────────────────

class SecretType(str, Enum):
    API_KEY       = "api_key"
    PASSWORD      = "password"
    DATABASE_URL  = "database_url"
    OAUTH_SECRET  = "oauth_secret"
    ENCRYPTION_KEY = "encryption_key"
    CERTIFICATE   = "certificate"
    TOKEN         = "token"
    GENERIC       = "generic"


class SecretStatus(str, Enum):
    ACTIVE  = "active"
    ROTATED = "rotated"
    EXPIRED = "expired"
    DELETED = "deleted"


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditEventType(str, Enum):
    # Authentication
    LOGIN           = "login"
    LOGOUT          = "logout"
    LOGIN_FAILED    = "login_failed"
    TOKEN_ISSUED    = "token_issued"
    TOKEN_REVOKED   = "token_revoked"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    LOCKOUT         = "account_lockout"
    # Authorization
    ACCESS_GRANTED  = "access_granted"
    ACCESS_DENIED   = "access_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    # Secrets
    SECRET_ACCESSED = "secret_accessed"
    SECRET_ROTATED  = "secret_rotated"
    SECRET_CREATED  = "secret_created"
    SECRET_DELETED  = "secret_deleted"
    # Crypto
    KEY_GENERATED   = "key_generated"
    KEY_ROTATED     = "key_rotated"
    KEY_REVOKED     = "key_revoked"
    ENCRYPTION_FAILED = "encryption_failed"
    # Integrity
    INTEGRITY_CHECK_PASSED = "integrity_check_passed"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    TAMPER_DETECTED = "tamper_detected"
    # Identity
    IDENTITY_CREATED = "identity_created"
    IDENTITY_UPDATED = "identity_updated"
    IDENTITY_DELETED = "identity_deleted"
    # Policy
    POLICY_CHANGED  = "policy_changed"


class AuditSeverity(str, Enum):
    DEBUG    = "debug"
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


# ── TLS / Certificates ────────────────────────────────────────────────────────

class TLSVersion(str, Enum):
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


class CertificateType(str, Enum):
    SELF_SIGNED = "self_signed"
    CA_SIGNED   = "ca_signed"
    CLIENT      = "client"
    SERVER      = "server"


# ── Numeric defaults ─────────────────────────────────────────────────────────

DEFAULT_TOKEN_TTL: Final[int]             = 3_600       # 1 hour
DEFAULT_SESSION_TTL: Final[int]           = 28_800      # 8 hours
DEFAULT_KEY_ROTATION_DAYS: Final[int]     = 90
DEFAULT_SECRET_TTL: Final[int]            = 86_400 * 30  # 30 days
MAX_LOGIN_ATTEMPTS: Final[int]            = 5
LOCKOUT_DURATION_SECONDS: Final[int]      = 900         # 15 min
MAX_AUDIT_HISTORY: Final[int]             = 100_000
DEFAULT_HASH_ROUNDS: Final[int]           = 260_000     # PBKDF2 iterations
MIN_PASSWORD_LENGTH: Final[int]           = 12
API_KEY_LENGTH_BYTES: Final[int]          = 32
SESSION_ID_LENGTH_BYTES: Final[int]       = 32
SECRET_ID_LENGTH_BYTES: Final[int]        = 16

# ── Special identities ────────────────────────────────────────────────────────

SYSTEM_PRINCIPAL_ID: Final[str]   = "iios:system"
ANONYMOUS_PRINCIPAL_ID: Final[str] = "iios:anonymous"
SUPER_ADMIN_ROLE: Final[str]      = "super_admin"
AUDIT_SOURCE: Final[str]          = "iios.security"
