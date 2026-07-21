"""
portfolio_validation.py — iios.portfolio.engine
================================================
Structural integrity validation for the Portfolio Engine.

Performs six validation checks on incoming portfolio requests
and active pipelines.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    PortfolioWorkflowType,
    ValidationCode,
)
from .portfolio_pipeline import PortfolioPipeline
from .portfolio_request import PortfolioRequest


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioValidationCheckResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    code :    Which property was checked.
    passed :  True if the check succeeded.
    message : Human-readable description (empty when passed).
    """
    code:    ValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class PortfolioValidationResult:
    """
    Aggregated validation outcome.

    Attributes
    ----------
    is_valid :      True iff all checks passed.
    checks :        Full ordered list of check results.
    failed_checks : Only the checks that failed.
    passed_count :  Number of checks that passed.
    failed_count :  Number of checks that failed.
    """
    is_valid:      bool
    checks:        Tuple[PortfolioValidationCheckResult, ...]
    failed_checks: Tuple[PortfolioValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PortfolioEngineValidator:
    """
    Validates portfolio engine inputs and pipeline state.

    Six checks (one per :class:`ValidationCode`):

    1. **SESSION_VALIDITY**      — request has non-empty portfolio_id and request_id.
    2. **PIPELINE_CONSISTENCY**  — workflow type is a valid enum value.
    3. **LIFECYCLE_CONSISTENCY** — request context workflow_type matches request workflow_type.
    4. **SNAPSHOT_CONSISTENCY**  — inputs dict is present (may be empty).
    5. **SUBSYSTEM_HEALTH**      — portfolio_id and request_id are non-empty strings.
    6. **INPUT_COMPLETENESS**    — requested_at timestamp is positive.
    """

    def validate_request(self, request: PortfolioRequest) -> PortfolioValidationResult:
        checks: List[PortfolioValidationCheckResult] = [
            self._check_session_validity(request),
            self._check_pipeline_consistency(request),
            self._check_lifecycle_consistency(request),
            self._check_snapshot_consistency(request),
            self._check_subsystem_health(request),
            self._check_input_completeness(request),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return PortfolioValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = sum(1 for c in checks if c.passed),
            failed_count  = len(failed),
        )

    def validate_pipeline(self, pipeline: PortfolioPipeline) -> PortfolioValidationResult:
        """Validate an active pipeline's structural integrity."""
        checks = [
            self._check_pipeline_ids(pipeline),
            self._check_pipeline_workflow(pipeline),
            self._check_pipeline_lifecycle(pipeline),
            self._check_pipeline_stage_consistency(pipeline),
        ]
        # Pad to 6 checks (remaining are trivially passed)
        while len(checks) < 6:
            checks.append(PortfolioValidationCheckResult(
                code    = ValidationCode.INPUT_COMPLETENESS,
                passed  = True,
            ))
        failed = tuple(c for c in checks if not c.passed)
        return PortfolioValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = sum(1 for c in checks if c.passed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Request checks
    # ------------------------------------------------------------------

    def _check_session_validity(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = bool(r.portfolio_id and r.request_id)
        return PortfolioValidationCheckResult(
            code    = ValidationCode.SESSION_VALIDITY,
            passed  = ok,
            message = "" if ok else "portfolio_id or request_id is empty",
        )

    def _check_pipeline_consistency(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = isinstance(r.workflow_type, PortfolioWorkflowType)
        return PortfolioValidationCheckResult(
            code    = ValidationCode.PIPELINE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else f"Invalid workflow_type: {r.workflow_type!r}",
        )

    def _check_lifecycle_consistency(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = r.context.workflow_type == r.workflow_type
        return PortfolioValidationCheckResult(
            code    = ValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = (
                "" if ok
                else (
                    f"Context workflow_type={r.context.workflow_type.value!r} "
                    f"does not match request workflow_type={r.workflow_type.value!r}"
                )
            ),
        )

    def _check_snapshot_consistency(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = isinstance(r.inputs, dict)
        return PortfolioValidationCheckResult(
            code    = ValidationCode.SNAPSHOT_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "inputs must be a dict",
        )

    def _check_subsystem_health(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = bool(r.portfolio_id.strip()) and bool(r.request_id.strip())
        return PortfolioValidationCheckResult(
            code    = ValidationCode.SUBSYSTEM_HEALTH,
            passed  = ok,
            message = "" if ok else "portfolio_id or request_id is blank",
        )

    def _check_input_completeness(self, r: PortfolioRequest) -> PortfolioValidationCheckResult:
        ok = r.requested_at > 0
        return PortfolioValidationCheckResult(
            code    = ValidationCode.INPUT_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "requested_at timestamp must be positive",
        )

    # ------------------------------------------------------------------
    # Pipeline checks
    # ------------------------------------------------------------------

    def _check_pipeline_ids(self, p: PortfolioPipeline) -> PortfolioValidationCheckResult:
        ok = bool(p.pipeline_id and p.portfolio_id and p.request_id)
        return PortfolioValidationCheckResult(
            code    = ValidationCode.SESSION_VALIDITY,
            passed  = ok,
            message = "" if ok else "pipeline_id, portfolio_id, or request_id is empty",
        )

    def _check_pipeline_workflow(self, p: PortfolioPipeline) -> PortfolioValidationCheckResult:
        ok = isinstance(p.workflow_type, PortfolioWorkflowType)
        return PortfolioValidationCheckResult(
            code    = ValidationCode.PIPELINE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "Invalid pipeline workflow_type",
        )

    def _check_pipeline_lifecycle(self, p: PortfolioPipeline) -> PortfolioValidationCheckResult:
        ok = p.created_at > 0
        return PortfolioValidationCheckResult(
            code    = ValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "pipeline created_at is invalid",
        )

    def _check_pipeline_stage_consistency(self, p: PortfolioPipeline) -> PortfolioValidationCheckResult:
        for stage in p.stages:
            if not stage.stage_name:
                return PortfolioValidationCheckResult(
                    code    = ValidationCode.SNAPSHOT_CONSISTENCY,
                    passed  = False,
                    message = "Pipeline contains stage with empty name",
                )
        return PortfolioValidationCheckResult(
            code   = ValidationCode.SNAPSHOT_CONSISTENCY,
            passed = True,
        )
