"""iios/execution/risk/integration/execution_risk_validation.py
==================================================
IntegrationValidator — stateless validator for integration layer inputs.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Tuple

from .exceptions import RequestValidationError
from .execution_risk_context import ExecutionContext
from .execution_risk_request import ExecutionRiskRequest


@dataclass(frozen=True)
class ValidationReport:
    """Result of a validation pass on an integration request or context."""

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    def __bool__(self) -> bool:
        return self.is_valid

    def raise_if_invalid(self, context: str = "") -> None:
        if not self.is_valid:
            msg = "; ".join(self.errors)
            if context:
                msg = f"[{context}] {msg}"
            raise RequestValidationError(msg)


class IntegrationValidator:
    """
    Stateless validator for integration layer inputs.

    All validate_* methods return ValidationReport — they do NOT raise.
    Use raise_if_invalid() or ValidationReport.raise_if_invalid() to convert
    to exceptions.
    """

    @staticmethod
    def validate_context(context: ExecutionContext) -> ValidationReport:
        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(context, ExecutionContext):
            return ValidationReport(False, ("context must be an ExecutionContext instance",), ())

        if not context.execution_id:
            errors.append("execution_id is required")
        if not context.order_id:
            errors.append("order_id is required")
        if context.quantity < 0:
            errors.append("quantity must be non-negative")
        if context.price < 0:
            errors.append("price must be non-negative")
        if context.timestamp > time.time() + 60:
            warnings.append("context.timestamp is in the future")

        return ValidationReport(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_request(request: ExecutionRiskRequest) -> ValidationReport:
        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(request, ExecutionRiskRequest):
            return ValidationReport(False, ("request must be an ExecutionRiskRequest instance",), ())

        if not request.request_id:
            errors.append("request_id is required")

        if request.execution_context is None:
            errors.append("execution_context is required")
        else:
            ctx_report = IntegrationValidator.validate_context(request.execution_context)
            errors.extend(ctx_report.errors)
            warnings.extend(ctx_report.warnings)

        if request.is_expired:
            errors.append(
                f"request has expired (age={request.age_ms:.0f}ms > timeout={request.timeout_ms:.0f}ms)"
            )

        if request.timeout_ms < 0:
            errors.append("timeout_ms must be non-negative")

        return ValidationReport(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_request_and_raise(
        request: ExecutionRiskRequest,
        context: str = "",
    ) -> None:
        report = IntegrationValidator.validate_request(request)
        if not report.is_valid:
            msg = "; ".join(report.errors)
            if context:
                msg = f"[{context}] {msg}"
            raise RequestValidationError(msg)
