"""
iios/infrastructure/security/security_manager.py
=================================================
Master security façade — single entry point for all security operations
within the IIOS framework.

Usage::

    sec = get_security_manager()

    # Identity
    user = sec.create_user("alice", email="alice@example.com", roles=["trader"])
    sec.set_password(user.principal_id, "SuperSecret123!")

    # Auth
    result = sec.login(user.principal_id, password="SuperSecret123!")
    assert result.is_success

    # Authz
    sec.require(user.principal_id, "trade:execute", "RELIANCE")

    # Encrypt
    ct = sec.encrypt(b"sensitive data")
    pt = sec.decrypt(ct)

    # Secrets
    sec.set_secret("broker/dhan/key", b"sk-abc")
    key = sec.get_secret("broker/dhan/key")
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .access_controller import get_access_controller
from .audit_manager import get_audit_manager
from .authentication_manager import get_authentication_manager
from .authorization_manager import get_authorization_manager
from .certificate_manager import get_certificate_manager
from .credential_manager import get_credential_manager
from .crypto_provider import get_crypto_provider
from .encryption_manager import get_encryption_manager
from .identity_manager import get_identity_manager
from .integrity_manager import get_integrity_manager
from .key_manager import get_key_manager
from .permission_manager import get_permission_manager
from .policy_manager import get_policy_manager
from .role_manager import get_role_manager
from .secret_manager import get_secret_manager
from .security_constants import (
    AuthMethod,
    AuditEventType,
    AuditSeverity,
    HashAlgorithm,
    SecretType,
    TokenType,
)
from .security_context import security_scope, get_security_context
from .security_exceptions import SecurityError
from .security_models import (
    AccessResult,
    AuthResult,
    AuditRecord,
    PrincipalRecord,
    SecretRecord,
    SignedPayload,
)
from .session_manager import get_session_manager
from .tamper_detector import get_tamper_detector
from .token_manager_new import get_token_manager
from .user_identity import UserIdentity
from .service_identity import ServiceIdentity

__all__ = ["SecurityManager", "get_security_manager", "reset_security_manager"]

_LOG = logging.getLogger("iios.security")
_mgr_lock = threading.Lock()
_manager: Optional["SecurityManager"] = None


class SecurityManager:
    """Master security façade for the IIOS Security Framework.

    Provides a unified API over identity, authentication, authorisation,
    encryption, secrets, integrity, and audit subsystems.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    # ═══════════════════════════════════════════════════════════════════════════
    # Identity Management
    # ═══════════════════════════════════════════════════════════════════════════

    def create_user(
        self,
        name: str,
        email: str = "",
        roles: Optional[list[str]] = None,
        principal_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> UserIdentity:
        """Create and register a user identity."""
        user = get_identity_manager().create_user(
            name=name, email=email, roles=roles,
            principal_id=principal_id, attributes=attributes,
        )
        get_audit_manager().record(
            event_type=AuditEventType.IDENTITY_CREATED,
            principal_id=user.principal_id,
            action="create_user",
            resource=user.principal_id,
        )
        return user

    def create_service(
        self,
        name: str,
        roles: Optional[list[str]] = None,
        principal_id: Optional[str] = None,
    ) -> ServiceIdentity:
        """Create and register a service identity."""
        svc = get_identity_manager().create_service(
            name=name, roles=roles, principal_id=principal_id
        )
        get_audit_manager().record(
            event_type=AuditEventType.IDENTITY_CREATED,
            principal_id=svc.principal_id,
            action="create_service",
            resource=svc.principal_id,
        )
        return svc

    def get_principal(self, principal_id: str) -> PrincipalRecord:
        """Return a PrincipalRecord for the given ID."""
        return get_identity_manager().get(principal_id).to_record()

    # ═══════════════════════════════════════════════════════════════════════════
    # Authentication
    # ═══════════════════════════════════════════════════════════════════════════

    def set_password(self, principal_id: str, password: str) -> None:
        """Set (or update) the password for a principal."""
        get_credential_manager().set_password(principal_id, password)

    def generate_api_key(self, principal_id: str, prefix: str = "") -> str:
        """Generate a new API key for *principal_id*. Returns the plaintext key."""
        return get_credential_manager().generate_api_key(principal_id, prefix=prefix)

    def login(
        self,
        principal_id: str,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        ip_address: str = "",
        issue_token: bool = False,
    ) -> AuthResult:
        """Authenticate a principal. Returns AuthResult."""
        credentials: dict[str, Any] = {"principal_id": principal_id}
        if password is not None:
            credentials["password"] = password
        elif api_key is not None:
            credentials["api_key"] = api_key
        elif token is not None:
            credentials["token"] = token

        result = get_authentication_manager().authenticate(
            credentials,
            issue_session=True,
            issue_token=issue_token,
            ip_address=ip_address,
        )
        get_audit_manager().login(principal_id, result.is_success, ip=ip_address)
        return result

    def logout(self, session_id: str, principal_id: Optional[str] = None) -> bool:
        """Terminate a session."""
        ok = get_authentication_manager().logout(session_id, principal_id)
        if principal_id:
            get_audit_manager().logout(principal_id, session_id)
        return ok

    def issue_token(self, principal_id: str, token_type: TokenType = TokenType.ACCESS, scopes: Optional[list[str]] = None) -> str:
        """Issue a signed access token."""
        token_str = get_token_manager().issue(principal_id, token_type=token_type, scopes=scopes)
        get_audit_manager().token_issued(principal_id, token_type.value)
        return token_str

    def validate_token(self, token_str: str) -> dict[str, Any]:
        """Validate a token. Returns claims dict. Raises TokenError on failure."""
        return get_token_manager().validate_raw(token_str)

    # ═══════════════════════════════════════════════════════════════════════════
    # Authorization
    # ═══════════════════════════════════════════════════════════════════════════

    def grant_role(self, principal_id: str, role_name: str) -> None:
        get_authorization_manager().grant_role(principal_id, role_name)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        get_authorization_manager().revoke_role(principal_id, role_name)

    def is_permitted(self, principal_id: str, action: str, resource: str,
                     attributes: Optional[dict[str, Any]] = None) -> bool:
        return get_authorization_manager().is_permitted(principal_id, action, resource, attributes)

    def require(self, principal_id: str, action: str, resource: str,
                attributes: Optional[dict[str, Any]] = None) -> AccessResult:
        """Like is_permitted() but raises AccessDeniedError if denied."""
        result = get_authorization_manager().require(principal_id, action, resource, attributes)
        get_audit_manager().access_granted(principal_id, action, resource)
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Encryption
    # ═══════════════════════════════════════════════════════════════════════════

    def encrypt(self, data: bytes, key_name: Optional[str] = None) -> bytes:
        return get_encryption_manager().encrypt(data, key_name)

    def decrypt(self, ciphertext: bytes, key_name: Optional[str] = None) -> bytes:
        return get_encryption_manager().decrypt(ciphertext, key_name)

    def encrypt_text(self, text: str) -> str:
        return get_encryption_manager().encrypt_text(text)

    def decrypt_text(self, encoded: str) -> str:
        return get_encryption_manager().decrypt_text(encoded)

    def hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        return get_encryption_manager().hash(data, algorithm)

    def sign(self, data: bytes) -> SignedPayload:
        return get_encryption_manager().create_signed_payload(data)

    def verify_signature(self, signed: SignedPayload) -> bool:
        return get_encryption_manager().verify_signed_payload(signed)

    def generate_token(self, byte_length: int = 32) -> str:
        return get_encryption_manager().generate_token(byte_length)

    # ═══════════════════════════════════════════════════════════════════════════
    # Secrets Management
    # ═══════════════════════════════════════════════════════════════════════════

    def set_secret(
        self,
        path: str,
        value: bytes,
        secret_type: SecretType = SecretType.GENERIC,
        **kwargs: Any,
    ) -> SecretRecord:
        rec = get_secret_manager().set(path, value, secret_type=secret_type, **kwargs)
        get_audit_manager().secret_created("iios:system", path)
        return rec

    def get_secret(self, path: str) -> bytes:
        value = get_secret_manager().get(path)
        get_audit_manager().secret_accessed("iios:system", path)
        return value

    def get_secret_str(self, path: str) -> str:
        return get_secret_manager().get_str(path)

    def rotate_secret(self, path: str, new_value: bytes) -> SecretRecord:
        rec = get_secret_manager().rotate(path, new_value)
        get_audit_manager().secret_rotated("iios:system", path)
        return rec

    def delete_secret(self, path: str) -> bool:
        ok = get_secret_manager().delete(path)
        if ok:
            get_audit_manager().secret_deleted("iios:system", path)
        return ok

    # ═══════════════════════════════════════════════════════════════════════════
    # Integrity
    # ═══════════════════════════════════════════════════════════════════════════

    def verify_integrity(self, resource_id: str, data: bytes, expected: Optional[str] = None) -> bool:
        return get_integrity_manager().verify_checksum(data, resource_id, expected)

    def compute_checksum(self, resource_id: str, data: bytes) -> str:
        return get_integrity_manager().checksum(data, resource_id).checksum

    # ═══════════════════════════════════════════════════════════════════════════
    # Audit
    # ═══════════════════════════════════════════════════════════════════════════

    def audit(
        self,
        event_type: AuditEventType,
        principal_id: str = "",
        action: str = "",
        resource: str = "",
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        return get_audit_manager().record(
            event_type=event_type,
            principal_id=principal_id,
            action=action,
            resource=resource,
            outcome=outcome,
            severity=severity,
            details=details,
        )

    def audit_trail(self, principal_id: Optional[str] = None, limit: int = 100) -> list[AuditRecord]:
        return get_audit_manager().query(principal_id=principal_id, limit=limit)

    # ═══════════════════════════════════════════════════════════════════════════
    # Context
    # ═══════════════════════════════════════════════════════════════════════════

    def security_scope(self, principal_id: str, session_id: Optional[str] = None):
        """Return a context manager that sets the security context."""
        return security_scope(principal_id, session_id)

    def reset(self) -> None:
        _LOG.info("SecurityManager reset")


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_security_manager() -> SecurityManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = SecurityManager()
        return _manager


def reset_security_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
