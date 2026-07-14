"""iios/investment/strategy/migration/migration_confidence.py
Computes a weighted confidence score for a completed migration session.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.validation_report import ValidationReport
from iios.investment.strategy.migration.behavior_validator import BehaviorReport
from iios.investment.strategy.migration.migration_status import MigrationStatus


# ── Grade thresholds ──────────────────────────────────────────────────────────
_GRADE_HIGH   = 80.0
_GRADE_MEDIUM = 55.0


@dataclass(frozen=True)
class MigrationConfidence:
    """
    Weighted composite confidence score for a migration outcome.
    All sub-scores are 0–100 (100 = best).
    """
    strategy_id:         str
    strategy_name:       str
    assessed_at:         datetime

    validation_confidence: float   # Did validation pass cleanly? (0–100)
    behavior_confidence:   float   # Behavior equivalence score (0–100)
    data_completeness:     float   # How complete is legacy metadata? (0–100)
    overall_confidence:    float   # Weighted composite (0–100)
    grade:                 str     # HIGH / MEDIUM / LOW

    def to_dict(self) -> dict:
        return {
            "strategy_id":           self.strategy_id,
            "strategy_name":         self.strategy_name,
            "assessed_at":           self.assessed_at.isoformat(),
            "validation_confidence": round(self.validation_confidence, 2),
            "behavior_confidence":   round(self.behavior_confidence, 2),
            "data_completeness":     round(self.data_completeness, 2),
            "overall_confidence":    round(self.overall_confidence, 2),
            "grade":                 self.grade,
        }

    @classmethod
    def compute(
        cls,
        session:           MigrationSession,
        validation_report: Optional[ValidationReport] = None,
        behavior_report:   Optional[BehaviorReport]   = None,
    ) -> "MigrationConfidence":
        """Compute confidence from session state and available reports."""
        meta = session.metadata

        # ── 1. Validation confidence (weight 40%) ─────────────────────────────
        if validation_report:
            total_checks = max(1, len(validation_report.checks))
            val_conf = (validation_report.passed_count / total_checks) * 100
            if validation_report.has_blocking_issues:
                val_conf = min(val_conf, 30.0)   # cap if blocking errors
        elif session.status == MigrationStatus.FAILED:
            val_conf = 0.0
        else:
            val_conf = 50.0   # no data — neutral

        # ── 2. Behavior confidence (weight 35%) ───────────────────────────────
        if behavior_report and behavior_report.test_case_count > 0:
            beh_conf = behavior_report.pass_rate * 100
        else:
            beh_conf = 50.0   # no tests — neutral

        # ── 3. Data completeness (weight 25%) ─────────────────────────────────
        fields_scored = [
            meta.min_rr > 0,
            meta.max_loss_pct > 0,
            bool(meta.preferred_regimes or meta.compatible_regimes),
            meta.category != "unknown",
            meta.precision is not None,
            meta.sharpe_ratio is not None,
            meta.max_drawdown is not None,
            bool(meta.description),
            bool(meta.tags),
            bool(meta.entry_conditions) or meta.strategy_type.value == "code_based",
        ]
        completeness = (sum(1 for f in fields_scored if f) / len(fields_scored)) * 100

        # ── Weighted composite ────────────────────────────────────────────────
        overall = (
            val_conf     * 0.40
            + beh_conf   * 0.35
            + completeness * 0.25
        )
        overall = round(min(overall, 100.0), 2)

        grade = (
            "HIGH"   if overall >= _GRADE_HIGH   else
            "MEDIUM" if overall >= _GRADE_MEDIUM else
            "LOW"
        )

        return cls(
            strategy_id=meta.strategy_id,
            strategy_name=meta.strategy_name,
            assessed_at=datetime.now(timezone.utc),
            validation_confidence=round(val_conf, 2),
            behavior_confidence=round(beh_conf, 2),
            data_completeness=round(completeness, 2),
            overall_confidence=overall,
            grade=grade,
        )
