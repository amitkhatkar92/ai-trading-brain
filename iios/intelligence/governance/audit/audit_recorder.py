"""
iios/intelligence/governance/audit/audit_recorder.py
=====================================================
AuditRecorder — convenience factory for writing audit events.
"""
from __future__ import annotations

import threading
from typing import Any

from .audit_record import AuditRecord
from .audit_registry import AuditRegistry, get_audit_registry
from ..quality_constants import (
    AuditEventType,
    IntelligenceType,
    GOVERNANCE_SYSTEM_ID,
)
from ..quality_result import QualityRecord


class AuditRecorder:
    """
    Writes AuditRecord entries to the AuditRegistry for every
    governance lifecycle event.
    """

    def __init__(self) -> None:
        self._registry: AuditRegistry = get_audit_registry()
        self._lock:     threading.RLock = threading.RLock()

    # -- Public shortcuts ──────────────────────────────────────────────────────

    def record_evaluation(
        self,
        record:   QualityRecord,
        actor_id: str = GOVERNANCE_SYSTEM_ID,
    ) -> AuditRecord:
        return self._write(
            event_type   = AuditEventType.EVALUATION,
            record       = record,
            actor_id     = actor_id,
            payload      = {
                "quality_score": record.quality_score,
                "quality_level": record.quality_level.value,
                "dimensions":    record.dimension_scores,
            },
        )

    def record_approval(
        self,
        record:   QualityRecord,
        actor_id: str = GOVERNANCE_SYSTEM_ID,
        reason:   str = "",
    ) -> AuditRecord:
        return self._write(
            event_type = AuditEventType.APPROVAL,
            record     = record,
            actor_id   = actor_id,
            payload    = {
                "reason":        reason,
                "quality_score": record.quality_score,
            },
        )

    def record_rejection(
        self,
        record:   QualityRecord,
        reason:   str = "",
        actor_id: str = GOVERNANCE_SYSTEM_ID,
    ) -> AuditRecord:
        return self._write(
            event_type = AuditEventType.REJECTION,
            record     = record,
            actor_id   = actor_id,
            payload    = {
                "reason":           reason,
                "quality_score":    record.quality_score,
                "rejection_reasons": record.rejection_reasons,
            },
        )

    def record_certification(
        self,
        record:  QualityRecord,
        cert_id: str,
        actor_id: str = GOVERNANCE_SYSTEM_ID,
    ) -> AuditRecord:
        return self._write(
            event_type = AuditEventType.CERTIFICATION,
            record     = record,
            actor_id   = actor_id,
            payload    = {"cert_id": cert_id},
        )

    def record_expiry(
        self,
        record:   QualityRecord,
        actor_id: str = GOVERNANCE_SYSTEM_ID,
    ) -> AuditRecord:
        return self._write(
            event_type = AuditEventType.EXPIRY,
            record     = record,
            actor_id   = actor_id,
            payload    = {},
        )

    def record_drift_alert(
        self,
        source_id:  str,
        drift_type: str,
        delta:      float,
        metadata:   dict[str, Any] | None = None,
    ) -> AuditRecord:
        entry = AuditRecord(
            event_type   = AuditEventType.DRIFT_ALERT,
            source_id    = source_id,
            actor_id     = GOVERNANCE_SYSTEM_ID,
            payload      = {
                "drift_type": drift_type,
                "delta":      round(delta, 4),
            },
            metadata = metadata or {},
        )
        self._registry.append(entry)
        return entry

    # -- Internal ──────────────────────────────────────────────────────────────

    def _write(
        self,
        event_type: AuditEventType,
        record:     QualityRecord,
        actor_id:   str,
        payload:    dict[str, Any],
    ) -> AuditRecord:
        entry = AuditRecord(
            event_type   = event_type,
            record_id    = record.record_id,
            product_id   = record.product_id,
            product_type = record.product_type,
            source_id    = record.source_id,
            actor_id     = actor_id,
            payload      = payload,
        )
        self._registry.append(entry)
        record.audit_ids.append(entry.audit_id)
        return entry


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock            = threading.Lock()
_RECORDER: AuditRecorder | None     = None


def get_audit_recorder() -> AuditRecorder:
    global _RECORDER
    if _RECORDER is None:
        with _LOCK:
            if _RECORDER is None:
                _RECORDER = AuditRecorder()
    return _RECORDER


def reset_audit_recorder() -> None:
    global _RECORDER
    with _LOCK:
        _RECORDER = None
