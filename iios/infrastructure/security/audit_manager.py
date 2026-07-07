"""
iios/infrastructure/security/audit_manager.py
==============================================
High-level audit façade with structured security event tracking.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .audit_recorder import get_audit_recorder
from .security_constants import AuditEventType, AuditSeverity, AUDIT_SOURCE
from .security_models import AuditRecord

__all__ = ["AuditManager", "get_audit_manager", "reset_audit_manager"]

_LOG = logging.getLogger("iios.security.audit_manager")
_mgr_lock = threading.Lock()
_manager: Optional["AuditManager"] = None


class AuditManager:
    """High-level audit façade.

    Provides convenience methods for recording security events.
    All writes go through the AuditRecorder for checksum signing.

    Usage::

        audit = get_audit_manager()
        audit.login("user:alice", success=True, ip="192.168.1.1")
        audit.access_denied("user:bob", "trade:execute", "RELIANCE")
        audit.secret_accessed("service:bot", "iios/broker/dhan/api_key")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._extra_listeners: list[Callable[[AuditRecord], None]] = []

    # ── Authentication events ─────────────────────────────────────────────────

    def login(self, principal_id: str, success: bool, ip: str = "", details: Optional[dict[str, Any]] = None) -> AuditRecord:
        d = dict(details or {})
        if ip:
            d["ip_address"] = ip
        return get_audit_recorder().record(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            principal_id=principal_id,
            action="login",
            resource="iios.auth",
            outcome="success" if success else "failure",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            details=d,
        )

    def logout(self, principal_id: str, session_id: str = "") -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.LOGOUT,
            principal_id=principal_id,
            action="logout",
            resource="iios.auth",
            outcome="success",
            severity=AuditSeverity.INFO,
            details={"session_id": session_id} if session_id else {},
        )

    def lockout(self, principal_id: str, reason: str = "") -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.LOCKOUT,
            principal_id=principal_id,
            action="account_lockout",
            resource="iios.auth",
            outcome="locked",
            severity=AuditSeverity.WARNING,
            details={"reason": reason},
        )

    def token_issued(self, principal_id: str, token_type: str = "access") -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.TOKEN_ISSUED,
            principal_id=principal_id,
            action="token_issued",
            resource="iios.token",
            severity=AuditSeverity.INFO,
            details={"token_type": token_type},
        )

    def token_revoked(self, principal_id: str, jti: str = "") -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.TOKEN_REVOKED,
            principal_id=principal_id,
            action="token_revoked",
            resource="iios.token",
            severity=AuditSeverity.WARNING,
            details={"jti": jti[:8] if jti else ""},
        )

    # ── Authorization events ──────────────────────────────────────────────────

    def access_granted(self, principal_id: str, action: str, resource: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.ACCESS_GRANTED,
            principal_id=principal_id,
            action=action,
            resource=resource,
            outcome="permit",
            severity=AuditSeverity.DEBUG,
        )

    def access_denied(self, principal_id: str, action: str, resource: str, reason: str = "") -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.ACCESS_DENIED,
            principal_id=principal_id,
            action=action,
            resource=resource,
            outcome="deny",
            severity=AuditSeverity.WARNING,
            details={"reason": reason},
        )

    # ── Secrets events ────────────────────────────────────────────────────────

    def secret_accessed(self, principal_id: str, path: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.SECRET_ACCESSED,
            principal_id=principal_id,
            action="read",
            resource=path,
            severity=AuditSeverity.INFO,
        )

    def secret_rotated(self, principal_id: str, path: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.SECRET_ROTATED,
            principal_id=principal_id,
            action="rotate",
            resource=path,
            severity=AuditSeverity.WARNING,
        )

    def secret_created(self, principal_id: str, path: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.SECRET_CREATED,
            principal_id=principal_id,
            action="create",
            resource=path,
            severity=AuditSeverity.INFO,
        )

    def secret_deleted(self, principal_id: str, path: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.SECRET_DELETED,
            principal_id=principal_id,
            action="delete",
            resource=path,
            severity=AuditSeverity.WARNING,
        )

    # ── Key events ────────────────────────────────────────────────────────────

    def key_generated(self, principal_id: str, key_name: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.KEY_GENERATED,
            principal_id=principal_id,
            action="generate",
            resource=f"key:{key_name}",
            severity=AuditSeverity.INFO,
        )

    def key_rotated(self, principal_id: str, key_name: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.KEY_ROTATED,
            principal_id=principal_id,
            action="rotate",
            resource=f"key:{key_name}",
            severity=AuditSeverity.WARNING,
        )

    # ── Integrity events ──────────────────────────────────────────────────────

    def tamper_detected(self, resource_id: str, details: Optional[dict[str, Any]] = None) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.TAMPER_DETECTED,
            action="tamper_check",
            resource=resource_id,
            outcome="tampered",
            severity=AuditSeverity.CRITICAL,
            details=dict(details or {}),
        )

    def integrity_passed(self, resource_id: str) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=AuditEventType.INTEGRITY_CHECK_PASSED,
            action="integrity_check",
            resource=resource_id,
            severity=AuditSeverity.DEBUG,
        )

    # ── Generic event ─────────────────────────────────────────────────────────

    def record(
        self,
        event_type: AuditEventType,
        principal_id: str = "",
        action: str = "",
        resource: str = "",
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        return get_audit_recorder().record(
            event_type=event_type,
            principal_id=principal_id,
            action=action,
            resource=resource,
            outcome=outcome,
            severity=severity,
            details=details,
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, **kwargs: Any) -> list[AuditRecord]:
        return get_audit_recorder().query(**kwargs)

    def recent(self, n: int = 50) -> list[AuditRecord]:
        return get_audit_recorder().query(limit=n)

    def count(self) -> int:
        return get_audit_recorder().count()

    def verify_all(self) -> tuple[int, int]:
        return get_audit_recorder().verify_all()

    def reset(self) -> None:
        with self._lock:
            self._extra_listeners.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_audit_manager() -> AuditManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = AuditManager()
        return _manager


def reset_audit_manager() -> None:
    global _manager
    with _mgr_lock:
        _manager = None
