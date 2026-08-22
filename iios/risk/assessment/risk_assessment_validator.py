"""
risk_assessment_validator.py — iios.risk.assessment
=====================================================
Input and result validation for the Risk Assessment Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    MIN_RETURNS_FOR_VAR,
    ValidationCode,
    VERSION,
)
from .exceptions import RiskAssessmentValidationError


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssessmentValidationCheck:
    """Result of a single validation check."""
    code:    ValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class AssessmentValidationResult:
    """Aggregated result of all validation checks."""
    assessment_id: str
    passed:        bool
    checks:        Tuple[AssessmentValidationCheck, ...]
    model_version: str = VERSION

    @property
    def failed_codes(self) -> List[ValidationCode]:
        return [c.code for c in self.checks if not c.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "passed":        self.passed,
            "checks":        [c.to_dict() for c in self.checks],
            "failed_codes":  [c.value for c in self.failed_codes],
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RiskAssessmentValidator:
    """
    Validates :class:`~.risk_assessment_request.RiskAssessmentRequest`
    instances and completed assessment results.

    Validation checks:
    1. Portfolio value is positive.
    2. Policy approval flag is set.
    3. Weights are valid (finite numbers).
    4. Returns series is sufficient for VaR when present.
    5. Limits are non-negative.
    """

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def validate_request(self, request: Any) -> AssessmentValidationResult:
        """
        Validate an assessment request.

        Parameters
        ----------
        request :
            :class:`~.risk_assessment_request.RiskAssessmentRequest` instance.

        Returns
        -------
        AssessmentValidationResult
        """
        checks: List[AssessmentValidationCheck] = []

        # 1. Portfolio value positive
        pv_ok = (
            isinstance(request.portfolio_value, (int, float))
            and request.portfolio_value > 0
        )
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.PORTFOLIO_VALUE_POSITIVE,
            passed  = pv_ok,
            message = "Portfolio value is positive" if pv_ok
                      else f"Portfolio value must be positive, got {request.portfolio_value}",
        ))

        # 2. Policy approved
        approved_ok = bool(request.policy_approved)
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.INPUT_CONSISTENT,
            passed  = approved_ok,
            message = "Policy approval confirmed" if approved_ok
                      else "Request must be policy-approved before assessment",
        ))

        # 3. Weights valid
        weights_ok = all(
            isinstance(w, (int, float)) and not (w != w)  # isnan check
            for w in request.positions.values()
        )
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.WEIGHTS_VALID,
            passed  = weights_ok,
            message = "Position weights are valid" if weights_ok
                      else "Position weights contain invalid values (NaN/non-numeric)",
        ))

        # 4. Returns sufficient
        n_returns = len(request.returns)
        ret_ok = n_returns == 0 or n_returns >= MIN_RETURNS_FOR_VAR
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.RETURNS_SUFFICIENT,
            passed  = ret_ok,
            message = f"Returns series has {n_returns} observations" if ret_ok
                      else f"Insufficient returns: {n_returns} < {MIN_RETURNS_FOR_VAR}",
        ))

        # 5. Limits non-negative
        limits_ok = all(
            isinstance(v, (int, float)) and v >= 0
            for v in request.limits.values()
        )
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.MODEL_CONSISTENT,
            passed  = limits_ok,
            message = "All limits are non-negative" if limits_ok
                      else "Limits contain negative or invalid values",
        ))

        all_passed = all(c.passed for c in checks)
        return AssessmentValidationResult(
            assessment_id = request.assessment_id,
            passed        = all_passed,
            checks        = tuple(checks),
        )

    def validate_request_or_raise(self, request: Any) -> AssessmentValidationResult:
        """
        Validate request and raise on failure.

        Raises
        ------
        RiskAssessmentValidationError
        """
        result = self.validate_request(request)
        if not result.passed:
            raise RiskAssessmentValidationError(
                f"Checks failed: {[c.value for c in result.failed_codes]}",
                failed_checks  = tuple(c.value for c in result.failed_codes),
                assessment_id  = request.assessment_id,
            )
        return result

    # ------------------------------------------------------------------
    # Result validation
    # ------------------------------------------------------------------

    def validate_report(self, report: Any) -> AssessmentValidationResult:
        """Validate a completed :class:`~.risk_assessment_response.RiskAssessmentReport`."""
        checks: List[AssessmentValidationCheck] = []

        # Assessment complete
        complete_ok = getattr(report, "status", None) is not None
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.ASSESSMENT_COMPLETE,
            passed  = complete_ok,
            message = "Report has a valid status" if complete_ok else "Report missing status",
        ))

        # Risk score in valid range
        score = getattr(report, "risk_score", -1.0)
        score_ok = isinstance(score, (int, float)) and 0.0 <= score <= 100.0
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.CALCULATION_INTEGRITY,
            passed  = score_ok,
            message = f"Risk score {score:.2f} in valid range" if score_ok
                      else f"Risk score {score} out of range [0, 100]",
        ))

        # Duration positive
        dur = getattr(report, "duration_s", -1.0)
        dur_ok = isinstance(dur, (int, float)) and dur >= 0
        checks.append(AssessmentValidationCheck(
            code    = ValidationCode.FORECAST_CONSISTENT,
            passed  = dur_ok,
            message = "Duration is non-negative" if dur_ok
                      else f"Duration {dur} is negative",
        ))

        all_passed = all(c.passed for c in checks)
        return AssessmentValidationResult(
            assessment_id = getattr(report, "assessment_id", "unknown"),
            passed        = all_passed,
            checks        = tuple(checks),
        )
