"""
iios/monitoring/audit_logger.py
=================================
Immutable audit trail for security, compliance, and operational governance.

Every security-relevant action (trades, config changes, kill-switch triggers,
login/logout) should be recorded here. Records are written to a dedicated
audit log file and optionally to SQLite.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .monitoring_models import AuditRecord
from .monitoring_constants import AuditAction

__all__ = [
    "AuditLogger",
    "get_audit_logger",
]

_audit_logger_lock = threading.Lock()
_audit_logger_instance: Optional["AuditLogger"] = None

_LOG = logging.getLogger("iios.monitoring.audit")


class AuditLogger:
    """Records immutable audit events to a dedicated log sink.

    Args:
        log_file:    Path to the audit log file. Appends to it.
        console:     If True, also echo to console at DEBUG level.
    """

    def __init__(
        self,
        log_file: str = "logs/audit.log",
        console: bool = False,
    ) -> None:
        self._log_file = Path(log_file)
        self._console = console
        self._lock = threading.Lock()
        self._records: list[AuditRecord] = []   # in-memory ring buffer
        self._max_in_memory = 1000
        self._record_count = 0
        self._setup_file()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        actor: str,
        resource: str,
        outcome: str = "success",
        reason: str = "",
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        session_id: str = "",
        correlation_id: str = "",
        ip_address: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        """Record an audit event.

        Returns the ``AuditRecord`` for caller inspection.
        """
        record = AuditRecord(
            action=action,
            actor=actor,
            resource=resource,
            outcome=outcome,
            reason=reason,
            old_value=old_value,
            new_value=new_value,
            session_id=session_id,
            correlation_id=correlation_id,
            ip_address=ip_address,
            metadata=metadata or {},
        )
        self._persist(record)
        return record

    def trade(
        self,
        actor: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        outcome: str = "success",
        correlation_id: str = "",
        **extra: Any,
    ) -> AuditRecord:
        """Convenience wrapper for trade audit records."""
        return self.log(
            action=AuditAction.TRADE.value,
            actor=actor,
            resource=symbol,
            outcome=outcome,
            reason=f"{side} {quantity}@{price}",
            correlation_id=correlation_id,
            metadata={"side": side, "quantity": quantity, "price": price, **extra},
        )

    def config_change(
        self,
        actor: str,
        key: str,
        old_value: Any,
        new_value: Any,
        reason: str = "",
        correlation_id: str = "",
    ) -> AuditRecord:
        """Record a configuration change."""
        return self.log(
            action=AuditAction.CONFIG.value,
            actor=actor,
            resource=key,
            old_value=str(old_value),
            new_value=str(new_value),
            reason=reason,
            correlation_id=correlation_id,
        )

    def security_event(
        self,
        actor: str,
        event: str,
        outcome: str = "success",
        **extra: Any,
    ) -> AuditRecord:
        """Record a security-relevant event."""
        return self.log(
            action=AuditAction.OVERRIDE.value,
            actor=actor,
            resource=event,
            outcome=outcome,
            metadata=extra,
        )

    def search(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Search in-memory records (most recent first)."""
        with self._lock:
            results = list(reversed(self._records))
        if actor:
            results = [r for r in results if r.actor == actor]
        if action:
            results = [r for r in results if r.action == action]
        if resource:
            results = [r for r in results if resource in r.resource]
        return results[:limit]

    @property
    def record_count(self) -> int:
        return self._record_count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _persist(self, record: AuditRecord) -> None:
        line = json.dumps(self._to_dict(record), default=str)
        with self._lock:
            # Write to file
            try:
                with self._log_file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                _LOG.error("Audit log write failed: %s", exc)

            # In-memory ring buffer
            self._records.append(record)
            if len(self._records) > self._max_in_memory:
                self._records.pop(0)
            self._record_count += 1

        if self._console:
            _LOG.debug("AUDIT %s", line)

    def _setup_file(self) -> None:
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    @staticmethod
    def _to_dict(record: AuditRecord) -> dict:
        return {
            "record_id": record.record_id,
            "timestamp": record.timestamp,
            "action": record.action,
            "actor": record.actor,
            "resource": record.resource,
            "outcome": record.outcome,
            "reason": record.reason,
            "old_value": record.old_value,
            "new_value": record.new_value,
            "ip_address": record.ip_address,
            "session_id": record.session_id,
            "correlation_id": record.correlation_id,
            "metadata": record.metadata,
        }


def get_audit_logger(log_file: str = "logs/audit.log") -> AuditLogger:
    """Return (or create) the global ``AuditLogger`` singleton."""
    global _audit_logger_instance
    with _audit_logger_lock:
        if _audit_logger_instance is None:
            _audit_logger_instance = AuditLogger(log_file=log_file)
        return _audit_logger_instance


def _reset_audit_logger() -> None:
    """Reset the global singleton — for tests only."""
    global _audit_logger_instance
    with _audit_logger_lock:
        _audit_logger_instance = None
