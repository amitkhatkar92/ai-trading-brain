"""
iios/infrastructure/security/audit_recorder.py
===============================================
Appends immutable audit records to an in-memory ring buffer.
Supports structured logging and tamper-evident checksums.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Optional

from .security_constants import AuditEventType, AuditSeverity, MAX_AUDIT_HISTORY, AUDIT_SOURCE
from .security_exceptions import AuditWriteError
from .security_models import AuditRecord
from .tamper_detector import get_tamper_detector

__all__ = ["AuditRecorder", "get_audit_recorder", "reset_audit_recorder"]

_LOG = logging.getLogger("iios.security.audit")
_mgr_lock = threading.Lock()
_recorder: Optional["AuditRecorder"] = None


class AuditRecorder:
    """Appends tamper-evident audit records to a bounded ring buffer.

    Audit records are signed with an HMAC checksum before storage.
    Any post-write modification will fail checksum verification.

    Usage::

        recorder = get_audit_recorder()
        recorder.record(
            event_type=AuditEventType.LOGIN,
            principal_id="user:alice",
            action="login",
            resource="iios.auth",
            severity=AuditSeverity.INFO,
        )
        records = recorder.query(principal_id="user:alice", limit=10)
    """

    def __init__(
        self,
        max_size: int = MAX_AUDIT_HISTORY,
        listeners: Optional[list[Callable[[AuditRecord], None]]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._buffer: deque[AuditRecord] = deque(maxlen=max_size)
        self._listeners: list[Callable[[AuditRecord], None]] = list(listeners or [])
        self._write_count = 0
        self._error_count = 0

    # ── Record ────────────────────────────────────────────────────────────────

    def record(
        self,
        event_type: AuditEventType,
        principal_id: str = "",
        action: str = "",
        resource: str = "",
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        source: str = AUDIT_SOURCE,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        """Create, sign, and append an audit record."""
        rec = AuditRecord(
            event_type=event_type,
            severity=severity,
            principal_id=principal_id,
            action=action,
            resource=resource,
            outcome=outcome,
            source=source,
            timestamp=time.time(),
            details=dict(details or {}),
        )
        try:
            rec.checksum = get_tamper_detector().sign_audit_record(rec.to_dict())
        except Exception:
            rec.checksum = ""

        with self._lock:
            self._buffer.append(rec)
            self._write_count += 1

        # Structured log
        log_fn = {
            AuditSeverity.DEBUG: _LOG.debug,
            AuditSeverity.INFO: _LOG.info,
            AuditSeverity.WARNING: _LOG.warning,
            AuditSeverity.ERROR: _LOG.error,
            AuditSeverity.CRITICAL: _LOG.critical,
        }.get(severity, _LOG.info)
        log_fn(
            "AUDIT [%s] principal=%s action=%s resource=%s outcome=%s",
            event_type.value, principal_id, action, resource, outcome,
        )

        # Notify listeners (best-effort — never let a listener crash the recorder)
        for listener in list(self._listeners):
            try:
                listener(rec)
            except Exception as exc:
                _LOG.warning("Audit listener error: %s", exc)

        return rec

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        principal_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Filter audit records. Returns newest-first, limited to *limit*."""
        with self._lock:
            records = list(reversed(list(self._buffer)))

        result = []
        for rec in records:
            if event_type is not None and rec.event_type != event_type:
                continue
            if principal_id is not None and rec.principal_id != principal_id:
                continue
            if action is not None and rec.action != action:
                continue
            if resource is not None and rec.resource != resource:
                continue
            if severity is not None and rec.severity != severity:
                continue
            if since is not None and rec.timestamp < since:
                continue
            if until is not None and rec.timestamp > until:
                continue
            result.append(rec)
            if len(result) >= limit:
                break
        return result

    def all_records(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._buffer)

    def count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def write_count(self) -> int:
        return self._write_count

    # ── Integrity verification ─────────────────────────────────────────────────

    def verify_record(self, rec: AuditRecord) -> bool:
        """Verify a single record's HMAC checksum."""
        if not rec.checksum:
            return False
        return get_tamper_detector().verify_audit_record(rec.to_dict(), rec.checksum)

    def verify_all(self) -> tuple[int, int]:
        """Verify all stored records. Returns (passed, failed)."""
        passed = failed = 0
        with self._lock:
            records = list(self._buffer)
        for rec in records:
            if self.verify_record(rec):
                passed += 1
            else:
                failed += 1
        return passed, failed

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[AuditRecord], None]) -> None:
        with self._lock:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[AuditRecord], None]) -> bool:
        with self._lock:
            try:
                self._listeners.remove(fn)
                return True
            except ValueError:
                return False

    def reset(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._listeners.clear()
            self._write_count = 0
            self._error_count = 0


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_audit_recorder() -> AuditRecorder:
    global _recorder
    with _mgr_lock:
        if _recorder is None:
            _recorder = AuditRecorder()
        return _recorder


def reset_audit_recorder() -> None:
    global _recorder
    with _mgr_lock:
        if _recorder is not None:
            _recorder.reset()
        _recorder = None
