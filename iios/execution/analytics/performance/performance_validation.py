"""
iios/execution/analytics/performance/performance_validation.py
==============================================================
PerformanceValidator — validates PerformanceRequest and
PerformanceContext before the analytics cycle runs.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import AggregationWindow
from .exceptions import PerformanceValidationError
from .performance_context import PerformanceContext
from .performance_request import PerformanceRequest


@dataclass(frozen=True)
class PerformanceValidationResult:
    """Result of a validation pass."""

    is_valid: bool
    errors:   Tuple[str, ...] = field(default_factory=tuple)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def _ok() -> PerformanceValidationResult:
    return PerformanceValidationResult(is_valid=True, errors=())


def _fail(errors: List[str]) -> PerformanceValidationResult:
    return PerformanceValidationResult(is_valid=False, errors=tuple(errors))


class PerformanceValidator:
    """
    Validates requests and contexts for the Performance Analytics Framework.

    Validation is synchronous and stateless.  Thread-safe.
    """

    def validate_request(self, request: PerformanceRequest) -> PerformanceValidationResult:
        errors: List[str] = []
        if not request.request_id:
            errors.append("request_id is required")
        if request.domain is None:
            errors.append("domain is required")
        if request.window is None:
            errors.append("window is required")
        if request.window == AggregationWindow.CUSTOM and request.priority < 1:
            # no specific check for custom_window on request; context carries it
            pass
        if request.priority < 1 or request.priority > 10:
            errors.append(f"priority must be 1-10, got {request.priority}")
        return _ok() if not errors else _fail(errors)

    def validate_context(self, context: PerformanceContext) -> PerformanceValidationResult:
        errors: List[str] = []
        if not context.context_id:
            errors.append("context_id is required")
        if not context.request_id:
            errors.append("request_id is required")
        if context.domain is None:
            errors.append("domain is required")
        if context.window is None:
            errors.append("window is required")
        if context.window == AggregationWindow.CUSTOM and context.custom_window_seconds <= 0.0:
            errors.append(
                "custom_window_seconds must be positive for CUSTOM window"
            )
        return _ok() if not errors else _fail(errors)

    def validate_and_raise(
        self,
        request: PerformanceRequest,
        context: Optional[PerformanceContext] = None,
    ) -> None:
        """Validate request (and optional context). Raise on failure."""
        result = self.validate_request(request)
        if not result.is_valid:
            raise PerformanceValidationError(errors=result.errors)
        if context is not None:
            ctx_result = self.validate_context(context)
            if not ctx_result.is_valid:
                raise PerformanceValidationError(errors=ctx_result.errors)
