"""iios/execution/gateway/lifecycle/gateway_validation.py
==================================================
GatewayValidator — validates gateway request transitions, identifier
consistency, timestamp consistency, and lifecycle invariants.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from .constants import ACTIVE_STATES, ENDED_STATES, VALID_TRANSITIONS, GatewayState
from .exceptions import GatewayValidationError

if TYPE_CHECKING:
    from .gateway_request import GatewayRequest


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

    def __bool__(self) -> bool:
        return self.is_valid

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

class GatewayValidator:
    """
    Stateless validator for execution gateway lifecycle invariants.

    Each ``validate_*`` method returns a ``ValidationResult``; it never
    raises.  Only ``raise_if_invalid`` converts a failed result into an
    exception.
    """

    # ── Transition ────────────────────────────────────────────────────────────

    def validate_transition(
        self,
        request:   "GatewayRequest",
        new_state: GatewayState,
    ) -> ValidationResult:
        """Check that *new_state* is reachable from request's current state."""
        errors:   List[str] = []
        warnings: List[str] = []

        current = request.state
        allowed = VALID_TRANSITIONS.get(current, frozenset())

        if new_state not in allowed:
            errors.append(
                f"Transition '{current.value}' → '{new_state.value}' is not permitted. "
                f"Allowed targets: {sorted(s.value for s in allowed) or 'none (terminal)'}"
            )

        if current in ENDED_STATES and new_state not in VALID_TRANSITIONS.get(current, frozenset()):
            errors.append(
                f"Request '{request.gateway_id}' is in a terminal/ended state "
                f"'{current.value}' and cannot transition further."
            )

        return _result(errors, warnings)

    def raise_if_invalid(
        self,
        result:    ValidationResult,
        gateway_id: str = "",
    ) -> None:
        """Raise ``GatewayValidationError`` if *result* is not valid."""
        if not result.is_valid:
            detail = "; ".join(result.errors)
            raise GatewayValidationError(
                f"Validation failed for gateway '{gateway_id}': {detail}",
                context={"errors": list(result.errors), "gateway_id": gateway_id},
            )

    # ── Identifier ────────────────────────────────────────────────────────────

    def validate_identifiers(
        self,
        gateway_id:   str,
        execution_id: str = "",
        order_id:     str = "",
        portfolio_id: str = "",
        strategy_id:  str = "",
    ) -> ValidationResult:
        """Check that all required identifier fields are non-empty."""
        errors:   List[str] = []
        warnings: List[str] = []

        if not gateway_id:
            errors.append("gateway_id must not be empty")
        if not execution_id:
            warnings.append("execution_id is empty — traceability reduced")
        if not order_id:
            warnings.append("order_id is empty — traceability reduced")
        if not portfolio_id:
            warnings.append("portfolio_id is empty — traceability reduced")

        return _result(errors, warnings)

    # ── Request lifecycle ─────────────────────────────────────────────────────

    def validate_request(self, request: "GatewayRequest") -> ValidationResult:
        """Full lifecycle consistency check for a gateway request."""
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.gateway_id:
            errors.append("gateway_id must not be empty")

        if request.created_at <= 0:
            errors.append("created_at must be a positive Unix timestamp")

        if request.updated_at < request.created_at:
            errors.append("updated_at must not precede created_at")

        if request.completion_time is not None:
            if request.completion_time < request.created_at:
                errors.append("completion_time must not precede created_at")
            if request.state in ACTIVE_STATES:
                errors.append(
                    f"completion_time is set but request is still active "
                    f"(state={request.state.value})"
                )

        if request.state in ENDED_STATES and request.completion_time is None:
            warnings.append(
                f"Request is in ended state '{request.state.value}' "
                f"but completion_time is not set"
            )

        return _result(errors, warnings)

    # ── History integrity ──────────────────────────────────────────────────────

    def validate_history(self, request: "GatewayRequest") -> ValidationResult:
        """Validate that the transition history is consistent."""
        errors:   List[str] = []
        warnings: List[str] = []

        transitions = request.history.transitions()

        # Each transition should be consistent with state machine
        for t in transitions:
            if t.to_state not in VALID_TRANSITIONS.get(t.from_state, frozenset()):
                errors.append(
                    f"History contains invalid transition: "
                    f"'{t.from_state.value}' → '{t.to_state.value}' "
                    f"at {t.triggered_at}"
                )

        # No gap in transition chain (each to_state = next from_state)
        for i in range(len(transitions) - 1):
            if transitions[i].to_state != transitions[i + 1].from_state:
                errors.append(
                    f"History has gap at position {i}: "
                    f"to_state={transitions[i].to_state.value} "
                    f"but next from_state={transitions[i + 1].from_state.value}"
                )

        return _result(errors, warnings)
