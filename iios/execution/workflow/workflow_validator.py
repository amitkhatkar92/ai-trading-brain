"""iios/execution/workflow/workflow_validator.py"""
from __future__ import annotations

from iios.execution.core.execution_request import ExecutionRequest
from iios.execution.execution_constants import (
    MAX_PRICE,
    MAX_QUANTITY,
    MIN_QUANTITY,
    ExecutionMode,
    ExecutionType,
)


class WorkflowValidator:
    """
    Validates an ExecutionRequest before the workflow begins.

    Returns (is_valid, list_of_error_messages).
    Validation is pure — no side-effects.
    """

    def validate(self, request: ExecutionRequest) -> tuple[bool, list[str]]:
        errors: list[str] = []

        # ── Ticker ────────────────────────────────────────────────────────────
        if not request.ticker or not request.ticker.strip():
            errors.append("ticker is required and must not be blank")

        # ── Execution type ────────────────────────────────────────────────────
        if request.execution_type == ExecutionType.UNKNOWN:
            errors.append("execution_type must not be UNKNOWN")

        # ── Quantity ──────────────────────────────────────────────────────────
        if request.quantity < MIN_QUANTITY:
            errors.append(
                f"quantity must be >= {MIN_QUANTITY} (got {request.quantity})"
            )
        if request.quantity > MAX_QUANTITY:
            errors.append(
                f"quantity exceeds maximum {MAX_QUANTITY} (got {request.quantity})"
            )

        # ── Prices ────────────────────────────────────────────────────────────
        for price_field, price_val in [
            ("target_price", request.target_price),
            ("price_limit",  request.price_limit),
            ("stop_loss",    request.stop_loss),
            ("take_profit",  request.take_profit),
        ]:
            if price_val is not None:
                if price_val < 0.0:
                    errors.append(f"{price_field} must not be negative (got {price_val})")
                if price_val > MAX_PRICE:
                    errors.append(
                        f"{price_field} exceeds maximum {MAX_PRICE} (got {price_val})"
                    )

        # ── Stop/limit logic ──────────────────────────────────────────────────
        if (
            request.stop_loss is not None
            and request.target_price is not None
            and request.execution_type in (ExecutionType.BUY, ExecutionType.COVER)
            and request.stop_loss >= request.target_price
        ):
            errors.append(
                "stop_loss must be below target_price for BUY orders "
                f"({request.stop_loss} >= {request.target_price})"
            )

        # ── Expiry ────────────────────────────────────────────────────────────
        if request.is_expired:
            errors.append(f"execution request has expired (expires_at={request.expires_at})")

        # ── Live-mode guard ───────────────────────────────────────────────────
        if request.execution_mode == ExecutionMode.LIVE:
            errors.append(
                "LIVE execution mode is not yet supported — "
                "use PAPER or SIMULATION (broker adapters are a future phase)"
            )

        return len(errors) == 0, errors
