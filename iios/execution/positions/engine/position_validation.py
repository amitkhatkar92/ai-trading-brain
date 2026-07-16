"""iios/execution/positions/engine/position_validation.py
==================================================
EngineValidator — validates Position Engine operation requests.

Validation is operation-specific (create / update / close / sync /
archive / query) and uses the M1 PositionValidator for field-level
checks.  Engine-level checks address lifecycle state compatibility,
execution-data consistency, and request completeness.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    CLOSED_STATES,
    Position,
    PositionState,
    PositionValidator as LifecycleValidator,
)

from .constants import VALIDATOR_SYSTEM_ID
from .exceptions import PositionEngineValidationError
from .position_request import (
    ArchivePositionRequest,
    ClosePositionRequest,
    CreatePositionRequest,
    QueryPositionRequest,
    SyncPositionRequest,
    UpdatePositionRequest,
)

if TYPE_CHECKING:
    pass


# ── ValidationResult ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of an engine validation check."""

    is_valid:     bool
    errors:       tuple[str, ...]
    warnings:     tuple[str, ...]
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

class EngineValidator:
    """
    Stateless engine-level validator.

    Each ``validate_*`` method returns a ``ValidationResult``; it never
    raises.  Use ``raise_if_invalid`` to convert a failed result into
    ``PositionEngineValidationError``.
    """

    def __init__(self) -> None:
        self._inner = LifecycleValidator()

    # ── CREATE ────────────────────────────────────────────────────────────────

    def validate_create(self, request: CreatePositionRequest) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.instrument or not request.instrument.strip():
            errors.append("instrument is required")
        if not request.exchange or not request.exchange.strip():
            errors.append("exchange is required")
        if request.product is None:
            errors.append("product is required")
        if request.direction is None:
            errors.append("direction is required")
        if request.quantity <= Decimal(0):
            errors.append(f"quantity must be positive; got {request.quantity}")
        if not request.portfolio_id:
            warnings.append("portfolio_id is empty")
        if not request.strategy_id:
            warnings.append("strategy_id is empty")

        return _result(errors, warnings)

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def validate_update(
        self,
        position: Position,
        request:  UpdatePositionRequest,
    ) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.position_id:
            errors.append("position_id is required")
            return _result(errors, warnings)

        if position.state in CLOSED_STATES:
            errors.append(
                f"Cannot update a position in '{position.state.value}' state"
            )

        if request.new_state is not None:
            r = self._inner.validate_transition(position, request.new_state)
            errors.extend(r.errors)
            warnings.extend(r.warnings)

        if request.open_quantity is not None and request.open_quantity < Decimal(0):
            errors.append(f"open_quantity must be ≥ 0; got {request.open_quantity}")
        if request.closed_quantity is not None and request.closed_quantity < Decimal(0):
            errors.append(f"closed_quantity must be ≥ 0; got {request.closed_quantity}")
        if request.avg_entry_price is not None and request.avg_entry_price < Decimal(0):
            errors.append(f"avg_entry_price must be ≥ 0; got {request.avg_entry_price}")
        if request.avg_exit_price is not None and request.avg_exit_price < Decimal(0):
            errors.append(f"avg_exit_price must be ≥ 0; got {request.avg_exit_price}")

        if not request.has_field_updates and request.new_state is None:
            warnings.append("UpdatePositionRequest has no field updates and no new_state")

        return _result(errors, warnings)

    # ── CLOSE ─────────────────────────────────────────────────────────────────

    def validate_close(
        self,
        position: Position,
        request:  ClosePositionRequest,
    ) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.position_id:
            errors.append("position_id is required")
            return _result(errors, warnings)

        # Must be closeable
        closeable = {
            PositionState.OPENING,
            PositionState.OPEN,
            PositionState.PARTIALLY_CLOSED,
            PositionState.CLOSING,
        }
        if position.state not in closeable:
            errors.append(
                f"Cannot close position in '{position.state.value}' state. "
                f"Closeable states: {[s.value for s in sorted(closeable, key=lambda x: x.value)]}"
            )

        if request.avg_exit_price is not None and request.avg_exit_price < Decimal(0):
            errors.append(f"avg_exit_price must be ≥ 0; got {request.avg_exit_price}")

        if request.avg_exit_price is None:
            warnings.append("avg_exit_price not provided; position will close at price 0")

        return _result(errors, warnings)

    # ── SYNC ──────────────────────────────────────────────────────────────────

    def validate_sync(
        self,
        position: Position,
        request:  SyncPositionRequest,
    ) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.position_id:
            errors.append("position_id is required")
            return _result(errors, warnings)

        if position.state in CLOSED_STATES:
            errors.append(
                f"Cannot sync a position in '{position.state.value}' state"
            )

        snap = request.execution_snapshot
        if snap is not None:
            if snap.position_id and snap.position_id != request.position_id:
                errors.append(
                    f"ExecutionSnapshot.position_id '{snap.position_id}' does not match "
                    f"request.position_id '{request.position_id}'"
                )
            if snap.open_quantity < Decimal(0):
                errors.append("ExecutionSnapshot.open_quantity must be ≥ 0")
            if snap.closed_quantity < Decimal(0):
                errors.append("ExecutionSnapshot.closed_quantity must be ≥ 0")

        if request.new_state is not None:
            r = self._inner.validate_transition(position, request.new_state)
            errors.extend(r.errors)
            warnings.extend(r.warnings)

        return _result(errors, warnings)

    # ── ARCHIVE ───────────────────────────────────────────────────────────────

    def validate_archive(
        self,
        position: Position,
        request:  ArchivePositionRequest,
    ) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.position_id:
            errors.append("position_id is required")
            return _result(errors, warnings)

        if position.state != PositionState.CLOSED:
            errors.append(
                f"Only CLOSED positions can be archived; "
                f"current state is '{position.state.value}'"
            )

        return _result(errors, warnings)

    # ── QUERY ─────────────────────────────────────────────────────────────────

    def validate_query(self, request: QueryPositionRequest) -> ValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if request.limit <= 0:
            errors.append(f"limit must be positive; got {request.limit}")

        return _result(errors, warnings)

    # ── Exception helper ──────────────────────────────────────────────────────

    def raise_if_invalid(self, result: ValidationResult, context: str = "") -> None:
        if not result.is_valid:
            prefix = f"[{context}] " if context else ""
            raise PositionEngineValidationError(
                f"{prefix}Validation failed: {'; '.join(result.errors)}",
                errors=result.errors,
                context={"errors": list(result.errors), "warnings": list(result.warnings)},
            )
