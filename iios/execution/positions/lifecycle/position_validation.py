"""iios/execution/positions/lifecycle/position_validation.py
==================================================
PositionValidator — validates position state transitions, identifier
consistency, quantity constraints, price consistency, and timestamp
ordering.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from .constants import (
    VALID_TRANSITIONS,
    VALIDATOR_SYSTEM_ID,
    PositionState,
    VERSION,
)
from .exceptions import PositionValidationError

if TYPE_CHECKING:
    from .position import Position


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
            "is_valid":     self.is_valid,
            "errors":       list(self.errors),
            "warnings":     list(self.warnings),
            "error_count":  self.error_count,
            "warning_count": self.warning_count,
            "validated_at": self.validated_at,
        }


def _result(errors: List[str], warnings: List[str]) -> ValidationResult:
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ── Validator ─────────────────────────────────────────────────────────────────

class PositionValidator:
    """
    Stateless validator for position lifecycle invariants.

    Each ``validate_*`` method returns a ``ValidationResult``; it never
    raises.  Only ``raise_if_invalid`` converts a failed result into an
    exception.
    """

    # ── Transition ────────────────────────────────────────────────────────────

    def validate_transition(
        self,
        position: "Position",
        new_state: PositionState,
    ) -> ValidationResult:
        """Check that *new_state* is reachable from position's current state."""
        errors:   List[str] = []
        warnings: List[str] = []

        current = position.state
        allowed = VALID_TRANSITIONS.get(current, frozenset())

        if new_state not in allowed:
            errors.append(
                f"Transition '{current.value}' → '{new_state.value}' is not allowed. "
                f"Valid targets: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
            )

        return _result(errors, warnings)

    # ── Identifiers ───────────────────────────────────────────────────────────

    def validate_identifiers(self, position: "Position") -> ValidationResult:
        """Check that mandatory identifier fields are non-empty strings."""
        errors:   List[str] = []
        warnings: List[str] = []

        if not position.position_id or not position.position_id.strip():
            errors.append("position_id must be a non-empty string")
        if not position.instrument or not position.instrument.strip():
            errors.append("instrument must be a non-empty string")
        if not position.exchange or not position.exchange.strip():
            errors.append("exchange must be a non-empty string")

        if not position.portfolio_id:
            warnings.append("portfolio_id is empty")
        if not position.strategy_id:
            warnings.append("strategy_id is empty")

        return _result(errors, warnings)

    # ── Quantities ────────────────────────────────────────────────────────────

    def validate_quantities(self, position: "Position") -> ValidationResult:
        """Check quantity invariants."""
        errors:   List[str] = []
        warnings: List[str] = []

        qty    = position.quantity
        open_q = position.open_quantity
        clos_q = position.closed_quantity

        if qty <= Decimal(0):
            errors.append(f"quantity must be positive; got {qty}")
        if open_q < Decimal(0):
            errors.append(f"open_quantity must be ≥ 0; got {open_q}")
        if clos_q < Decimal(0):
            errors.append(f"closed_quantity must be ≥ 0; got {clos_q}")
        if open_q + clos_q > qty:
            errors.append(
                f"open_quantity ({open_q}) + closed_quantity ({clos_q}) "
                f"exceeds total quantity ({qty})"
            )

        return _result(errors, warnings)

    # ── Prices ────────────────────────────────────────────────────────────────

    def validate_prices(self, position: "Position") -> ValidationResult:
        """Check price invariants."""
        errors:   List[str] = []
        warnings: List[str] = []

        if position.average_entry_price < Decimal(0):
            errors.append(
                f"average_entry_price must be ≥ 0; got {position.average_entry_price}"
            )
        if position.average_exit_price < Decimal(0):
            errors.append(
                f"average_exit_price must be ≥ 0; got {position.average_exit_price}"
            )

        # In an open or partially-closed position, a zero entry price is suspicious
        if (
            position.state in {PositionState.OPEN, PositionState.PARTIALLY_CLOSED}
            and position.average_entry_price == Decimal(0)
        ):
            warnings.append("average_entry_price is zero for an open position")

        return _result(errors, warnings)

    # ── Timestamps ────────────────────────────────────────────────────────────

    def validate_timestamps(self, position: "Position") -> ValidationResult:
        """Check timestamp ordering."""
        errors:   List[str] = []
        warnings: List[str] = []

        if position.updated_at < position.created_at:
            errors.append(
                f"updated_at ({position.updated_at}) is before created_at ({position.created_at})"
            )

        now = time.time()
        if position.created_at > now + 1.0:
            warnings.append("created_at is in the future")

        return _result(errors, warnings)

    # ── Full validation ───────────────────────────────────────────────────────

    def validate_full(self, position: "Position") -> ValidationResult:
        """Run all validations and aggregate results."""
        all_errors:   List[str] = []
        all_warnings: List[str] = []

        for check in (
            self.validate_identifiers,
            self.validate_quantities,
            self.validate_prices,
            self.validate_timestamps,
        ):
            r = check(position)
            all_errors.extend(r.errors)
            all_warnings.extend(r.warnings)

        return _result(all_errors, all_warnings)

    # ── Exception helper ──────────────────────────────────────────────────────

    def raise_if_invalid(self, result: ValidationResult, context: str = "") -> None:
        """Raise ``PositionValidationError`` if *result* is not valid."""
        if not result.is_valid:
            prefix = f"[{context}] " if context else ""
            raise PositionValidationError(
                f"{prefix}Validation failed: {'; '.join(result.errors)}",
                context={"errors": list(result.errors), "warnings": list(result.warnings)},
            )
