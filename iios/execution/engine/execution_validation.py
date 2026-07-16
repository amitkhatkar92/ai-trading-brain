"""iios/execution/engine/execution_validation.py
==================================================
Stateless validation logic for the Execution Engine.

ExecutionValidator validates:
  1. ExecutionRequest   — identifiers, mode, expiry
  2. ExecutionContext   — order presence, order state compatibility
  3. State transitions  — engine state machine rules

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .constants import ExecutionValidationCode
from .execution_state import (
    EngineExecutionState, can_engine_transition, is_engine_terminal,
)

if TYPE_CHECKING:
    from .execution_context import ExecutionContext
    from .execution_request import ExecutionRequest


# ── ValidationResult ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """
    Immutable result of a validation pass.

    Attributes
    ----------
    passed   : True when no errors were found.
    errors   : Tuple of error messages (empty on success).
    warnings : Tuple of non-blocking warning messages.
    """
    passed:   bool
    errors:   tuple[str, ...]
    warnings: tuple[str, ...]

    @classmethod
    def ok(cls, warnings: tuple[str, ...] = ()) -> "ValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str, warnings: tuple[str, ...] = ()) -> "ValidationResult":
        return cls(passed=False, errors=tuple(errors), warnings=warnings)

    def __bool__(self) -> bool:
        return self.passed


# ── ExecutionValidator ────────────────────────────────────────────────────────

class ExecutionValidator:
    """
    Stateless, thread-safe validator for the Execution Engine.

    All methods are pure functions — they do not mutate any state
    and can be called concurrently from multiple threads.
    """

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(self, request: "ExecutionRequest") -> ValidationResult:
        """
        Validate an ExecutionRequest before processing begins.

        Checks
        ------
        • request_id is not empty.
        • order_id is not empty.
        • decision_id is not empty.
        • portfolio_id is not empty.
        • strategy_id is not empty.
        • execution_mode is a recognised ExecutionMode.
        • Request has not expired.
        """
        errors:   list[str] = []
        warnings: list[str] = []

        if not request.request_id:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_ORDER_ID.value}] "
                "request_id must not be empty"
            )
        if not request.order_id:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if not request.decision_id:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_DECISION_ID.value}] "
                "decision_id must not be empty"
            )
        if not request.portfolio_id:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_PORTFOLIO_ID.value}] "
                "portfolio_id must not be empty"
            )
        if not request.strategy_id:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_STRATEGY_ID.value}] "
                "strategy_id must not be empty"
            )
        if request.is_expired:
            errors.append(
                f"[{ExecutionValidationCode.REQUEST_EXPIRED.value}] "
                "execution request has passed its expires_at deadline"
            )

        # Mode is always valid (enum prevents invalid values) — just note LIVE
        from .constants import ExecutionMode
        if request.execution_mode == ExecutionMode.LIVE:
            warnings.append(
                "LIVE execution mode requires a connected broker adapter "
                "(not yet implemented in this module)"
            )

        if errors:
            return ValidationResult.fail(*errors, warnings=tuple(warnings))
        return ValidationResult.ok(warnings=tuple(warnings))

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(self, context: "ExecutionContext") -> ValidationResult:
        """
        Validate an ExecutionContext after it has been assembled.

        Checks
        ------
        • context.request is not None.
        • order is present (order_id was resolved).
        • order is not in a terminal state that prevents further processing.
        • execution_mode matches request.
        """
        errors:   list[str] = []
        warnings: list[str] = []

        if context.request is None:
            errors.append(
                f"[{ExecutionValidationCode.MISSING_ORDER_ID.value}] "
                "ExecutionContext.request must not be None"
            )
            return ValidationResult.fail(*errors)

        if context.order is None:
            errors.append(
                f"[{ExecutionValidationCode.ORDER_NOT_FOUND.value}] "
                f"Order {context.request.order_id!r} was not resolved in the context"
            )
        else:
            # Validate order state compatibility
            from iios.execution.lifecycle.order_state import (
                TERMINAL_STATES, OrderState,
            )
            if context.order.state in TERMINAL_STATES:
                errors.append(
                    f"[{ExecutionValidationCode.ORDER_TERMINAL.value}] "
                    f"Order {context.order.order_id!r} is in terminal state "
                    f"{context.order.state.value!r} and cannot be executed"
                )
            elif context.order.state not in {
                OrderState.CREATED,
                OrderState.VALIDATED,
                OrderState.PENDING_SUBMISSION,
                OrderState.RECOVERED,
            }:
                errors.append(
                    f"[{ExecutionValidationCode.ORDER_INVALID_STATE.value}] "
                    f"Order {context.order.order_id!r} is in state "
                    f"{context.order.state.value!r}; expected CREATED, VALIDATED, "
                    "PENDING_SUBMISSION, or RECOVERED for execution"
                )

        if not context.has_portfolio:
            warnings.append(
                f"[{ExecutionValidationCode.PORTFOLIO_MISSING.value}] "
                "No PortfolioIntelligenceSnapshot provided; "
                "portfolio-level constraints cannot be checked"
            )
        if not context.has_decision:
            warnings.append(
                f"[{ExecutionValidationCode.DECISION_MISSING.value}] "
                "No Decision provided; "
                "decision-level constraints cannot be checked"
            )

        if errors:
            return ValidationResult.fail(*errors, warnings=tuple(warnings))
        return ValidationResult.ok(warnings=tuple(warnings))

    # ── State transition validation ───────────────────────────────────────────

    def validate_engine_transition(
        self,
        current_state: EngineExecutionState,
        target_state:  EngineExecutionState,
        execution_id:  str = "",
    ) -> ValidationResult:
        """
        Validate that transitioning from *current_state* to *target_state*
        is legal according to VALID_ENGINE_TRANSITIONS.
        """
        if is_engine_terminal(current_state):
            return ValidationResult.fail(
                f"[{ExecutionValidationCode.TRANSITION_INVALID.value}] "
                f"Execution {execution_id!r} is already in terminal state "
                f"{current_state.value!r}"
            )
        if not can_engine_transition(current_state, target_state):
            return ValidationResult.fail(
                f"[{ExecutionValidationCode.TRANSITION_INVALID.value}] "
                f"Invalid engine state transition "
                f"{current_state.value!r} → {target_state.value!r}"
                + (f" (execution: {execution_id!r})" if execution_id else "")
            )
        return ValidationResult.ok()
