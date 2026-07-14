"""iios/investment/strategy/migration/migration_report.py
Immutable migration report for a single strategy.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.migration_status import (
    MigrationStatus,
    CompatibilityLevel,
    MigrationRisk,
)
from iios.investment.strategy.migration.validation_report import ValidationReport
from iios.investment.strategy.migration.behavior_validator import BehaviorReport
from iios.investment.strategy.migration.signal_equivalence import EquivalenceResult
from iios.investment.strategy.migration.migration_steps import MigrationStepResult


# ── Approval recommendation constants ─────────────────────────────────────────
RECOMMEND_APPROVE = "APPROVE"
RECOMMEND_REJECT  = "REJECT"
RECOMMEND_REVIEW  = "REVIEW"


@dataclass(frozen=True)
class MigrationReport:
    """
    Complete report for one strategy's migration outcome.
    Immutable — constructed from session data after migration completes.
    """
    report_id:         str
    strategy_id:       str
    strategy_name:     str
    generated_at:      datetime
    migration_status:  MigrationStatus
    compatibility_level: CompatibilityLevel
    risk_level:        MigrationRisk

    validation_report:  Optional[ValidationReport]
    behavior_report:    Optional[BehaviorReport]
    equivalence_result: Optional[EquivalenceResult]
    step_results:       List[MigrationStepResult]

    known_limitations:       List[str]
    approval_recommendation: str      # APPROVE / REJECT / REVIEW
    confidence_score:        float    # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "strategy_id":        self.strategy_id,
            "strategy_name":      self.strategy_name,
            "generated_at":       self.generated_at.isoformat(),
            "migration_status":   self.migration_status.value,
            "compatibility_level": self.compatibility_level.value,
            "risk_level":         self.risk_level.value,
            "approval_recommendation": self.approval_recommendation,
            "confidence_score":   round(self.confidence_score, 2),
            "known_limitations":  self.known_limitations,
            "validation_report":  self.validation_report.to_dict() if self.validation_report else None,
            "behavior_report":    self.behavior_report.to_dict() if self.behavior_report else None,
            "equivalence_result": self.equivalence_result.to_dict() if self.equivalence_result else None,
            "steps":              [s.to_dict() for s in self.step_results],
        }


def build_migration_report(
    strategy_id:        str,
    strategy_name:      str,
    migration_status:   MigrationStatus,
    validation_report:  Optional[ValidationReport]  = None,
    behavior_report:    Optional[BehaviorReport]    = None,
    equivalence_result: Optional[EquivalenceResult] = None,
    step_results:       Optional[List[MigrationStepResult]] = None,
    known_limitations:  Optional[List[str]] = None,
) -> MigrationReport:
    """Construct a MigrationReport with computed recommendation and confidence."""

    # ── Compatibility level ───────────────────────────────────────────────────
    if validation_report:
        compat_str = validation_report.compatibility_level
        compat = {
            "full":             CompatibilityLevel.FULL,
            "partial":          CompatibilityLevel.PARTIAL,
            "requires_adapter": CompatibilityLevel.REQUIRES_ADAPTER,
            "incompatible":     CompatibilityLevel.INCOMPATIBLE,
        }.get(compat_str, CompatibilityLevel.UNKNOWN)
    else:
        compat = CompatibilityLevel.UNKNOWN

    # ── Risk level ────────────────────────────────────────────────────────────
    if compat == CompatibilityLevel.INCOMPATIBLE:
        risk = MigrationRisk.CRITICAL
    elif compat == CompatibilityLevel.REQUIRES_ADAPTER:
        risk = MigrationRisk.MEDIUM
    elif compat == CompatibilityLevel.PARTIAL:
        risk = MigrationRisk.LOW
    else:
        risk = MigrationRisk.LOW

    # ── Confidence score (0–100) ──────────────────────────────────────────────
    confidence = _compute_confidence(
        migration_status, validation_report, behavior_report, equivalence_result
    )

    # ── Approval recommendation ───────────────────────────────────────────────
    recommendation = _compute_recommendation(
        migration_status, validation_report, equivalence_result, confidence
    )

    # ── Known limitations ─────────────────────────────────────────────────────
    limitations = list(known_limitations or [])
    if validation_report and validation_report.interface_gaps:
        limitations.extend(validation_report.interface_gaps)

    return MigrationReport(
        report_id=str(uuid.uuid4()),
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        generated_at=datetime.now(timezone.utc),
        migration_status=migration_status,
        compatibility_level=compat,
        risk_level=risk,
        validation_report=validation_report,
        behavior_report=behavior_report,
        equivalence_result=equivalence_result,
        step_results=step_results or [],
        known_limitations=limitations,
        approval_recommendation=recommendation,
        confidence_score=confidence,
    )


def _compute_confidence(
    status:      MigrationStatus,
    validation:  Optional[ValidationReport],
    behavior:    Optional[BehaviorReport],
    equivalence: Optional[EquivalenceResult],
) -> float:
    if status == MigrationStatus.FAILED:
        return 0.0

    score = 0.0

    # Validation weight 40
    if validation:
        total_checks = max(1, len(validation.checks))
        pass_rate = validation.passed_count / total_checks
        score += pass_rate * 40
    else:
        score += 20   # neutral partial credit

    # Behavior weight 30
    if behavior:
        score += behavior.pass_rate * 30
    else:
        score += 15

    # Equivalence weight 30
    if equivalence:
        score += equivalence.confidence * 0.30
    else:
        score += 15

    return round(min(score, 100.0), 2)


def _compute_recommendation(
    status:      MigrationStatus,
    validation:  Optional[ValidationReport],
    equivalence: Optional[EquivalenceResult],
    confidence:  float,
) -> str:
    if status == MigrationStatus.FAILED:
        return RECOMMEND_REJECT
    if status == MigrationStatus.ROLLED_BACK:
        return RECOMMEND_REJECT
    if validation and validation.has_blocking_issues:
        return RECOMMEND_REJECT
    if equivalence and not equivalence.is_equivalent:
        return RECOMMEND_REVIEW
    if confidence >= 80:
        return RECOMMEND_APPROVE
    if confidence >= 55:
        return RECOMMEND_REVIEW
    return RECOMMEND_REJECT
