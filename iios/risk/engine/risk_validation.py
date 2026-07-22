"""
risk_validation.py — iios.risk.engine
========================================
Input validation for risk engine workflow requests.

Performs structural and semantic checks before a request is processed:
  1. Identifier consistency
  2. Workflow type validity
  3. Priority validity
  4. Inputs schema
  5. Context consistency
  6. Lifecycle readiness

No business logic.  All checks are structural gate-keepers only.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .constants import (
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    RiskWorkflowType,
    SchedulerPriority,
)
from .risk_request import RiskRequest
from .exceptions import RiskEngineValidationError


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskEngineValidationCheckResult:
    """Result of a single validation check."""
    check_name: str
    passed:     bool
    message:    str = ""


@dataclass
class RiskEngineValidationResult:
    """Aggregate result of all validation checks for a request."""
    checks:  List[RiskEngineValidationCheckResult] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[str]:
        return [c.check_name for c in self.checks if not c.passed]

    @property
    def error_messages(self) -> List[str]:
        return [c.message for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RiskEngineValidator:
    """
    Validates risk requests before they enter the execution pipeline.

    Parameters
    ----------
    max_sessions :  Active session limit (used for lifecycle readiness check).
    active_count_fn : Callable returning current active session count.
    """

    def __init__(
        self,
        max_sessions:    int                  = DEFAULT_MAX_CONCURRENT_SESSIONS,
        active_count_fn: Optional[callable]   = None,
    ) -> None:
        self._max_sessions    = max_sessions
        self._active_count_fn = active_count_fn

    def validate_request(self, request: RiskRequest) -> RiskEngineValidationResult:
        """
        Run all six validation checks.

        Returns
        -------
        RiskEngineValidationResult
        """
        result = RiskEngineValidationResult()
        result.checks.append(self._check_identifier_consistency(request))
        result.checks.append(self._check_workflow_type(request))
        result.checks.append(self._check_priority(request))
        result.checks.append(self._check_inputs_schema(request))
        result.checks.append(self._check_context_consistency(request))
        result.checks.append(self._check_lifecycle_readiness(request))
        return result

    def validate_or_raise(self, request: RiskRequest) -> None:
        """Run validation and raise RiskEngineValidationError on failure."""
        result = self.validate_request(request)
        if not result.is_valid:
            raise RiskEngineValidationError(
                "; ".join(result.error_messages),
                failed_checks = tuple(result.failed_checks),
            )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_identifier_consistency(
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        if not request.request_id:
            return RiskEngineValidationCheckResult(
                "identifier_consistency", False, "request_id is empty"
            )
        if not request.risk_id:
            return RiskEngineValidationCheckResult(
                "identifier_consistency", False, "risk_id is empty"
            )
        if not request.portfolio_id:
            return RiskEngineValidationCheckResult(
                "identifier_consistency", False, "portfolio_id is empty"
            )
        if request.context.risk_id != request.risk_id:
            return RiskEngineValidationCheckResult(
                "identifier_consistency",
                False,
                "context.risk_id does not match request.risk_id",
            )
        if request.context.portfolio_id != request.portfolio_id:
            return RiskEngineValidationCheckResult(
                "identifier_consistency",
                False,
                "context.portfolio_id does not match request.portfolio_id",
            )
        return RiskEngineValidationCheckResult("identifier_consistency", True)

    @staticmethod
    def _check_workflow_type(
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        try:
            RiskWorkflowType(request.workflow_type.value)
        except (ValueError, AttributeError):
            return RiskEngineValidationCheckResult(
                "workflow_type_validity",
                False,
                f"Unknown workflow type: {request.workflow_type!r}",
            )
        return RiskEngineValidationCheckResult("workflow_type_validity", True)

    @staticmethod
    def _check_priority(
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        try:
            SchedulerPriority(int(request.priority))
        except (ValueError, AttributeError):
            return RiskEngineValidationCheckResult(
                "priority_validity",
                False,
                f"Unknown priority value: {request.priority!r}",
            )
        return RiskEngineValidationCheckResult("priority_validity", True)

    @staticmethod
    def _check_inputs_schema(
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        if not isinstance(request.inputs, dict):
            return RiskEngineValidationCheckResult(
                "inputs_schema",
                False,
                "inputs must be a dict",
            )
        return RiskEngineValidationCheckResult("inputs_schema", True)

    @staticmethod
    def _check_context_consistency(
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        if request.context.workflow_type != request.workflow_type:
            return RiskEngineValidationCheckResult(
                "context_consistency",
                False,
                "context.workflow_type does not match request.workflow_type",
            )
        return RiskEngineValidationCheckResult("context_consistency", True)

    def _check_lifecycle_readiness(
        self,
        request: RiskRequest,
    ) -> RiskEngineValidationCheckResult:
        if self._active_count_fn is not None:
            try:
                count = self._active_count_fn()
                if count >= self._max_sessions:
                    return RiskEngineValidationCheckResult(
                        "lifecycle_readiness",
                        False,
                        f"Session limit reached ({count}/{self._max_sessions})",
                    )
            except Exception as exc:  # noqa: BLE001
                return RiskEngineValidationCheckResult(
                    "lifecycle_readiness",
                    False,
                    f"Failed to query active sessions: {exc}",
                )
        return RiskEngineValidationCheckResult("lifecycle_readiness", True)
