"""iios/investment/portfolio/construction/readiness_validator.py

Determines whether a portfolio blueprint is operationally ready —
i.e., safe to pass to the execution layer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    HealthStatus,
    ValidationCategory,
)
from iios.investment.portfolio.construction.validation_report import (
    ValidationFinding,
    ValidationReport,
    _fail,
    _pass,
    _warn,
    build_report,
)


@dataclass(frozen=True)
class ReadinessAssessment:
    """
    Binary readiness verdict for a portfolio blueprint.

    is_ready is True only when:
      • No HARD constraint violations
      • No FAILED validation findings from portfolio or construction validators
      • Blueprint has at least one position
      • Blueprint has a valid portfolio_id
    """

    assessment_id:    str               = field(default_factory=lambda: __import__("uuid").uuid4().__str__())
    blueprint_id:     str               = ""
    portfolio_id:     str               = ""

    is_ready:         bool              = False
    health_status:    HealthStatus      = HealthStatus.UNKNOWN

    blocking_reasons: Tuple[str, ...]   = field(default_factory=tuple)
    warnings:         Tuple[str, ...]   = field(default_factory=tuple)

    constraint_compliant:   bool        = False
    portfolio_valid:        bool        = False
    construction_valid:     bool        = False

    assessed_at:      float             = field(default_factory=time.time)
    metadata:         Dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id":       self.assessment_id,
            "blueprint_id":        self.blueprint_id,
            "portfolio_id":        self.portfolio_id,
            "is_ready":            self.is_ready,
            "health_status":       self.health_status.value,
            "blocking_reasons":    list(self.blocking_reasons),
            "warnings":            list(self.warnings),
            "constraint_compliant":self.constraint_compliant,
            "portfolio_valid":     self.portfolio_valid,
            "construction_valid":  self.construction_valid,
            "assessed_at":         self.assessed_at,
        }


class ReadinessValidator:
    """
    Aggregates constraint and validation reports into a binary readiness verdict.

    Accepts pre-computed ConstraintReport, portfolio ValidationReport,
    and construction ValidationReport, then determines overall readiness.
    """

    VALIDATOR_NAME = "readiness_validator"

    def validate(
        self,
        blueprint: Any,
        constraint_report: Any,           # ConstraintReport
        portfolio_report:  ValidationReport,
        construction_report: ValidationReport,
    ) -> ReadinessAssessment:
        """
        Produce a ReadinessAssessment from pre-computed reports.
        """
        blocking: List[str] = []
        warnings: List[str] = []

        # 1. Blueprint must have positions
        if blueprint.is_empty:
            blocking.append("Blueprint has no positions")

        # 2. Portfolio_id must be set
        if not blueprint.portfolio_id:
            blocking.append("Blueprint missing portfolio_id")

        # 3. HARD constraint violations block readiness
        if not constraint_report.is_compliant:
            for check in constraint_report.checks:
                from iios.investment.portfolio.construction.construction_types import (
                    ConstraintOutcome, ConstraintSeverity,
                )
                if (check.outcome == ConstraintOutcome.VIOLATED
                        and check.severity == ConstraintSeverity.HARD):
                    blocking.append(f"Constraint violation [{check.constraint_name}]: {check.message}")

        # 4. FAILED portfolio validation findings block readiness
        if not portfolio_report.is_valid:
            for f in portfolio_report.failed_findings:
                blocking.append(f"Portfolio validation [{f.rule}]: {f.message}")

        # 5. FAILED construction validation findings block readiness
        if not construction_report.is_valid:
            for f in construction_report.failed_findings:
                blocking.append(f"Construction validation [{f.rule}]: {f.message}")

        # 6. Warnings are advisory only
        for check in constraint_report.warnings:
            warnings.append(f"Constraint warning [{check.constraint_name}]: {check.message}")
        for f in portfolio_report.warning_findings:
            warnings.append(f"Portfolio warning [{f.rule}]: {f.message}")
        for f in construction_report.warning_findings:
            warnings.append(f"Construction warning [{f.rule}]: {f.message}")

        is_ready = len(blocking) == 0
        if is_ready:
            health = HealthStatus.HEALTHY if not warnings else HealthStatus.DEGRADED
        else:
            health = HealthStatus.UNHEALTHY

        return ReadinessAssessment(
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            is_ready=is_ready,
            health_status=health,
            blocking_reasons=tuple(blocking),
            warnings=tuple(warnings),
            constraint_compliant=constraint_report.is_compliant,
            portfolio_valid=portfolio_report.is_valid,
            construction_valid=construction_report.is_valid,
        )

    def validate_and_report(
        self,
        blueprint: Any,
        constraint_report: Any,
        portfolio_report: ValidationReport,
        construction_report: ValidationReport,
    ) -> Tuple[ReadinessAssessment, ValidationReport]:
        """
        Convenience: returns both a ReadinessAssessment and a ValidationReport
        summarising all readiness findings.
        """
        t0 = time.monotonic()
        assessment = self.validate(
            blueprint, constraint_report, portfolio_report, construction_report
        )

        findings: List[ValidationFinding] = []
        for reason in assessment.blocking_reasons:
            findings.append(_fail(
                ValidationCategory.READINESS, "readiness_check", reason,
            ))
        for w in assessment.warnings:
            findings.append(_warn(
                ValidationCategory.READINESS, "readiness_warning", w,
            ))
        if assessment.is_ready:
            findings.append(_pass(
                ValidationCategory.READINESS, "overall_readiness",
                "Portfolio blueprint is ready for execution",
            ))

        report = build_report(
            findings,
            validator=self.VALIDATOR_NAME,
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            duration_ms=(time.monotonic() - t0) * 1000.0,
        )
        return assessment, report
