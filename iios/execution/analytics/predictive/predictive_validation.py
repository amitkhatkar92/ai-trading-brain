"""
iios/execution/analytics/predictive/predictive_validation.py
============================================================
PredictiveValidator — validates PredictionRequest and PredictiveContext
before a prediction cycle runs.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import ForecastHorizon
from .exceptions import PredictionValidationError
from .predictive_context import PredictiveContext
from .predictive_request import PredictionRequest


@dataclass(frozen=True)
class PredictiveValidationResult:
    """Result of a validation pass."""

    is_valid: bool
    errors:   Tuple[str, ...] = field(default_factory=tuple)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def _ok() -> PredictiveValidationResult:
    return PredictiveValidationResult(is_valid=True, errors=())


def _fail(errors: List[str]) -> PredictiveValidationResult:
    return PredictiveValidationResult(is_valid=False, errors=tuple(errors))


class PredictiveValidator:
    """
    Validates requests and contexts for the Predictive Intelligence Framework.

    Stateless and thread-safe.
    """

    def validate_request(
        self, request: PredictionRequest
    ) -> PredictiveValidationResult:
        errors: List[str] = []
        if not request.request_id:
            errors.append("request_id is required")
        if request.domain is None:
            errors.append("domain is required")
        if request.horizon is None:
            errors.append("horizon is required")
        if request.priority < 1 or request.priority > 10:
            errors.append(f"priority must be 1-10, got {request.priority}")
        return _ok() if not errors else _fail(errors)

    def validate_context(
        self, context: PredictiveContext
    ) -> PredictiveValidationResult:
        errors: List[str] = []
        if not context.context_id:
            errors.append("context_id is required")
        if not context.request_id:
            errors.append("request_id is required")
        if context.domain is None:
            errors.append("domain is required")
        if context.horizon is None:
            errors.append("horizon is required")
        if context.horizon == ForecastHorizon.CUSTOM and context.custom_horizon_seconds <= 0.0:
            errors.append(
                "custom_horizon_seconds must be positive for CUSTOM horizon"
            )
        return _ok() if not errors else _fail(errors)

    def validate_and_raise(
        self,
        request: PredictionRequest,
        context: Optional[PredictiveContext] = None,
    ) -> None:
        """Validate request (and optional context). Raise on failure."""
        result = self.validate_request(request)
        if not result.is_valid:
            raise PredictionValidationError(errors=result.errors)
        if context is not None:
            ctx_result = self.validate_context(context)
            if not ctx_result.is_valid:
                raise PredictionValidationError(errors=ctx_result.errors)
