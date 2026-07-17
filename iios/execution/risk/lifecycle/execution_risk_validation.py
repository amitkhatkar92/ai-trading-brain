"""iios/execution/risk/lifecycle/execution_risk_validation.py
==================================================
RiskValidator — validates execution risk state transitions, identifier
consistency, timestamp consistency, category validity, and lifecycle
consistency.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from .constants import VALID_TRANSITIONS, VALIDATOR_SYSTEM_ID, RiskState, VERSION
from .exceptions import RiskValidationError

if TYPE_CHECKING:
    from .execution_risk import ExecutionRisk


# ── Validation result ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of a validation run."""

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":      self.is_valid,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "validated_at":  self.validated_at,
        }


def _result(errors: List[str], warnings: List[str]) -> ValidationResult:
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ── Validator ─────────────────────────────────────────────────────────────────

class RiskValidator:
    """
    Stateless validator for execution risk lifecycle invariants.

    Each ``validate_*`` method returns a ``ValidationResult``; it never
    raises.  Only ``raise_if_invalid`` converts a failed result into an
    exception.
    """

    # ── Transition ────────────────────────────────────────────────────────────

    def validate_transition(
        self,
        risk:      "ExecutionRisk",
        new_state: RiskState,
    ) -> ValidationResult:
        """Check that *new_state* is reachable from risk's current state."""
        errors:   List[str] = []
        warnings: List[str] = []

        current = risk.state
        allowed = VALID_TRANSITIONS.get(current, frozenset())

        if new_state not in allowed:
            errors.append(
                f"Transition '{current.value}' → '{new_state.value}' is not allowed. "
                f"Valid targets: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
            )

        return _result(errors, warnings)

    # ── Identifiers ───────────────────────────────────────────────────────────

    def validate_identifiers(self, risk: "ExecutionRisk") -> ValidationResult:
        """Check that mandatory identifier fields are non-empty strings."""
        errors:   List[str] = []
        warnings: List[str] = []

        if not risk.risk_id or not risk.risk_id.strip():
            errors.append("risk_id must be a non-empty string")

        if not risk.portfolio_id:
            warnings.append("portfolio_id is empty")
        if not risk.strategy_id:
            warnings.append("strategy_id is empty")
        if not risk.execution_id:
            warnings.append("execution_id is empty")

        return _result(errors, warnings)

    # ── Timestamps ────────────────────────────────────────────────────────────

    def validate_timestamps(self, risk: "ExecutionRisk") -> ValidationResult:
        """Check timestamp ordering and expiry consistency."""
        errors:   List[str] = []
        warnings: List[str] = []

        if risk.updated_at < risk.created_at:
            errors.append(
                f"updated_at ({risk.updated_at}) is before created_at ({risk.created_at})"
            )

        now = time.time()
        if risk.created_at > now + 1.0:
            warnings.append("created_at is in the future")

        if risk.expiry_time is not None and risk.expiry_time <= risk.created_at:
            errors.append(
                f"expiry_time ({risk.expiry_time}) must be after created_at ({risk.created_at})"
            )

        return _result(errors, warnings)

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_lifecycle(self, risk: "ExecutionRisk") -> ValidationResult:
        """Check that the current state is consistent with recorded history."""
        errors:   List[str] = []
        warnings: List[str] = []

        states = risk.history.states()
        if not states:
            errors.append("History contains no state records")
            return _result(errors, warnings)

        latest = states[-1]
        if latest.state != risk.state:
            errors.append(
                f"Latest state record ({latest.state.value}) does not match "
                f"current state ({risk.state.value})"
            )

        return _result(errors, warnings)

    # ── Category ─────────────────────────────────────────────────────────────

    def validate_category(self, risk: "ExecutionRisk") -> ValidationResult:
        """Check that the risk category is set."""
        errors:   List[str] = []
        warnings: List[str] = []

        if risk.risk_category is None:
            errors.append("risk_category must be set")

        return _result(errors, warnings)

    # ── Full validation ───────────────────────────────────────────────────────

    def validate_full(self, risk: "ExecutionRisk") -> ValidationResult:
        """Run all validations and aggregate results."""
        all_errors:   List[str] = []
        all_warnings: List[str] = []

        for check in (
            self.validate_identifiers,
            self.validate_timestamps,
            self.validate_lifecycle,
            self.validate_category,
        ):
            result = check(risk)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        return _result(all_errors, all_warnings)

    # ── Raise helper ──────────────────────────────────────────────────────────

    def raise_if_invalid(self, result: ValidationResult) -> None:
        """Raise ``RiskValidationError`` if *result* is not valid."""
        if not result.is_valid:
            raise RiskValidationError(
                f"Validation failed with {result.error_count} error(s): "
                + "; ".join(result.errors)
            )
