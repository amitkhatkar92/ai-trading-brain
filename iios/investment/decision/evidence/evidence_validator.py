"""iios/investment/decision/evidence/evidence_validator.py
EvidenceValidator — orchestrates freshness, consistency, and coverage checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.evidence.evidence_constants import EvidenceValidationStatus
from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.freshness_validator import FreshnessValidator, FreshnessReport
from iios.investment.decision.evidence.consistency_checker import ConsistencyChecker, ConsistencyReport
from iios.investment.decision.evidence.coverage_validator import CoverageValidator, CoverageReport


@dataclass(frozen=True)
class ValidationResult:
    freshness:    FreshnessReport
    consistency:  ConsistencyReport
    coverage:     CoverageReport
    overall:      EvidenceValidationStatus
    refreshed_items: Tuple[EvidenceItem, ...]

    @property
    def is_publishable(self) -> bool:
        return self.overall.allows_publishing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":          self.overall.value,
            "is_publishable":   self.is_publishable,
            "freshness": {
                "total":         self.freshness.total,
                "stale":         self.freshness.stale,
                "avg_freshness": self.freshness.avg_freshness,
                "stale_keys":    list(self.freshness.stale_keys),
            },
            "consistency": {
                "conflict_count":   self.consistency.conflict_count,
                "score":            self.consistency.consistency_score,
            },
            "coverage": {
                "coverage_fraction": self.coverage.coverage_fraction,
                "missing_required":  list(self.coverage.missing_required),
                "status":            self.coverage.validation_status.value,
            },
        }


class EvidenceValidator:
    """Runs all three validation checks and computes an overall ValidationStatus."""

    def __init__(
        self,
        freshness_validator: FreshnessValidator | None = None,
        consistency_checker: ConsistencyChecker | None = None,
        coverage_validator:  CoverageValidator  | None = None,
    ) -> None:
        self._fresh  = freshness_validator  or FreshnessValidator()
        self._consis = consistency_checker  or ConsistencyChecker()
        self._cov    = coverage_validator   or CoverageValidator()

    def validate(self, items: List[EvidenceItem]) -> ValidationResult:
        # 1 — Freshness (also refreshes freshness_scores)
        refreshed, fresh_report = self._fresh.validate(items)

        # 2 — Consistency
        consis_report = self._consis.check(refreshed)

        # 3 — Coverage
        cov_report    = self._cov.validate(refreshed)

        # 4 — Aggregate
        overall = self._aggregate(fresh_report, consis_report, cov_report)

        return ValidationResult(
            freshness=fresh_report,
            consistency=consis_report,
            coverage=cov_report,
            overall=overall,
            refreshed_items=tuple(refreshed),
        )

    @staticmethod
    def _aggregate(
        fresh:   FreshnessReport,
        consis:  ConsistencyReport,
        cov:     CoverageReport,
    ) -> EvidenceValidationStatus:
        if cov.validation_status == EvidenceValidationStatus.INSUFFICIENT:
            return EvidenceValidationStatus.INSUFFICIENT
        if not consis.is_acceptable:
            return EvidenceValidationStatus.FAILED
        if not fresh.is_acceptable:
            return EvidenceValidationStatus.PASSED_WITH_GAPS
        if cov.validation_status == EvidenceValidationStatus.PASSED_WITH_GAPS:
            return EvidenceValidationStatus.PASSED_WITH_GAPS
        return EvidenceValidationStatus.PASSED
