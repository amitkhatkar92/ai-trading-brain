"""
iios/intelligence/governance/audit/audit_engine.py
==================================================
AuditEngine — thin orchestration layer over Registry + Recorder + Report.
AuditManager — convenience façade (same instance, different alias).
"""
from __future__ import annotations

import threading
from typing import Any

from .audit_record import AuditRecord
from .audit_recorder import AuditRecorder, get_audit_recorder
from .audit_registry import AuditRegistry, get_audit_registry
from .audit_report import AuditReport, build_audit_report
from ..quality_constants import AuditEventType
from ..quality_result import QualityRecord


class AuditEngine:
    """
    Orchestrates audit recording, retrieval, and reporting.
    """

    def __init__(self) -> None:
        self._registry: AuditRegistry = get_audit_registry()
        self._recorder: AuditRecorder = get_audit_recorder()

    # -- Write ─────────────────────────────────────────────────────────────────

    def record_evaluation(self, record: QualityRecord, actor_id: str = "") -> AuditRecord:
        return self._recorder.record_evaluation(record, actor_id=actor_id or "")

    def record_approval(
        self,
        record:   QualityRecord,
        actor_id: str = "",
        reason:   str = "",
    ) -> AuditRecord:
        return self._recorder.record_approval(record, actor_id=actor_id, reason=reason)

    def record_rejection(
        self,
        record:  QualityRecord,
        reason:  str = "",
        actor_id: str = "",
    ) -> AuditRecord:
        return self._recorder.record_rejection(record, reason=reason, actor_id=actor_id)

    def record_certification(
        self,
        record:  QualityRecord,
        cert_id: str,
        actor_id: str = "",
    ) -> AuditRecord:
        return self._recorder.record_certification(record, cert_id=cert_id, actor_id=actor_id)

    def record_drift_alert(
        self,
        source_id:  str,
        drift_type: str,
        delta:      float,
    ) -> AuditRecord:
        return self._recorder.record_drift_alert(source_id, drift_type, delta)

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, audit_id: str) -> AuditRecord:
        return self._registry.get(audit_id)

    def for_product(self, product_id: str) -> list[AuditRecord]:
        return self._registry.for_product(product_id)

    def for_source(self, source_id: str) -> list[AuditRecord]:
        return self._registry.for_source(source_id)

    def for_event_type(self, event_type: AuditEventType) -> list[AuditRecord]:
        return self._registry.for_event_type(event_type)

    def recent(self, n: int = 100) -> list[AuditRecord]:
        return self._registry.recent(n)

    # -- Report ────────────────────────────────────────────────────────────────

    def report(
        self,
        product_id: str = "*",
        source_id:  str = "*",
    ) -> AuditReport:
        if product_id != "*":
            records = self._registry.for_product(product_id)
        elif source_id != "*":
            records = self._registry.for_source(source_id)
        else:
            records = self._registry.all()
        return build_audit_report(records, product_id=product_id, source_id=source_id)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        s = self._registry.stats()
        s["engine"] = "AuditEngine"
        return s


# AuditManager is an alias for the same class
AuditManager = AuditEngine


# ── Singletons ─────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock        = threading.Lock()
_ENGINE:  AuditEngine | None   = None
_MANAGER: AuditManager | None  = None


def get_audit_engine() -> AuditEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = AuditEngine()
    return _ENGINE


def reset_audit_engine() -> None:
    global _ENGINE, _MANAGER
    with _LOCK:
        _ENGINE  = None
        _MANAGER = None


def get_audit_manager() -> AuditManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = AuditManager()
    return _MANAGER


def reset_audit_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
