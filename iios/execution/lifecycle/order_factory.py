"""iios/execution/lifecycle/order_factory.py
==================================================
OrderFactory — creates well-formed Order instances.

The factory is the ONLY authorised way to create orders.
It enforces that every order carries a valid OrderContext,
correct field defaults for each order type, and an initial
metadata record.

All factory methods call OrderValidator.validate_new() and
raise OrderValidationError on failure, so callers receive a
validated Order in CREATED state ready for registry
registration.

Frameworks
----------
Logging:  get_logger / get_audit_logger  (IIOS v1.0)
Errors:   get_error_manager / report_failure  (IIOS v1.0)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
import time
import uuid

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

from .constants import (
    FACTORY_SYSTEM_ID, VERSION,
    OrderSide, OrderType, TimeInForce,
)
from .exceptions import OrderValidationError
from .order import Order
from .order_context import OrderContext
from .order_metadata import OrderMetadata
from .order_validation import OrderValidator

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="OrderFactory")


class OrderFactory:
    """
    Stateless factory for creating validated Order instances.

    Thread-safe.  A single shared instance is safe for concurrent use.
    """

    SYSTEM_ID = FACTORY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self) -> None:
        self._validator = OrderValidator()

    # ── Public factory methods ─────────────────────────────────────────────────

    def create_market_order(
        self,
        *,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        quantity:      Decimal,
        time_in_force: TimeInForce           = TimeInForce.DAY,
        order_id:      Optional[str]         = None,
        metadata:      Optional[OrderMetadata] = None,
    ) -> Order:
        """Create a MARKET order (no limit_price or stop_price)."""
        return self._build(
            order_id      = order_id or self._gen_id(),
            context       = context,
            instrument    = instrument,
            exchange      = exchange,
            side          = side,
            order_type    = OrderType.MARKET,
            quantity      = quantity,
            limit_price   = None,
            stop_price    = None,
            time_in_force = time_in_force,
            metadata      = metadata,
        )

    def create_limit_order(
        self,
        *,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        quantity:      Decimal,
        limit_price:   Decimal,
        time_in_force: TimeInForce           = TimeInForce.DAY,
        order_id:      Optional[str]         = None,
        metadata:      Optional[OrderMetadata] = None,
    ) -> Order:
        """Create a LIMIT order."""
        return self._build(
            order_id      = order_id or self._gen_id(),
            context       = context,
            instrument    = instrument,
            exchange      = exchange,
            side          = side,
            order_type    = OrderType.LIMIT,
            quantity      = quantity,
            limit_price   = limit_price,
            stop_price    = None,
            time_in_force = time_in_force,
            metadata      = metadata,
        )

    def create_stop_order(
        self,
        *,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        quantity:      Decimal,
        stop_price:    Decimal,
        time_in_force: TimeInForce           = TimeInForce.GTC,
        order_id:      Optional[str]         = None,
        metadata:      Optional[OrderMetadata] = None,
    ) -> Order:
        """Create a STOP order."""
        return self._build(
            order_id      = order_id or self._gen_id(),
            context       = context,
            instrument    = instrument,
            exchange      = exchange,
            side          = side,
            order_type    = OrderType.STOP,
            quantity      = quantity,
            limit_price   = None,
            stop_price    = stop_price,
            time_in_force = time_in_force,
            metadata      = metadata,
        )

    def create_stop_limit_order(
        self,
        *,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        quantity:      Decimal,
        stop_price:    Decimal,
        limit_price:   Decimal,
        time_in_force: TimeInForce           = TimeInForce.GTC,
        order_id:      Optional[str]         = None,
        metadata:      Optional[OrderMetadata] = None,
    ) -> Order:
        """Create a STOP_LIMIT order."""
        return self._build(
            order_id      = order_id or self._gen_id(),
            context       = context,
            instrument    = instrument,
            exchange      = exchange,
            side          = side,
            order_type    = OrderType.STOP_LIMIT,
            quantity      = quantity,
            limit_price   = limit_price,
            stop_price    = stop_price,
            time_in_force = time_in_force,
            metadata      = metadata,
        )

    def clone(self, order: Order, *, new_order_id: Optional[str] = None) -> Order:
        """
        Create a copy of *order* with a fresh order_id and reset fill state.

        The clone starts in CREATED state with zero fill.
        """
        cloned_id = new_order_id or self._gen_id()
        cloned = Order(
            order_id      = cloned_id,
            context       = order.context,
            instrument    = order.instrument,
            exchange      = order.exchange,
            side          = order.side,
            order_type    = order.order_type,
            quantity      = order.quantity,
            limit_price   = order.limit_price,
            stop_price    = order.stop_price,
            time_in_force = order.time_in_force,
            metadata      = OrderMetadata(
                source = order.metadata.source + ":clone",
                tags   = frozenset(order.metadata.tags),
                notes  = order.metadata.notes,
            ),
        )
        _log.info("Order cloned.", original_id=order.order_id, clone_id=cloned_id)
        return cloned

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build(
        self,
        order_id:      str,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        order_type:    OrderType,
        quantity:      Decimal,
        limit_price:   Optional[Decimal],
        stop_price:    Optional[Decimal],
        time_in_force: TimeInForce,
        metadata:      Optional[OrderMetadata],
    ) -> Order:
        ctx = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "create_order",
            stage     = "factory",
        )
        try:
            order = Order(
                order_id      = order_id,
                context       = context,
                instrument    = instrument,
                exchange      = exchange,
                side          = side,
                order_type    = order_type,
                quantity      = quantity,
                limit_price   = limit_price,
                stop_price    = stop_price,
                time_in_force = time_in_force,
                metadata      = metadata or OrderMetadata(source=self.SYSTEM_ID),
            )
            result = self._validator.validate_new(order)
            if not result:
                raise OrderValidationError(
                    f"Order {order_id!r} failed validation: "
                    + "; ".join(result.errors),
                    code    = "EL-003",
                    context = {"order_id": order_id, "errors": list(result.errors)},
                )
            _log.info(
                "Order created.",
                order_id   = order_id,
                order_type = order_type.value,
                instrument = instrument,
                side       = side.value,
                quantity   = str(quantity),
            )
            _audit.log_workflow_event(
                workflow_id = self.SYSTEM_ID,
                stage       = "build",
                event       = "create_order",
                order_id    = order_id,
            )
            return order
        except OrderValidationError:
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx)
            _log.exception("Unexpected error in OrderFactory._build.", exc=exc)
            raise

    @staticmethod
    def _gen_id() -> str:
        """Generate a unique order ID."""
        return f"ORD-{uuid.uuid4().hex[:16].upper()}"
