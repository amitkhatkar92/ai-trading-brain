"""
iios/intelligence/governance/quality/quality_report.py
=======================================================
QualityReport — aggregated quality assessment for one or many products.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import IntelligenceType, QualityLevel
from ..quality_result import QualityRecord


@dataclass
class QualityReport:
    """
    Snapshot-in-time quality summary for a product or a source engine.

    Can cover:
    - a single product (product_id set, source_id optional)
    - all products from a source (source_id set, product_id="*")
    - the full system  (product_id="*", source_id="*")
    """

    report_id:       str              = field(default_factory=lambda: str(uuid.uuid4()))
    product_id:      str              = "*"
    source_id:       str              = "*"
    total_records:   int              = 0
    approved:        int              = 0
    rejected:        int              = 0
    certified:       int              = 0
    avg_score:       float            = 0.0
    min_score:       float            = 1.0
    max_score:       float            = 0.0
    level_counts:    dict[str, int]   = field(default_factory=dict)
    top_warnings:    list[str]        = field(default_factory=list)
    records_summary: list[dict[str, Any]] = field(default_factory=list)
    generated_at:    float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "product_id":    self.product_id,
            "source_id":     self.source_id,
            "total_records": self.total_records,
            "approved":      self.approved,
            "rejected":      self.rejected,
            "certified":     self.certified,
            "avg_score":     round(self.avg_score, 4),
            "min_score":     round(self.min_score, 4),
            "max_score":     round(self.max_score, 4),
            "level_counts":  self.level_counts,
            "top_warnings":  self.top_warnings,
            "generated_at":  self.generated_at,
        }


def build_report(
    records:    list[QualityRecord],
    product_id: str = "*",
    source_id:  str = "*",
) -> QualityReport:
    """Build a QualityReport from a list of QualityRecord objects."""
    if not records:
        return QualityReport(product_id=product_id, source_id=source_id)

    from ..quality_constants import ApprovalStatus, CertificationStatus

    total       = len(records)
    approved    = sum(1 for r in records if r.approval_status == ApprovalStatus.APPROVED)
    rejected    = sum(1 for r in records if r.approval_status == ApprovalStatus.REJECTED)
    certified   = sum(1 for r in records if r.certification_status == CertificationStatus.CERTIFIED)
    avg_score   = sum(r.quality_score for r in records) / total
    min_score   = min(r.quality_score for r in records)
    max_score   = max(r.quality_score for r in records)

    level_counts: dict[str, int] = {}
    warning_bag:  list[str]      = []
    for r in records:
        level_counts[r.quality_level.value] = level_counts.get(r.quality_level.value, 0) + 1
        warning_bag.extend(r.warnings)

    # Top 5 unique warnings
    seen: set[str] = set()
    top_warnings: list[str] = []
    for w in warning_bag:
        if w not in seen:
            seen.add(w)
            top_warnings.append(w)
        if len(top_warnings) >= 5:
            break

    return QualityReport(
        product_id    = product_id,
        source_id     = source_id,
        total_records = total,
        approved      = approved,
        rejected      = rejected,
        certified     = certified,
        avg_score     = avg_score,
        min_score     = min_score,
        max_score     = max_score,
        level_counts  = level_counts,
        top_warnings  = top_warnings,
    )
