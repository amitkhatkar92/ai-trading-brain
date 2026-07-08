"""
iios/intelligence/governance/governance_engine.py
=================================================
IntelligenceQualityEngine — the mandatory AI governance gateway.

No intelligence product shall be forwarded to the Decision Layer unless
it has passed through this engine's evaluate() call.

Usage
-----
    from iios.intelligence.governance.governance_engine import get_governance_engine

    engine = get_governance_engine()
    engine.initialize()

    record = engine.evaluate(
        product_id   = "hyp:NIFTY:001",
        product_type = IntelligenceType.HYPOTHESIS,
        content      = hypothesis_object,
        source_id    = "hypothesis_engine",
    )
    if record.is_approved:
        # forward to Decision Layer
        ...
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from .audit.audit_record import AuditRecord
from .audit.audit_report import AuditReport
from .certification.certification_record import CertificationRecord
from .evaluation.evaluation_dashboard import DashboardSnapshot
from .governance_manager import GovernanceManager, get_governance_manager
from .monitoring.drift_detector import DriftAlert
from .quality_constants import (
    AuditEventType,
    ExplanationType,
    IntelligenceType,
    GOVERNANCE_ENGINE_VERSION,
)
from .quality_exceptions import (
    GovernanceEngineAlreadyRunningError,
    GovernanceEngineNotInitializedError,
)
from .quality_result import QualityApproval, QualityRecord


class IntelligenceQualityEngine:
    """
    Top-level AI Governance Layer gateway.

    Wraps GovernanceManager and enforces the initialise/shutdown lifecycle.
    All intelligence products MUST be evaluated here before reaching the
    Decision Layer.

    Thread-safe. Supports both synchronous and async evaluation.
    """

    VERSION: str = GOVERNANCE_ENGINE_VERSION

    def __init__(self) -> None:
        self._manager: GovernanceManager | None = None
        self._running: bool = False
        self._lock:    threading.RLock = threading.RLock()

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._running:
                raise GovernanceEngineAlreadyRunningError()
            self._manager = get_governance_manager()
            self._running = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _require_running(self) -> GovernanceManager:
        with self._lock:
            if not self._running or self._manager is None:
                raise GovernanceEngineNotInitializedError()
            return self._manager

    # -- Core governance pipeline ──────────────────────────────────────────────

    def evaluate(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      Any,
        source_id:    str = "",
        metadata:     dict[str, Any] | None = None,
    ) -> QualityRecord:
        """
        Run the complete governance pipeline.

        Returns a QualityRecord.  Check ``record.is_approved`` before
        forwarding to the Decision Layer.
        """
        mgr = self._require_running()
        return mgr.evaluate(
            product_id   = product_id,
            product_type = product_type,
            content      = content,
            source_id    = source_id,
            metadata     = metadata,
        )

    async def evaluate_async(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      Any,
        source_id:    str = "",
        metadata:     dict[str, Any] | None = None,
    ) -> QualityRecord:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.evaluate(product_id, product_type, content, source_id, metadata),
        )

    # -- Approval ──────────────────────────────────────────────────────────────

    def approve(
        self,
        record_id:   str,
        approver_id: str = "",
        reason:      str = "",
    ) -> QualityApproval:
        mgr = self._require_running()
        return mgr.approve(record_id, approver_id=approver_id, reason=reason)

    def reject(self, record_id: str, reason: str = "") -> None:
        mgr = self._require_running()
        mgr.reject(record_id, reason=reason)

    # -- Explainability ────────────────────────────────────────────────────────

    def explain(
        self,
        record_id:        str,
        explanation_type: ExplanationType = ExplanationType.HUMAN_READABLE,
    ) -> Any:
        mgr = self._require_running()
        return mgr.explain(record_id, explanation_type=explanation_type)

    def summary(self, record_id: str) -> str:
        mgr = self._require_running()
        return mgr.summary(record_id)

    # -- Certification ─────────────────────────────────────────────────────────

    def certify(self, record_id: str) -> CertificationRecord:
        mgr = self._require_running()
        return mgr.certify(record_id)

    def revoke_cert(self, cert_id: str, reason: str = "") -> None:
        mgr = self._require_running()
        mgr.revoke_cert(cert_id, reason=reason)

    # -- Audit ─────────────────────────────────────────────────────────────────

    def audit_query(
        self,
        product_id: str = "*",
        source_id:  str = "*",
        event_type: AuditEventType | None = None,
        limit:      int = 100,
    ) -> list[AuditRecord]:
        mgr = self._require_running()
        return mgr.audit_query(
            product_id = product_id,
            source_id  = source_id,
            event_type = event_type,
            limit      = limit,
        )

    def audit_report(
        self,
        product_id: str = "*",
        source_id:  str = "*",
    ) -> AuditReport:
        mgr = self._require_running()
        return mgr.audit_report(product_id=product_id, source_id=source_id)

    # -- Monitoring ────────────────────────────────────────────────────────────

    def check_drift(self, source_id: str) -> list[DriftAlert]:
        mgr = self._require_running()
        return mgr.check_drift(source_id)

    # -- Metrics ───────────────────────────────────────────────────────────────

    def dashboard(self) -> DashboardSnapshot:
        mgr = self._require_running()
        return mgr.dashboard()

    def stats(self) -> dict[str, Any]:
        mgr = self._require_running()
        base = mgr.stats()
        base["engine_version"] = self.VERSION
        return base

    def health(self) -> dict[str, Any]:
        with self._lock:
            running = self._running
        if not running:
            return {"status": "stopped", "engine_version": self.VERSION}
        try:
            mgr = self._require_running()
            h   = mgr.health()
            h["engine_version"] = self.VERSION
            return h
        except Exception as exc:
            return {
                "status":         "error",
                "error":          str(exc),
                "engine_version": self.VERSION,
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock                      = threading.Lock()
_ENGINE: IntelligenceQualityEngine | None   = None


def get_governance_engine() -> IntelligenceQualityEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = IntelligenceQualityEngine()
    return _ENGINE


def reset_governance_engine() -> None:
    global _ENGINE
    with _LOCK:
        if _ENGINE is not None:
            try:
                _ENGINE.shutdown()
            except Exception:
                pass
        _ENGINE = None
