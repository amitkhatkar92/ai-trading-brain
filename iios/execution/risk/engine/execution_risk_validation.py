"""iios/execution/risk/engine/execution_risk_validation.py
==================================================
EngineValidator — stateless request validation for the Execution Risk Engine.

Validates EvaluationRequest, QueryEvaluationRequest, and
post-evaluation rule result sets before they are processed.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .constants import DEFAULT_SEARCH_LIMIT, ValidationCode
from .exceptions import RiskEngineValidationError
from .execution_risk_request import EvaluationRequest, QueryEvaluationRequest, RuleResult


@dataclass(frozen=True)
class ValidationResult:
    """Result of a single validation pass."""

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":      self.is_valid,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "validated_at":  self.validated_at,
        }


def _ok(warnings: List[str] | None = None) -> ValidationResult:
    return ValidationResult(
        is_valid=True,
        errors=(),
        warnings=tuple(warnings or []),
    )


def _fail(errors: List[str], warnings: List[str] | None = None) -> ValidationResult:
    return ValidationResult(
        is_valid=False,
        errors=tuple(errors),
        warnings=tuple(warnings or []),
    )


class EngineValidator:
    """
    Stateless validator for Execution Risk Engine requests.

    Methods return ``ValidationResult`` — callers can inspect errors
    directly or call ``raise_if_invalid`` to convert to an exception.
    """

    # ── EvaluationRequest ─────────────────────────────────────────────────────

    def validate_request(self, request: EvaluationRequest) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.request_id:
            errors.append(f"{ValidationCode.IDENTIFIER_MISSING.value}: request_id is required")

        if request.risk_category is None:
            errors.append(
                f"{ValidationCode.CONTEXT_INVALID.value}: risk_category must be provided"
            )

        if not request.execution_id and not request.order_id:
            warnings.append(
                "Neither execution_id nor order_id was provided — evaluation may lack context"
            )

        if request.expiry_ttl_seconds is not None and request.expiry_ttl_seconds <= 0:
            errors.append(
                f"{ValidationCode.CONTEXT_INVALID.value}: expiry_ttl_seconds must be positive"
            )

        if errors:
            return _fail(errors, warnings)
        return _ok(warnings)

    # ── QueryEvaluationRequest ────────────────────────────────────────────────

    def validate_query(self, request: QueryEvaluationRequest) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if request.limit < 1:
            errors.append(
                f"{ValidationCode.CONTEXT_INVALID.value}: query limit must be >= 1"
            )
        elif request.limit > DEFAULT_SEARCH_LIMIT:
            warnings.append(
                f"Query limit {request.limit} exceeds recommended maximum {DEFAULT_SEARCH_LIMIT}"
            )

        if errors:
            return _fail(errors, warnings)
        return _ok(warnings)

    # ── Post-evaluation rule results ──────────────────────────────────────────

    def validate_evaluation_complete(
        self,
        rule_results: List[RuleResult],
    ) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        for r in rule_results:
            if not r.rule_name:
                errors.append(
                    f"{ValidationCode.CONTEXT_INVALID.value}: rule_name is missing in a RuleResult"
                )
            if r.elapsed_ms < 0:
                warnings.append(
                    f"Rule '{r.rule_name}' reported negative elapsed_ms ({r.elapsed_ms:.2f})"
                )

        if errors:
            return _fail(errors, warnings)
        return _ok(warnings)

    # ── Convenience ──────────────────────────────────────────────────────────

    def raise_if_invalid(self, result: ValidationResult) -> None:
        """Raise ``RiskEngineValidationError`` if *result* is not valid."""
        if not result.is_valid:
            detail = "; ".join(result.errors)
            raise RiskEngineValidationError(detail)
