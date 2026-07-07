"""
iios/infrastructure/security/security_models.py
================================================
Core dataclass models for the IIOS Security Framework.
All models are immutable-friendly (frozen where applicable) and serialisable.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .security_constants import (
    PrincipalType,
    IdentityStatus,
    AuthMethod,
    AuthStatus,
    TokenType,
    TokenStatus,
    SessionStatus,
    CredentialType,
    PermissionEffect,
    PolicyType,
    PolicyEffect,
    AccessDecision,
    KeyType,
    KeyStatus,
    SecretType,
    SecretStatus,
    AuditEventType,
    AuditSeverity,
    HashAlgorithm,
    EncryptionAlgorithm,
    CertificateType,
)

__all__ = [
    "PrincipalRecord",
    "TokenRecord",
    "SessionRecord",
    "CredentialRecord",
    "PermissionRecord",
    "RoleRecord",
    "PolicyStatement",
    "PolicyRecord",
    "AccessRequest",
    "AccessResult",
    "KeyRecord",
    "CertificateRecord",
    "SecretRecord",
    "SecretVersion",
    "AuditRecord",
    "AuthResult",
    "IntegrityChecksum",
    "SignedPayload",
    "SecurityEvent",
]


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> float:
    return time.time()


# ── Identity ──────────────────────────────────────────────────────────────────

@dataclass
class PrincipalRecord:
    """Serialisable snapshot of any principal (user, service, system, etc.)."""
    principal_id: str
    principal_type: PrincipalType
    name: str
    status: IdentityStatus = IdentityStatus.ACTIVE
    roles: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    last_login: Optional[float] = None
    login_failures: int = 0
    locked_until: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == IdentityStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        if self.status == IdentityStatus.LOCKED:
            if self.locked_until is None:
                return True
            return time.time() < self.locked_until
        return False


# ── Authentication ────────────────────────────────────────────────────────────

@dataclass
class TokenRecord:
    """Represents an issued token (access, refresh, API key, etc.)."""
    token_id: str = field(default_factory=_new_id)
    principal_id: str = ""
    token_type: TokenType = TokenType.ACCESS
    status: TokenStatus = TokenStatus.ACTIVE
    issued_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # The raw signed string is NOT stored in the record for security
    # Only the token_id (jti) is stored for revocation lookups

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.status == TokenStatus.ACTIVE and not self.is_expired


@dataclass
class SessionRecord:
    """Represents an authenticated session."""
    session_id: str = field(default_factory=lambda: _new_id()[:16].replace("-", ""))
    principal_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    auth_method: AuthMethod = AuthMethod.PASSWORD
    created_at: float = field(default_factory=_now)
    last_active: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    ip_address: str = ""
    user_agent: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE and not self.is_expired

    def touch(self) -> None:
        self.last_active = time.time()


@dataclass
class CredentialRecord:
    """Stored credential (hashed password, hashed API key, etc.)."""
    credential_id: str = field(default_factory=_new_id)
    principal_id: str = ""
    credential_type: CredentialType = CredentialType.PASSWORD
    # Stored as: "<algorithm>:<salt>:<hash>" for passwords
    # or "<prefix>:<truncated>" for API keys
    hashed_value: str = ""
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    is_primary: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    status: AuthStatus
    principal_id: str = ""
    session_id: str = ""
    token: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == AuthStatus.SUCCESS


# ── Authorization ─────────────────────────────────────────────────────────────

@dataclass
class PermissionRecord:
    """A single named permission (action on resource)."""
    permission_id: str = field(default_factory=_new_id)
    name: str = ""               # e.g. "orders:read"
    resource: str = ""           # e.g. "orders"
    action: str = ""             # e.g. "read"
    effect: PermissionEffect = PermissionEffect.ALLOW
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name and self.resource and self.action:
            self.name = f"{self.resource}:{self.action}"


@dataclass
class RoleRecord:
    """A named role that bundles permissions."""
    role_id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    permissions: list[str] = field(default_factory=list)   # permission names
    parent_roles: list[str] = field(default_factory=list)  # role inheritance
    attributes: dict[str, Any] = field(default_factory=dict)
    is_system: bool = False    # system roles cannot be deleted


@dataclass
class PolicyStatement:
    """A single statement within a policy (allow/deny a set of actions)."""
    effect: PolicyEffect = PolicyEffect.ALLOW
    actions: list[str] = field(default_factory=list)       # ["orders:read", "*"]
    resources: list[str] = field(default_factory=list)     # ["orders/*", "*"]
    conditions: dict[str, Any] = field(default_factory=dict)  # ABAC conditions


@dataclass
class PolicyRecord:
    """A named policy document (collection of statements)."""
    policy_id: str = field(default_factory=_new_id)
    name: str = ""
    policy_type: PolicyType = PolicyType.RBAC
    statements: list[PolicyStatement] = field(default_factory=list)
    description: str = ""
    is_system: bool = False


@dataclass
class AccessRequest:
    """Captures the context of an authorisation check."""
    principal_id: str
    action: str
    resource: str
    attributes: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessResult:
    """Result of an authorisation decision."""
    decision: AccessDecision
    principal_id: str = ""
    action: str = ""
    resource: str = ""
    matched_policy: str = ""
    matched_role: str = ""
    reason: str = ""

    @property
    def is_permitted(self) -> bool:
        return self.decision == AccessDecision.PERMIT


# ── Encryption / Keys ─────────────────────────────────────────────────────────

@dataclass
class KeyRecord:
    """Metadata for a managed encryption key."""
    key_id: str = field(default_factory=_new_id)
    name: str = ""
    key_type: KeyType = KeyType.SYMMETRIC
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: float = field(default_factory=_now)
    rotates_at: Optional[float] = None
    rotated_from: Optional[str] = None   # previous key_id
    metadata: dict[str, Any] = field(default_factory=dict)
    # Raw key material is NOT stored in KeyRecord — only in KeyManager's vault

    @property
    def needs_rotation(self) -> bool:
        if self.rotates_at is None:
            return False
        return time.time() > self.rotates_at

    @property
    def is_active(self) -> bool:
        return self.status == KeyStatus.ACTIVE


@dataclass
class CertificateRecord:
    """Metadata for a managed certificate."""
    cert_id: str = field(default_factory=_new_id)
    name: str = ""
    cert_type: CertificateType = CertificateType.SELF_SIGNED
    subject: str = ""
    issuer: str = ""
    fingerprint: str = ""
    not_before: float = field(default_factory=_now)
    not_after: float = field(default_factory=lambda: _now() + 365 * 86400)
    pem_data: str = ""    # PEM-encoded cert (no private key)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.not_after

    @property
    def is_valid(self) -> bool:
        now = time.time()
        return self.not_before <= now <= self.not_after


@dataclass
class SignedPayload:
    """A payload bundled with its HMAC or digital signature."""
    payload: bytes
    signature: bytes
    algorithm: str = "hmac-sha256"
    key_id: str = ""
    signed_at: float = field(default_factory=_now)

    @property
    def payload_str(self) -> str:
        return self.payload.decode("utf-8", errors="replace")


@dataclass
class IntegrityChecksum:
    """Stores a computed checksum for later verification."""
    checksum_id: str = field(default_factory=_new_id)
    resource_id: str = ""
    algorithm: str = "sha256"
    checksum: str = ""
    computed_at: float = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Secrets ───────────────────────────────────────────────────────────────────

@dataclass
class SecretVersion:
    """One version of a secret's value (encrypted at rest)."""
    version: int = 1
    encrypted_value: bytes = field(default_factory=bytes)
    created_at: float = field(default_factory=_now)
    created_by: str = ""
    is_current: bool = True


