"""iios/common/logging/audit_logger.py
Structured audit logging for the IIOS platform.

Captures all compliance-relevant events:
  • Configuration changes
  • Engine lifecycle transitions
  • Workflow stage events
  • Validation pass/fail
  • Snapshot publications
  • Failures and exceptions
  • Security events

All audit records are emitted at ``logging.INFO`` level with an
``audit=True`` marker so they can be filtered/routed separately from
regular application logs.

Usage::

    from iios.common.logging.audit_logger import get_audit_logger

    audit = get_audit_logger("iios.market.integration",
                              engine_id="iios:market:intelligence:integration")

    audit.log_lifecycle_event(
        engine_id  = "iios:market:intelligence:integration",
        from_state = "INITIALIZED",
        to_state   = "RUNNING",
        version    = "1.0.0",
    )

    audit.log_config_change("market_engine", "polling_interval", 30, 15)
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from iios.common.logging.logging_context import LoggingContext
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.structured_logger import StructuredLogger


# ── Audit event types ─────────────────────────────────────────────────────────

class AuditEventType(str, Enum):
    CONFIG_CHANGED    = "CONFIG_CHANGED"
    LIFECYCLE_EVENT   = "LIFECYCLE_EVENT"
    WORKFLOW_EVENT    = "WORKFLOW_EVENT"
    VALIDATION_EVENT  = "VALIDATION_EVENT"
    PUBLICATION_EVENT = "PUBLICATION_EVENT"
    FAILURE           = "FAILURE"
    SECURITY_EVENT    = "SECURITY_EVENT"


# ── Audit record ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditRecord:
    """Immutable snapshot of a single audit event."""

    event_type:       AuditEventType
    component:        str
    engine_id:        str
    timestamp:        datetime
    details:          Dict[str, Any]
    actor:            str                   = ""
    context_snapshot: Dict[str, str]        = field(default_factory=dict)


# ── AuditLogger ───────────────────────────────────────────────────────────────

class AuditLogger:
    """
    Thread-safe audit logger for one component/engine.

    Emits structured log records at ``logging.INFO`` level with an
    ``audit=True`` extra field, allowing downstream handlers to route
    audit events to dedicated storage.
    """

    def __init__(
        self,
        name:      str,
        *,
        engine_id: str = "",
        component: str = "",
    ) -> None:
        self._name:      str = name
        self._engine_id: str = engine_id
        self._component: str = component
        self._log:       StructuredLogger = get_logger(
            name, engine_id=engine_id, component=component
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _emit(
        self,
        event_type: AuditEventType,
        message:    str,
        details:    Dict[str, Any],
        *,
        actor:      str = "",
        exc:        Optional[BaseException] = None,
    ) -> AuditRecord:
        ctx_snapshot = LoggingContext.to_dict()

        record = AuditRecord(
            event_type       = event_type,
            component        = self._component or self._name,
            engine_id        = self._engine_id,
            timestamp        = datetime.now(timezone.utc),
            details          = details,
            actor            = actor,
            context_snapshot = ctx_snapshot,
        )

        full_details: Dict[str, Any] = {
            "event_type": event_type.value,
            "component":  record.component,
            **details,
        }
        if actor:
            full_details["actor"] = actor

        self._log.structured(
            logging.INFO,
            message,
            context = full_details,
            exc     = exc,
        )

        return record

    # ── Public API ────────────────────────────────────────────────────────────

    def log_lifecycle_event(
        self,
        engine_id:  str,
        from_state: str,
        to_state:   str,
        version:    str,
        *,
        actor:      str = "system",
        **kwargs:   Any,
    ) -> AuditRecord:
        """Audit an engine lifecycle state transition."""
        details: Dict[str, Any] = {
            "engine_id":  engine_id,
            "from_state": from_state,
            "to_state":   to_state,
            "version":    version,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.LIFECYCLE_EVENT,
            f"Lifecycle: {engine_id} {from_state} → {to_state}",
            details,
            actor=actor,
        )

    def log_workflow_event(
        self,
        workflow_id: str,
        stage:       str,
        event:       str,
        *,
        actor:       str = "system",
        **kwargs:    Any,
    ) -> AuditRecord:
        """Audit a workflow stage event."""
        details: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "stage":       stage,
            "event":       event,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.WORKFLOW_EVENT,
            f"Workflow: {workflow_id} stage={stage} event={event}",
            details,
            actor=actor,
        )

    def log_config_change(
        self,
        component: str,
        key:       str,
        old_value: Any,
        new_value: Any,
        *,
        actor:     str = "system",
        **kwargs:  Any,
    ) -> AuditRecord:
        """Audit a configuration change."""
        details: Dict[str, Any] = {
            "config_component": component,
            "key":              key,
            "old_value":        old_value,
            "new_value":        new_value,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.CONFIG_CHANGED,
            f"Config changed: {component}.{key} = {old_value!r} → {new_value!r}",
            details,
            actor=actor,
        )

    def log_validation_event(
        self,
        component:       str,
        validation_type: str,
        result:          bool,
        *,
        actor:           str = "system",
        **kwargs:        Any,
    ) -> AuditRecord:
        """Audit a validation pass or fail."""
        details: Dict[str, Any] = {
            "validated_component": component,
            "validation_type":     validation_type,
            "result":              "PASS" if result else "FAIL",
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.VALIDATION_EVENT,
            f"Validation {details['result']}: {component} [{validation_type}]",
            details,
            actor=actor,
        )

    def log_publication_event(
        self,
        component:   str,
        snapshot_id: str,
        *,
        actor:       str = "system",
        **kwargs:    Any,
    ) -> AuditRecord:
        """Audit a data snapshot publication."""
        details: Dict[str, Any] = {
            "published_component": component,
            "snapshot_id":         snapshot_id,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.PUBLICATION_EVENT,
            f"Published: {component} snapshot_id={snapshot_id}",
            details,
            actor=actor,
        )

    def log_failure(
        self,
        component:  str,
        error_type: str,
        message:    str,
        *,
        exc:        Optional[BaseException] = None,
        actor:      str = "system",
        **kwargs:   Any,
    ) -> AuditRecord:
        """Audit a failure event, optionally capturing exception details."""
        details: Dict[str, Any] = {
            "failed_component": component,
            "error_type":       error_type,
            "error_message":    message,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.FAILURE,
            f"Failure in {component}: [{error_type}] {message}",
            details,
            actor=actor,
            exc=exc,
        )

    def log_security_event(
        self,
        component:  str,
        event_type: str,
        *,
        actor:      str = "system",
        **kwargs:   Any,
    ) -> AuditRecord:
        """Audit a security-relevant event (access, auth, privilege changes)."""
        details: Dict[str, Any] = {
            "security_component": component,
            "security_event":     event_type,
        }
        details.update(kwargs)
        return self._emit(
            AuditEventType.SECURITY_EVENT,
            f"Security event: {component} [{event_type}]",
            details,
            actor=actor,
        )


# ── Registry ──────────────────────────────────────────────────────────────────

_registry_lock:   threading.Lock                 = threading.Lock()
_audit_registry:  Dict[str, AuditLogger]         = {}


def get_audit_logger(
    name:      str,
    *,
    engine_id: str = "",
    component: str = "",
) -> AuditLogger:
    """
    Return or create an ``AuditLogger`` for the given name.

    Cached per ``(name, engine_id)`` pair.

    Example::

        audit = get_audit_logger("iios.market.integration",
                                  engine_id="iios:market:intelligence:integration")
    """
    key = f"{name}:{engine_id}"
    with _registry_lock:
        if key not in _audit_registry:
            _audit_registry[key] = AuditLogger(
                name, engine_id=engine_id, component=component
            )
        return _audit_registry[key]
