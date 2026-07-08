"""
iios/intelligence/governance/quality/quality_manager.py
========================================================
QualityManager — façade for evaluating and storing quality records.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from .quality_evaluator import QualityEvaluator
from .quality_report import QualityReport, build_report
from .quality_score import QualityScore
from ..quality_constants import (
    IntelligenceType,
    ApprovalStatus,
    QualityLevel,
    MAX_QUALITY_RECORDS,
    MIN_APPROVAL_SCORE,
    GOVERNANCE_SYSTEM_ID,
)
from ..quality_exceptions import (
    QualityRecordNotFoundError,
    QualityAlreadyExistsError,
)
from ..quality_result import QualityRecord, QualityApproval, _level_from_score


class QualityManager:
    """
    Creates, scores, stores, and retrieves QualityRecord objects.
    """

    def __init__(self) -> None:
        self._evaluator: QualityEvaluator    = QualityEvaluator()
        self._records:   dict[str, QualityRecord] = {}
        self._by_product: dict[str, list[str]]    = {}
        self._by_source:  dict[str, list[str]]    = {}
        self._lock:      threading.RLock           = threading.RLock()

    # -- Evaluate & Store ──────────────────────────────────────────────────────

    def evaluate(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      dict[str, Any],
        source_id:    str             = "",
        metadata:     dict[str, Any] | None = None,
    ) -> QualityRecord:
        score_obj = self._evaluator.evaluate(
            product_id   = product_id,
            product_type = product_type,
            content      = content,
            metadata     = metadata,
        )

        # Auto-decide approval based on score
        approval_status = (
            ApprovalStatus.PENDING
            if score_obj.composite >= MIN_APPROVAL_SCORE
            else ApprovalStatus.REJECTED
        )
        rejection_reasons: list[str] = []
        if score_obj.composite < MIN_APPROVAL_SCORE:
            rejection_reasons.append(
                f"Quality score {score_obj.composite:.3f} < minimum {MIN_APPROVAL_SCORE}"
            )

        record = QualityRecord(
            product_id        = product_id,
            product_type      = product_type,
            source_id         = source_id,
            quality_score     = score_obj.composite,
            quality_level     = score_obj.level,
            dimension_scores  = {d.dimension.value: d.score for d in score_obj.dimensions},
            approval_status   = approval_status,
            warnings          = list(score_obj.warnings),
            rejection_reasons = rejection_reasons,
            metadata          = metadata or {},
        )

        with self._lock:
            if len(self._records) >= MAX_QUALITY_RECORDS:
                # Evict the oldest record
                oldest_id = next(iter(self._records))
                self._evict(oldest_id)
            self._records[record.record_id] = record
            self._by_product.setdefault(product_id, []).append(record.record_id)
            self._by_source.setdefault(source_id, []).append(record.record_id)
        return record

    # -- Approval / Rejection ──────────────────────────────────────────────────

    def approve(
        self,
        record_id:   str,
        approver_id: str = GOVERNANCE_SYSTEM_ID,
        reason:      str = "",
    ) -> QualityApproval:
        record = self.get(record_id)
        record.approval_status = ApprovalStatus.APPROVED
        record.touch()
        return QualityApproval(
            record_id     = record_id,
            product_id    = record.product_id,
            approved      = True,
            approver_id   = approver_id,
            reason        = reason or "Passed quality threshold",
            quality_score = record.quality_score,
            quality_level = record.quality_level,
        )

    def reject(
        self,
        record_id: str,
        reason:    str = "",
    ) -> None:
        record = self.get(record_id)
        record.approval_status = ApprovalStatus.REJECTED
        if reason:
            record.rejection_reasons.append(reason)
        record.touch()

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, record_id: str) -> QualityRecord:
        with self._lock:
            r = self._records.get(record_id)
        if r is None:
            raise QualityRecordNotFoundError(record_id)
        return r

    def has(self, record_id: str) -> bool:
        with self._lock:
            return record_id in self._records

    def for_product(self, product_id: str) -> list[QualityRecord]:
        with self._lock:
            ids = list(self._by_product.get(product_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_source(self, source_id: str) -> list[QualityRecord]:
        with self._lock:
            ids = list(self._by_source.get(source_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def all(self) -> list[QualityRecord]:
        with self._lock:
            return list(self._records.values())

    # -- Report ────────────────────────────────────────────────────────────────

    def report(
        self,
        product_id: str | None = None,
        source_id:  str | None = None,
    ) -> QualityReport:
        if product_id:
            records = self.for_product(product_id)
        elif source_id:
            records = self.for_source(source_id)
        else:
            records = self.all()
        return build_report(
            records,
            product_id = product_id or "*",
            source_id  = source_id  or "*",
        )

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total    = len(self._records)
            approved = sum(1 for r in self._records.values()
                           if r.approval_status == ApprovalStatus.APPROVED)
            return {"total": total, "approved": approved, "rejected": total - approved}

    # -- Internal ──────────────────────────────────────────────────────────────

    def _evict(self, record_id: str) -> None:
        r = self._records.pop(record_id, None)
        if r:
            pid_list = self._by_product.get(r.product_id, [])
            if record_id in pid_list:
                pid_list.remove(record_id)
            sid_list = self._by_source.get(r.source_id, [])
            if record_id in sid_list:
                sid_list.remove(record_id)


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock             = threading.Lock()
_MANAGER: QualityManager | None     = None


def get_quality_manager() -> QualityManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = QualityManager()
    return _MANAGER


def reset_quality_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
