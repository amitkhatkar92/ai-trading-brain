"""iios/execution/orders/validation/validation_rules.py

Individual, composable validation rules.
Each rule returns (passed: bool, errors: list[str], warnings: list[str]).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..order_constants import (
    MAX_PRICE,
    MAX_QUANTITY,
    MIN_PRICE,
    MIN_QUANTITY,
    OrderType,
)
from ..core.order_request import OrderRequest


class ValidationRule(ABC):
    """Base class for a single validation rule."""

    name: str = "base_rule"

    @abstractmethod
    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        """Returns (passed, errors, warnings)."""
        ...


class TickerRule(ValidationRule):
    """Ticker / asset_id must be present."""
    name = "ticker_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        if not request.ticker and not request.asset_id:
            errors.append("Either ticker or asset_id must be provided")
        return (len(errors) == 0, errors, [])


class QuantityRule(ValidationRule):
    """Quantity must be within allowed bounds."""
    name = "quantity_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        if request.quantity <= 0:
            errors.append(f"Quantity must be > 0, got {request.quantity}")
        elif request.quantity < MIN_QUANTITY:
            errors.append(f"Quantity {request.quantity} is below minimum {MIN_QUANTITY}")
        elif request.quantity > MAX_QUANTITY:
            errors.append(f"Quantity {request.quantity} exceeds maximum {MAX_QUANTITY}")
        return (len(errors) == 0, errors, [])


class PriceRule(ValidationRule):
    """Limit/Stop orders must have a valid price."""
    name = "price_rule"

    _price_required = {OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT, OrderType.BRACKET}

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []

        if request.order_type in self._price_required:
            p = request.price or request.limit_price
            if p is None:
                errors.append(f"Order type {request.order_type.value} requires a price")
            elif p < MIN_PRICE:
                errors.append(f"Price {p} is below minimum {MIN_PRICE}")
            elif p > MAX_PRICE:
                errors.append(f"Price {p} exceeds maximum {MAX_PRICE}")

        if request.order_type == OrderType.MARKET and request.price is not None:
            warnings.append("Price is ignored for MARKET orders")

        return (len(errors) == 0, errors, warnings)


class StopPriceRule(ValidationRule):
    """Stop orders must have a valid stop price."""
    name = "stop_price_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        if request.order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
            sp = request.stop_price
            if sp is None:
                errors.append(f"Order type {request.order_type.value} requires stop_price")
            elif sp <= 0:
                errors.append(f"stop_price must be > 0, got {sp}")
        return (len(errors) == 0, errors, [])


class PortfolioRule(ValidationRule):
    """portfolio_id must be supplied."""
    name = "portfolio_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        if not request.portfolio_id:
            errors.append("portfolio_id is required")
        return (len(errors) == 0, errors, [])


class SlippageRule(ValidationRule):
    """Slippage tolerance must be sane."""
    name = "slippage_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []
        if request.max_slippage_pct < 0:
            errors.append("max_slippage_pct must be >= 0")
        if request.max_slippage_pct > 0.10:
            warnings.append(f"max_slippage_pct={request.max_slippage_pct:.2%} is unusually high")
        return (len(errors) == 0, errors, warnings)


class OrderTypeConsistencyRule(ValidationRule):
    """Bracket and Cover orders must have both price and stop_price."""
    name = "order_type_consistency_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        if request.order_type == OrderType.BRACKET:
            if request.price is None and request.limit_price is None:
                errors.append("BRACKET order requires price or limit_price")
            if request.stop_price is None:
                errors.append("BRACKET order requires stop_price")
        return (len(errors) == 0, errors, [])


class ExpiryRule(ValidationRule):
    """GTD orders must have an expires_at date."""
    name = "expiry_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        from ..order_constants import TimeInForce
        errors: list[str] = []
        if request.time_in_force == TimeInForce.GTD and request.expires_at is None:
            errors.append("GTD orders must have expires_at set")
        return (len(errors) == 0, errors, [])


class SideRule(ValidationRule):
    """OrderSide must be set to a known value."""
    name = "side_rule"

    def validate(self, request: OrderRequest) -> tuple[bool, list[str], list[str]]:
        from ..order_constants import OrderSide
        errors: list[str] = []
        valid = {OrderSide.BUY, OrderSide.SELL, OrderSide.BUY_TO_COVER, OrderSide.SELL_SHORT}
        if request.side not in valid:
            errors.append(f"Invalid order side: {request.side!r}")
        return (len(errors) == 0, errors, [])


# ── Default rule set ──────────────────────────────────────────────────────────

DEFAULT_RULES: list[ValidationRule] = [
    TickerRule(),
    QuantityRule(),
    PriceRule(),
    StopPriceRule(),
    PortfolioRule(),
    SlippageRule(),
    OrderTypeConsistencyRule(),
    ExpiryRule(),
    SideRule(),
]
