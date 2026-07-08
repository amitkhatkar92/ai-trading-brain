"""
iios/intelligence/governance/governance_manager.py
==================================================
GovernanceManager — unified façade over all sub-engines.
The Decision Layer should interact exclusively with this class
(or with IntelligenceQualityEngine which wraps it).
"""
from __future__ import annotations

import threading
from typing import Any

from .audit.audit_engine import AuditEngine, get_audit_engine
from .audit.audit_record import AuditRecord
from .audit.audit_report import AuditReport
from .certification.certification_engine import (
    CertificationEngine,
    get_certification_engine,
)
from .certification.certification_record import CertificationRecord
from .evaluation.evaluation_dashboard import DashboardSnapshot, EvaluationDashboard
from .evaluation.evaluation_engine import EvaluationEngine, get_evaluation_engine
from .explainability.explanation_engine import ExplanationEngine, get_explanation_engine
from .monitoring.drift_detector import DriftAlert, DriftDetector, get_drift_detector
from .monitoring.performance_tracker import (
    PerformanceTracker,
    get_governance_performance_tracker,
)
from .quality.quality_manager import QualityManager, get_quality_manager
from .quality_constants import AuditEventType, ExplanationType, IntelligenceType, GOVERNANCE_SYSTEM_ID
from .quality_result import QualityApproval, QualityRecord


class GovernanceManager:
    """
    Single-entry-point governance façade.

    This class holds lazy references to every sub-engine singleton and
    exposes the methods that the Decision Layer (and above) need.
    """

    def __init__(self) -> None:
        self._eval:   EvaluationEngine    = get_evaluation_engine()
        self._quality: QualityManager     = get_quality_manager()
        self._explain: ExplanationEngine  = get_explanation_engine()
        self._audit:  AuditEngine         = get_audit_engine()
        self._cert:   CertificationEngine = get_certification_engine()
        self._drift:  DriftDetector       = get_drift_detector()
        self._perf:   PerformanceTracker  = get_governance_performance_tracker()

        # Dashboard is built lazily on first call
        self._dashboard: EvaluationDashboard | None = None
        self._lock: threading.RLock = threading.RLock()

    # -- Full pipeline ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      Any,
        source_id:    str = "",
        metadata:     dict[str, Any] | None = None,
    ) -> QualityRecord:
        """Run the complete governance pipeline and return the QualityRecord."""
        return self._eval.evaluate(
            product_id   = product_id,
            product_type = product_type,
            content      = content,
            source_id    = source_id,
            metadata     = metadata,
        )

    # -- Approval ──────────────────────────────────────────────────────────────

    def approve(
        self,
        record_id:  str,
        approver_id: str = GOVERNANCE_SYSTEM_ID,
        reason:     str = "",
    ) -> QualityApproval:
        approval = self._quality.approve(record_id, approver_id=approver_id, reason=reason)
        record   = self._quality.get(record_id)
        self._audit.record_approval(record, actor_id=approver_id, reason=reason)
        return approval

    def reject(self, record_id: str, reason: str = "") -> None:
        self._quality.reject(record_id, reason=reason)
        record = self._quality.get(record_id)
        self._audit.record_rejection(record, reason=reason)

    # -- Explainability ────────────────────────────────────────────────────────

    def explain(
        self,
        record_id: str,
        explanation_type: ExplanationType = ExplanationType.HUMAN_READABLE,
    ) -> Any:
        record = self._quality.get(record_id)
        if explanation_type == ExplanationType.HUMAN_READABLE:
            return self._explain.explain_text(record)
        return self._explain.explain(record)

    def summary(self, record_id: str) -> str:
        record = self._quality.get(record_id)
        return self._explain.summary(record)

    # -- Certification ─────────────────────────────────────────────────────────

    def certify(self, record_id: str) -> CertificationRecord:
        record = self._quality.get(record_id)
        cert   = self._cert.certify(record)
        self._audit.record_certification(record, cert_id=cert.cert_id)
        return cert

    def revoke_cert(self, cert_id: str, reason: str = "") -> None:
        self._cert.revoke(cert_id, reason=reason)

    # -- Audit ─────────────────────────────────────────────────────────────────

    def audit_query(
        self,
        product_id:  str = "*",
        source_id:   str = "*",
        event_type:  AuditEventType | None = None,
        limit:       int = 100,
    ) -> list[AuditRecord]:
        if event_type is not None:
            return self._audit.for_event_type(event_type)[:limit]
        if product_id != "*":
            return self._audit.for_product(product_id)[:limit]
        if source_id != "*":
            return self._audit.for_source(source_id)[:limit]
        return self._audit.recent(limit)

    def audit_report(
        self,
        product_id: str = "*",
        source_id:  str = "*",
    ) -> AuditReport:
        return self._audit.report(product_id=product_id, source_id=source_id)

    # -- Monitoring ────────────────────────────────────────────────────────────

    def check_drift(self, source_id: str) -> list[DriftAlert]:
        return self._drift.get_alerts(source_id)

    def all_drift_alerts(self) -> list[DriftAlert]:
        return self._drift.all_alerts()

    # -- Dashboard ─────────────────────────────────────────────────────────────

    def dashboard(self) -> DashboardSnapshot:
        if self._dashboard is None:
            with self._lock:
                if self._dashboard is None:
                    self._dashboard = EvaluationDashboard(
                        records_provider = self._quality.all,
                        alerts_provider  = self._drift.all_alerts,
                    )
        return self._dashboard.snapshot()

    # -- Stats & health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "evaluation": self._eval.stats(),
            "audit":      self._audit.stats(),
            "cert":       self._cert.stats(),
            "drift":      self._drift.stats(),
            "performance": self._perf.stats(),
        }

    def health(self) -> dict[str, Any]:
        return {
            "status":    "healthy",
            "subsystems": {
                "quality_manager":       "ok",
                "explanation_engine":    "ok",
                "audit_engine":          "ok",
                "certification_engine":  "ok",
                "drift_detector":        "ok",
                "performance_tracker":   "ok",
                "evaluation_engine":     "ok",
            },
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock            = threading.Lock()
_MANAGER: GovernanceManager | None = None


def get_governance_manager() -> GovernanceManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = GovernanceManager()
    return _MANAGER


def reset_governance_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
