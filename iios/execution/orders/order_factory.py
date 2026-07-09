"""iios/execution/orders/order_factory.py

Stateless factory that converts an OrderRequest into a fully-initialised Order.
"""
from __future__ import annotations

from .core.order import Order
from .core.order_request import OrderRequest


class OrderFactory:
    """Pure factory — no state, no I/O."""

    def create(self, request: OrderRequest) -> Order:
        return Order(
            request_id             = request.request_id,
            execution_id           = request.execution_id,
            decision_id            = request.decision_id,
            portfolio_id           = request.portfolio_id,
            strategy_id            = request.strategy_id,
            account_id             = request.account_id,
            asset_id               = request.asset_id,
            ticker                 = request.ticker,
            exchange               = request.exchange,
            asset_class            = request.asset_class,
            order_type             = request.order_type,
            side                   = request.side,
            quantity               = request.quantity,
            price                  = request.price,
            stop_price             = request.stop_price,
            limit_price            = request.limit_price,
            trail_amount           = request.trail_amount,
            time_in_force          = request.time_in_force,
            priority               = request.priority,
            mode                   = request.mode,
            max_slippage_pct       = request.max_slippage_pct,
            max_market_impact_pct  = request.max_market_impact_pct,
            expires_at             = request.expires_at,
            tags                   = list(request.tags),
            metadata               = dict(request.metadata),
        )

    def clone(self, order: Order) -> Order:
        """Create a copy of an existing order with a new order_id."""
        import copy
        clone           = copy.deepcopy(order)
        import uuid
        clone.order_id  = str(uuid.uuid4())
        clone.parent_order_id = order.order_id
        return clone

    def split(self, order: Order, quantities: list[float]) -> list[Order]:
        """Split one order into N child orders with the given quantities."""
        from .order_constants import OrderStatus
        if abs(sum(quantities) - order.quantity) > 1e-6:
            from .order_exceptions import OrderSplitError
            raise OrderSplitError(
                f"Split quantities {sum(quantities)} != original {order.quantity}",
                order_id=order.order_id,
            )
        children = []
        for qty in quantities:
            child = self.clone(order)
            child.quantity            = qty
            child.remaining_quantity  = qty
            child.filled_quantity     = 0.0
            child.avg_fill_price      = 0.0
            child.status              = OrderStatus.DRAFT
            order.child_order_ids.append(child.order_id)
            children.append(child)
        return children