@dataclass
class SecretRecord:
    """Metadata for a managed secret (value stored encrypted separately)."""
    secret_id: str = field(default_factory=_new_id)
    name: str = ""
    path: str = ""          # e.g. "iios/broker/dhan/api_key"
    secret_type: SecretType = SecretType.GENERIC
    status: SecretStatus = SecretStatus.ACTIVE
    description: str = ""
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    current_version: int = 1

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


# ── Audit ─────────────────────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    """Immutable audit log entry. Once written, must not be modified."""
    audit_id: str = field(default_factory=_new_id)
    event_type: AuditEventType = AuditEventType.ACCESS_GRANTED
    severity: AuditSeverity = AuditSeverity.INFO
    principal_id: str = ""
    action: str = ""
    resource: str = ""
    outcome: str = "success"
    source: str = "iios.security"
    timestamp: float = field(default_factory=_now)
    details: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""    # HMAC of the record content for tamper detection

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "principal_id": self.principal_id,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "source": self.source,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class SecurityEvent:
    """A security-related event emitted to the event bus."""
    event_id: str = field(default_factory=_new_id)
    event_type: AuditEventType = AuditEventType.ACCESS_GRANTED
    severity: AuditSeverity = AuditSeverity.INFO
    principal_id: str = ""
    source: str = "iios.security"
    timestamp: float = field(default_factory=_now)
    payload: dict[str, Any] = field(default_factory=dict)
