"""
iios/intelligence/governance/evaluation/evaluation_engine.py
============================================================
EvaluationEngine — runs the full governance pipeline end-to-end and
returns a QualityRecord ready for the Decision Layer.

Pipeline (per product):
  1. QualityManager.evaluate()         — dimension scoring + composite
  2. ExplanationEngine.explain()       — build traces
  3. AuditEngine.record_evaluation()   — audit event
  4. CertificationEngine.certify()     — attempt cert (best-effort)
  5. DriftDetector.record_sample()     — monitoring update
  6. PerformanceTracker.record()       — metrics
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from ..audit.audit_engine import AuditEngine, get_audit_engine
from ..certification.certification_engine import (
    CertificationEngine,
    get_certification_engine,
)
from ..explainability.explanation_engine import (
    ExplanationEngine,
    get_explanation_engine,
)
from ..monitoring.drift_detector import DriftDetector, get_drift_detector
from ..monitoring.performance_tracker import (
    PerformanceTracker,
    get_governance_performance_tracker,
)
from ..quality.quality_manager import QualityManager, get_quality_manager
from ..quality_constants import IntelligenceType
from ..quality_exceptions import CertificationFailedError
from ..quality_result import QualityRecord


class EvaluationEngine:
    """
    Orchestrates the complete governance evaluation pipeline.
    Thread-safe; all sub-engine calls are synchronous.
    """

    def __init__(self) -> None:
        self._quality:   QualityManager       = get_quality_manager()
        self._explain:   ExplanationEngine    = get_explanation_engine()
        self._audit:     AuditEngine          = get_audit_engine()
        self._cert:      CertificationEngine  = get_certification_engine()
        self._drift:     DriftDetector        = get_drift_detector()
        self._perf:      PerformanceTracker   = get_governance_performance_tracker()
        self._lock:      threading.RLock      = threading.RLock()
        self._count:     int                  = 0

    # -- Core pipeline ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      Any,
        source_id:    str = "",
        metadata:     dict[str, Any] | None = None,
    ) -> QualityRecord:
        meta = metadata or {}

        # 1. Quality scoring
        record = self._quality.evaluate(
            product_id   = product_id,
            product_type = product_type,
            content      = content,
            source_id    = source_id,
            metadata     = meta,
        )

        # 2. Explanation
        self._explain.explain(record)

        # 3. Audit
        self._audit.record_evaluation(record)

        # 4. Certification (best-effort — failures stored but pipeline continues)
        try:
            self._cert.certify(record)
        except CertificationFailedError:
            pass   # certification_status already set on record

        # 5. Monitoring
        confidence = record.dimension_scores.get("confidence", record.quality_score)
        self._drift.record_sample(
            source_id        = source_id or "unknown",
            quality_score    = record.quality_score,
            confidence_score = confidence,
        )

        # 6. Performance tracking
        self._perf.record(source_id or "unknown", "quality_score", record.quality_score)
        self._perf.record(source_id or "unknown", "confidence", confidence)

        with self._lock:
            self._count += 1

        return record

    # -- Batch ─────────────────────────────────────────────────────────────────

    def batch_evaluate(
        self,
        products: list[dict[str, Any]],
    ) -> list[QualityRecord]:
        """
        Evaluate a list of products.
        Each dict must contain: product_id, product_type, content.
        Optional keys: source_id, metadata.
        """
        results: list[QualityRecord] = []
        for p in products:
            record = self.evaluate(
                product_id   = p["product_id"],
                product_type = p["product_type"],
                content      = p["content"],
                source_id    = p.get("source_id", ""),
                metadata     = p.get("metadata"),
            )
            results.append(record)
        return results

    # -- Async wrapper ─────────────────────────────────────────────────────────

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

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            count = self._count
        return {
            "total_evaluated": count,
            "quality":         self._quality.stats(),
            "audit":           self._audit.stats(),
            "certification":   self._cert.stats(),
            "drift":           self._drift.stats(),
            "performance":     self._perf.stats(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock             = threading.Lock()
_ENGINE: EvaluationEngine | None   = None


def get_evaluation_engine() -> EvaluationEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = EvaluationEngine()
    return _ENGINE


def reset_evaluation_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
