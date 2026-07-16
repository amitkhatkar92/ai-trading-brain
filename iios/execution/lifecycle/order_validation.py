"""iios/execution/lifecycle/order_validation.py
==================================================
OrderValidator — stateless validator for orders and
state transitions.

Validates
---------
• New order structural correctness (identifiers, quantities, prices)
• State transition legality (against the canonical transition table)
• Fill events (quantity bounds, price positivity, state compatibility)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Tuple

from .constants import MIN_PRICE, MIN_QUANTITY, MAX_QUANTITY, OrderType
from .order_state import FILL_STATES, TERMINAL_STATES, OrderState, can_transition

if TYPE_CHECKING:
    from .order import Order


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of a validation check.

    Parameters
    ----------
    passed : bool
    errors : tuple[str, ...]
        Hard failures — the operation must be rejected.
    warnings : tuple[str, ...]
        Soft concerns — the operation may proceed.
    """
    passed:   bool
    errors:   Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def ok(cls, warnings: Tuple[str, ...] = ()) -> "ValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "ValidationResult":
        return cls(passed=False, errors=errors, warnings=())

    def __bool__(self) -> bool:
        return self.passed


class OrderValidator:
    """
    Stateless validator.

    A single shared instance is safe for concurrent use;
    all methods are pure functions with no side effects.
    """

    # ── New order validation ───────────────────────────────────────────────────

    def validate_new(self, order: "Order") -> ValidationResult:
        """
        Validate a newly created order for structural correctness.

        Checks: order_id, context identifiers, instrument, exchange,
        quantity bounds, price consistency for order type.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Identifiers
        if not order.order_id or not order.order_id.strip():
            errors.append("order_id must not be empty.")
        if not order.context.strategy_id:
            errors.append("context.strategy_id must not be empty.")
        if not order.context.portfolio_id:
            errors.append("context.portfolio_id must not be empty.")
        if not order.context.decision_id:
            errors.append("context.decision_id must not be empty.")
        if not order.context.workflow_id:
            errors.append("context.workflow_id must not be empty.")

        # Instrument
        if not order.instrument or not order.instrument.strip():
            errors.append("instrument must not be empty.")
        if not order.exchange or not order.exchange.strip():
            errors.append("exchange must not be empty.")

        # Quantity
        qty_errors = self._validate_quantity(order.quantity)
        errors.extend(qty_errors)

        # Price constraints by order type
        errors.extend(self._validate_prices(order))

        # Timestamps
        if order.created_at <= 0:
            errors.append("created_at must be a positive Unix timestamp.")
        if order.updated_at < order.created_at:
            errors.append("updated_at must not be earlier than created_at.")

        if errors:
            return ValidationResult(passed=False, errors=tuple(errors),
                                    warnings=tuple(warnings))
        return ValidationResult(passed=True, errors=(), warnings=tuple(warnings))

    # ── Transition validation ──────────────────────────────────────────────────

    def validate_transition(
        self,
        order:        "Order",
        target_state: OrderState,
    ) -> ValidationResult:
        """
        Validate that the order may transition to *target_state*.

        Checks: terminal guard, canonical transition table.
        """
        if order.state in TERMINAL_STATES:
            return ValidationResult.fail(
                f"Order {order.order_id!r} is in terminal state "
                f"{order.state.value!r} — no further transitions allowed."
            )
        if not can_transition(order.state, target_state):
            return ValidationResult.fail(
                f"Transition {order.state.value!r} → {target_state.value!r} "
                f"is not permitted by the state machine "
                f"(order_id={order.order_id!r})."
            )
        return ValidationResult.ok()

    # ── Fill validation ────────────────────────────────────────────────────────

    def validate_fill(
        self,
        order:      "Order",
        fill_qty:   Decimal,
        fill_price: Decimal,
    ) -> ValidationResult:
        """
        Validate a fill event against the order's current state and quantities.

        Checks: order state allows fills, fill_qty bounds,
        fill_price positivity, no overfill.
        """
        errors: list[str] = []

        # State must allow fills
        if order.state not in FILL_STATES and order.state not in {
            OrderState.ACKNOWLEDGED,
            OrderState.CANCEL_PENDING,
        }:
            errors.append(
                f"Order {order.order_id!r} is in state {order.state.value!r} "
                f"which does not accept fills."
            )

        # fill_qty
        errors.extend(self._validate_quantity(fill_qty, label="fill_qty"))
        if not errors:
            if fill_qty > order.remaining_quantity:
                errors.append(
                    f"fill_qty {fill_qty} exceeds remaining_quantity "
                    f"{order.remaining_quantity} (order_id={order.order_id!r})."
                )

        # fill_price
        if fill_price <= 0:
            errors.append(f"fill_price must be positive (got {fill_price}).")

        if errors:
            return ValidationResult(passed=False, errors=tuple(errors), warnings=())
        return ValidationResult.ok()

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _validate_quantity(qty: Decimal, label: str = "quantity") -> list[str]:
        errors: list[str] = []
        try:
            q = Decimal(qty)
        except (InvalidOperation, TypeError):
            errors.append(f"{label} is not a valid Decimal.")
            return errors
        if q <= 0:
            errors.append(f"{label} must be positive (got {q}).")
        elif q < MIN_QUANTITY:
            errors.append(f"{label} {q} is below minimum {MIN_QUANTITY}.")
        elif q > MAX_QUANTITY:
            errors.append(f"{label} {q} exceeds maximum {MAX_QUANTITY}.")
        return errors

    @staticmethod
    def _validate_prices(order: "Order") -> list[str]:
        errors: list[str] = []
        ot = order.order_type
        if ot in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if order.limit_price is None:
                errors.append(f"{ot.value} orders require limit_price.")
            elif order.limit_price <= 0:
                errors.append(f"limit_price must be positive.")
        if ot in (OrderType.STOP, OrderType.STOP_LIMIT):
            if order.stop_price is None:
                errors.append(f"{ot.value} orders require stop_price.")
            elif order.stop_price <= 0:
                errors.append(f"stop_price must be positive.")
        # Check that a supplied limit_price is sane
        if order.limit_price is not None and order.limit_price <= 0:
            errors.append("limit_price must be positive if supplied.")
        if order.stop_price is not None and order.stop_price <= 0:
            errors.append("stop_price must be positive if supplied.")
        return errors
