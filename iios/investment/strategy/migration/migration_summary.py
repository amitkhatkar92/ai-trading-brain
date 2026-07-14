"""iios/investment/strategy/migration/migration_summary.py
Aggregated summary across all strategy migrations in one run.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.migration_report import (
    MigrationReport,
    RECOMMEND_APPROVE,
    RECOMMEND_REJECT,
    RECOMMEND_REVIEW,
)
from iios.investment.strategy.migration.migration_status import MigrationStatus
from iios.investment.strategy.migration.migration_session import MigrationSession


@dataclass(frozen=True)
class MigrationSummary:
    """
    Immutable summary of a full migration batch run.
    """
    summary_id:          str
    total_strategies:    int
    completed:           int
    failed:              int
    rolled_back:         int
    approval_pending:    int

    approve_recommended: int
    reject_recommended:  int
    review_recommended:  int

    success_rate:        float      # completed / total (%)
    avg_confidence:      float
    reports:             List[MigrationReport]
    generated_at:        datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":         self.summary_id,
            "total_strategies":   self.total_strategies,
            "completed":          self.completed,
            "failed":             self.failed,
            "rolled_back":        self.rolled_back,
            "approval_pending":   self.approval_pending,
            "approve_recommended": self.approve_recommended,
            "reject_recommended": self.reject_recommended,
            "review_recommended": self.review_recommended,
            "success_rate":       round(self.success_rate, 2),
            "avg_confidence":     round(self.avg_confidence, 2),
            "generated_at":       self.generated_at.isoformat(),
            "reports":            [r.to_dict() for r in self.reports],
        }

    def approve_candidates(self) -> List[MigrationReport]:
        return [r for r in self.reports if r.approval_recommendation == RECOMMEND_APPROVE]

    def reject_candidates(self) -> List[MigrationReport]:
        return [r for r in self.reports if r.approval_recommendation == RECOMMEND_REJECT]

    def review_candidates(self) -> List[MigrationReport]:
        return [r for r in self.reports if r.approval_recommendation == RECOMMEND_REVIEW]


class MigrationSummaryBuilder:
    """Builds a MigrationSummary from completed sessions and their reports."""

    def build(
        self,
        sessions: List[MigrationSession],
        reports:  List[MigrationReport],
    ) -> MigrationSummary:
        total        = len(sessions)
        completed    = sum(1 for s in sessions if s.status == MigrationStatus.COMPLETED)
        failed       = sum(1 for s in sessions if s.status == MigrationStatus.FAILED)
        rolled_back  = sum(1 for s in sessions if s.status == MigrationStatus.ROLLED_BACK)
        pending      = sum(1 for s in sessions if s.status == MigrationStatus.APPROVAL_PENDING)

        approve_cnt  = sum(1 for r in reports if r.approval_recommendation == RECOMMEND_APPROVE)
        reject_cnt   = sum(1 for r in reports if r.approval_recommendation == RECOMMEND_REJECT)
        review_cnt   = sum(1 for r in reports if r.approval_recommendation == RECOMMEND_REVIEW)

        success_rate = (completed / total * 100) if total > 0 else 0.0

        confidences  = [r.confidence_score for r in reports]
        avg_conf     = sum(confidences) / len(confidences) if confidences else 0.0

        return MigrationSummary(
            summary_id=str(uuid.uuid4()),
            total_strategies=total,
            completed=completed,
            failed=failed,
            rolled_back=rolled_back,
            approval_pending=pending,
            approve_recommended=approve_cnt,
            reject_recommended=reject_cnt,
            review_recommended=review_cnt,
            success_rate=round(success_rate, 2),
            avg_confidence=round(avg_conf, 2),
            reports=list(reports),
            generated_at=datetime.now(timezone.utc),
        )
