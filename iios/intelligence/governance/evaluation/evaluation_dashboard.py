"""
iios/intelligence/governance/evaluation/evaluation_dashboard.py
===============================================================
EvaluationDashboard — aggregated snapshot of the governance system.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .evaluation_metrics import (
    approval_rate,
    avg_quality_score,
    certification_rate,
)
from ..quality_constants import ApprovalStatus, CertificationStatus
from ..quality_result import QualityRecord


@dataclass
class DashboardSnapshot:
    """
    Point-in-time snapshot of governance system metrics.
    """

    snapshot_id:              str              = field(default_factory=lambda: str(uuid.uuid4()))
    total_evaluated:          int              = 0
    approved:                 int              = 0
    rejected:                 int              = 0
    pending:                  int              = 0
    certified:                int              = 0
    approval_rate:            float            = 0.0
    certification_rate:       float            = 0.0
    avg_quality:              float            = 0.0
    quality_level_distribution: dict[str, int] = field(default_factory=dict)
    top_sources:              list[dict[str, Any]] = field(default_factory=list)
    drift_alert_count:        int              = 0
    generated_at:             float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":               self.snapshot_id,
            "total_evaluated":           self.total_evaluated,
            "approved":                  self.approved,
            "rejected":                  self.rejected,
            "pending":                   self.pending,
            "certified":                 self.certified,
            "approval_rate":             round(self.approval_rate, 4),
            "certification_rate":        round(self.certification_rate, 4),
            "avg_quality":               round(self.avg_quality, 4),
            "quality_level_distribution": self.quality_level_distribution,
            "top_sources":               self.top_sources,
            "drift_alert_count":         self.drift_alert_count,
            "generated_at":              self.generated_at,
        }


class EvaluationDashboard:
    """
    Builds aggregated DashboardSnapshot from all known QualityRecords.
    Stateless — requires a provider callable that returns current records.
    """

    def __init__(
        self,
        records_provider: Any,      # Callable[[], list[QualityRecord]]
        alerts_provider:  Any = None,  # Callable[[], list[DriftAlert]]
    ) -> None:
        self._records_provider = records_provider
        self._alerts_provider  = alerts_provider

    def snapshot(self, top_n: int = 5) -> DashboardSnapshot:
        records: list[QualityRecord] = self._records_provider()

        approved  = [r for r in records if r.approval_status == ApprovalStatus.APPROVED]
        rejected  = [r for r in records if r.approval_status == ApprovalStatus.REJECTED]
        pending   = [r for r in records if r.approval_status == ApprovalStatus.PENDING]
        certified = [r for r in records
                     if r.certification_status == CertificationStatus.CERTIFIED]

        # Quality level distribution
        level_dist: dict[str, int] = {}
        for r in records:
            level_dist[r.quality_level.value] = level_dist.get(r.quality_level.value, 0) + 1

        # Top sources by count
        source_counts: dict[str, int] = {}
        for r in records:
            source_counts[r.source_id] = source_counts.get(r.source_id, 0) + 1
        top_sources = [
            {"source_id": s, "count": c}
            for s, c in sorted(source_counts.items(), key=lambda x: -x[1])[:top_n]
        ]

        # Drift alerts
        alert_count = 0
        if self._alerts_provider is not None:
            try:
                alert_count = len(self._alerts_provider())
            except Exception:
                pass

        return DashboardSnapshot(
            total_evaluated         = len(records),
            approved                = len(approved),
            rejected                = len(rejected),
            pending                 = len(pending),
            certified               = len(certified),
            approval_rate           = approval_rate(records),
            certification_rate      = certification_rate(records),
            avg_quality             = avg_quality_score(records),
            quality_level_distribution = level_dist,
            top_sources             = top_sources,
            drift_alert_count       = alert_count,
        )

    def source_summary(self, source_id: str) -> dict[str, Any]:
        records = [
            r for r in self._records_provider()
            if r.source_id == source_id
        ]
        return {
            "source_id":          source_id,
            "total":              len(records),
            "approved":           sum(1 for r in records if r.is_approved),
            "rejected":           sum(1 for r in records if r.is_rejected),
            "certified":          sum(1 for r in records if r.is_certified),
            "avg_quality":        round(avg_quality_score(records), 4),
            "approval_rate":      round(approval_rate(records), 4),
            "certification_rate": round(certification_rate(records), 4),
        }
