"""
market_validation.py — iios.market.engine
============================================
Input validation for market engine workflow requests.

Performs structural and semantic checks before a request is processed:
  1. Identifier consistency
  2. Workflow type validity
  3. Priority validity
  4. Inputs schema
  5. Context consistency
  6. Lifecycle readiness

No business logic.  All checks are structural gate-keepers only.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .constants import (
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    MarketWorkflowType,
    SchedulerPriority,
)
from .market_request import MarketRequest
from .exceptions import MarketEngineValidationError


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketEngineValidationCheckResult:
    """Result of a single validation check."""
    check_name: str
    passed:     bool
    message:    str = ""


@dataclass
class MarketEngineValidationResult:
    """Aggregate result of all validation checks for a request."""
    checks: List[MarketEngineValidationCheckResult] = field(default_factory=list)

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

class MarketEngineValidator:
    """
    Validates market requests before they enter the execution pipeline.

    Parameters
    ----------
    max_sessions :    Active session limit (used for lifecycle readiness check).
    active_count_fn : Callable returning current active session count.
    """

    def __init__(
        self,
        max_sessions:    int                  = DEFAULT_MAX_CONCURRENT_SESSIONS,
        active_count_fn: Optional[callable]   = None,
    ) -> None:
        self._max_sessions    = max_sessions
        self._active_count_fn = active_count_fn

    def validate_request(
        self,
        request: MarketRequest,
    ) -> MarketEngineValidationResult:
        """
        Run all six validation checks.

        Returns
        -------
        MarketEngineValidationResult
        """
        result = MarketEngineValidationResult()
        result.checks.append(self._check_identifier_consistency(request))
        result.checks.append(self._check_workflow_type(request))
        result.checks.append(self._check_priority(request))
        result.checks.append(self._check_inputs_schema(request))
        result.checks.append(self._check_context_consistency(request))
        result.checks.append(self._check_lifecycle_readiness(request))
        return result

    def validate_or_raise(self, request: MarketRequest) -> None:
        """Run validation and raise MarketEngineValidationError on failure."""
        result = self.validate_request(request)
        if not result.is_valid:
            raise MarketEngineValidationError(
                "; ".join(result.error_messages),
                failed_checks=tuple(result.failed_checks),
            )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_identifier_consistency(
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        if not request.request_id:
            return MarketEngineValidationCheckResult(
                "identifier_consistency", False, "request_id is empty"
            )
        if not request.market_analysis_id:
            return MarketEngineValidationCheckResult(
                "identifier_consistency", False, "market_analysis_id is empty"
            )
        if not request.exchange:
            return MarketEngineValidationCheckResult(
                "identifier_consistency", False, "exchange is empty"
            )
        if request.context.market_analysis_id != request.market_analysis_id:
            return MarketEngineValidationCheckResult(
                "identifier_consistency",
                False,
                "context.market_analysis_id does not match request.market_analysis_id",
            )
        if request.context.exchange != request.exchange:
            return MarketEngineValidationCheckResult(
                "identifier_consistency",
                False,
                "context.exchange does not match request.exchange",
            )
        return MarketEngineValidationCheckResult("identifier_consistency", True)

    @staticmethod
    def _check_workflow_type(
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        try:
            MarketWorkflowType(request.workflow_type.value)
        except (ValueError, AttributeError):
            return MarketEngineValidationCheckResult(
                "workflow_type_validity",
                False,
                f"Unknown workflow type: {request.workflow_type!r}",
            )
        return MarketEngineValidationCheckResult("workflow_type_validity", True)

    @staticmethod
    def _check_priority(
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        try:
            SchedulerPriority(int(request.priority))
        except (ValueError, AttributeError):
            return MarketEngineValidationCheckResult(
                "priority_validity",
                False,
                f"Unknown priority value: {request.priority!r}",
            )
        return MarketEngineValidationCheckResult("priority_validity", True)

    @staticmethod
    def _check_inputs_schema(
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        if not isinstance(request.inputs, dict):
            return MarketEngineValidationCheckResult(
                "inputs_schema",
                False,
                "inputs must be a dict",
            )
        return MarketEngineValidationCheckResult("inputs_schema", True)

    @staticmethod
    def _check_context_consistency(
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        if request.context.workflow_type != request.workflow_type:
            return MarketEngineValidationCheckResult(
                "context_consistency",
                False,
                "context.workflow_type does not match request.workflow_type",
            )
        return MarketEngineValidationCheckResult("context_consistency", True)

    def _check_lifecycle_readiness(
        self,
        request: MarketRequest,
    ) -> MarketEngineValidationCheckResult:
        if self._active_count_fn is not None:
            try:
                count = self._active_count_fn()
                if count >= self._max_sessions:
                    return MarketEngineValidationCheckResult(
                        "lifecycle_readiness",
                        False,
                        f"Active session limit reached: {count}/{self._max_sessions}",
                    )
            except Exception:   # noqa: BLE001
                pass
        return MarketEngineValidationCheckResult("lifecycle_readiness", True)
