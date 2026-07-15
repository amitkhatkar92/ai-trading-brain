"""iios/investment/portfolio/recommendation/recommendation_validator.py

Comprehensive validation of portfolio recommendations.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from iios.investment.portfolio.recommendation.recommendation_policies import (
    InstitutionalPolicy,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    PortfolioIntelligence, RecommendationAction,
    RecommendationPriority, RecommendationRisk,
    ValidationStatus, now_utc,
)


# ---------------------------------------------------------------------------
# ValidationCheck / ValidationReport (independent of rebalancing module)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationCheck:
    check_id:    str               = ""
    description: str               = ""
    status:      ValidationStatus  = ValidationStatus.PASSED
    detail:      str               = ""
    severity:    str               = "info"

    def to_dict(self) -> dict:
        return {
            "check_id":   self.check_id,
            "status":     self.status.value,
            "detail":     self.detail,
            "severity":   self.severity,
        }


@dataclass(frozen=True)
class RecValidationReport:
    report_id:       str               = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str               = ""
    created_at:      str               = field(default_factory=now_utc)
    overall_status:  ValidationStatus  = ValidationStatus.PASSED
    is_valid:        bool              = True
    checks:          tuple             = field(default_factory=tuple)  # ValidationCheck
    n_passed:        int               = 0
    n_warnings:      int               = 0
    n_failed:        int               = 0
    primary_failure: Optional[str]     = None
    warnings:        tuple             = field(default_factory=tuple)  # str

    def to_dict(self) -> dict:
        return {
            "overall_status":  self.overall_status.value,
            "is_valid":        self.is_valid,
            "n_passed":        self.n_passed,
            "n_warnings":      self.n_warnings,
            "n_failed":        self.n_failed,
            "primary_failure": self.primary_failure,
        }


def _build_report(checks: List[ValidationCheck], portfolio_id: str = "") -> RecValidationReport:
    n_passed   = sum(1 for c in checks if c.status == ValidationStatus.PASSED)
    n_warnings = sum(1 for c in checks if c.status == ValidationStatus.WARNING)
    n_failed   = sum(1 for c in checks if c.status == ValidationStatus.FAILED)

    if n_failed > 0:
        overall = ValidationStatus.FAILED
    elif n_warnings > 0:
        overall = ValidationStatus.WARNING
    else:
        overall = ValidationStatus.PASSED

    failures = [c.detail for c in checks if c.status == ValidationStatus.FAILED]
    warns    = [c.detail for c in checks if c.status == ValidationStatus.WARNING]

    return RecValidationReport(
        portfolio_id    = portfolio_id,
        overall_status  = overall,
        is_valid        = n_failed == 0,
        checks          = tuple(checks),
        n_passed        = n_passed,
        n_warnings      = n_warnings,
        n_failed        = n_failed,
        primary_failure = failures[0] if failures else None,
        warnings        = tuple(warns),
    )


# ---------------------------------------------------------------------------
# Recommendation validator
# ---------------------------------------------------------------------------

class RecommendationValidator:
    """Validates a recommendation against policy, intelligence, and governance rules."""

    def validate(
        self,
        rec:          Any,   # PortfolioRecommendation
        policy:       InstitutionalPolicy,
        intelligence: PortfolioIntelligence,
    ) -> RecValidationReport:
        checks: List[ValidationCheck] = []
        params = policy.parameters

        # 1. Minimum confidence to publish
        confidence = getattr(rec, "confidence", 0.0)
        if confidence < params.min_confidence_to_publish:
            checks.append(ValidationCheck(
                check_id    = "min_confidence",
                description = "Recommendation meets minimum confidence threshold",
                status      = ValidationStatus.FAILED,
                detail      = f"Confidence {confidence:.2%} < minimum {params.min_confidence_to_publish:.2%}",
                severity    = "error",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "min_confidence",
                description = "Recommendation meets minimum confidence threshold",
                status      = ValidationStatus.PASSED,
                detail      = f"Confidence {confidence:.2%} ≥ minimum",
            ))

        # 2. Approval required for high-risk
        risk_level = getattr(rec, "risk_level", RecommendationRisk.LOW)
        if params.require_approval_for_high_risk and risk_level == RecommendationRisk.HIGH:
            requires_approval = getattr(rec, "requires_approval", False)
            if not requires_approval:
                checks.append(ValidationCheck(
                    check_id    = "approval_required",
                    description = "High-risk recommendation flagged for approval",
                    status      = ValidationStatus.WARNING,
                    detail      = "High-risk recommendation requires approval per policy",
                    severity    = "warning",
                ))
            else:
                checks.append(ValidationCheck(
                    check_id    = "approval_required",
                    description = "High-risk recommendation flagged for approval",
                    status      = ValidationStatus.PASSED,
                ))

        # 3. Intelligence readiness: sufficient positions
        if intelligence.n_positions < 1:
            checks.append(ValidationCheck(
                check_id    = "portfolio_readiness",
                description = "Portfolio has sufficient positions",
                status      = ValidationStatus.WARNING,
                detail      = "No positions in portfolio — intelligence may be incomplete",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "portfolio_readiness",
                description = "Portfolio has sufficient positions",
                status      = ValidationStatus.PASSED,
            ))

        # 4. Rationale completeness
        rationale = getattr(rec, "rationale", "")
        if not rationale:
            checks.append(ValidationCheck(
                check_id    = "rationale_completeness",
                description = "Recommendation has rationale",
                status      = ValidationStatus.FAILED,
                detail      = "Missing rationale — recommendation is not auditable",
                severity    = "error",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "rationale_completeness",
                description = "Recommendation has rationale",
                status      = ValidationStatus.PASSED,
            ))

        # 5. Traceability: intelligence_id present
        intel_id = getattr(rec, "intelligence_id", "")
        if not intel_id:
            checks.append(ValidationCheck(
                check_id    = "traceability",
                description = "Recommendation is traceable to intelligence snapshot",
                status      = ValidationStatus.WARNING,
                detail      = "Missing intelligence_id — traceability incomplete",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "traceability",
                description = "Recommendation is traceable to intelligence snapshot",
                status      = ValidationStatus.PASSED,
            ))

        # 6. Action vs NO_ACTION for actionable priority
        action   = getattr(rec, "action", RecommendationAction.NO_ACTION)
        priority = getattr(rec, "priority", RecommendationPriority.INFORMATIONAL)
        if (priority in (RecommendationPriority.IMMEDIATE, RecommendationPriority.HIGH)
                and action == RecommendationAction.NO_ACTION):
            checks.append(ValidationCheck(
                check_id    = "action_priority_consistency",
                description = "High-priority recommendation has actionable action",
                status      = ValidationStatus.WARNING,
                detail      = "IMMEDIATE/HIGH priority recommendation has NO_ACTION — check logic",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "action_priority_consistency",
                description = "High-priority recommendation has actionable action",
                status      = ValidationStatus.PASSED,
            ))

        pid = getattr(rec, "portfolio_id", intelligence.portfolio_id)
        return _build_report(checks, pid)
