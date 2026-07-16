"""iios/execution/oms/order_book/order_book_factory.py
==================================================
OrderBookEntryFactory — creates OrderBookEntry objects from
OrderAddRequest instances.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger
from iios.execution.oms.order_book.constants import (
    FACTORY_SYSTEM_ID,
    ORDER_STATE_TO_BOOK_STATUS,
    BookEntryStatus,
)
from iios.execution.oms.order_book.order_book_context import OrderAddRequest
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry

_log = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)


class OrderBookEntryFactory:
    """Stateless factory for OrderBookEntry. Thread-safe."""

    def create(self, request: OrderAddRequest) -> OrderBookEntry:
        """Create an OrderBookEntry from an OrderAddRequest."""
        status = ORDER_STATE_TO_BOOK_STATUS.get(
            request.order_state,
            BookEntryStatus.ACTIVE,
        )
        entry = OrderBookEntry(
            order_id      = request.order_id,
            portfolio_id  = request.portfolio_id,
            strategy_id   = request.strategy_id,
            decision_id   = request.decision_id,
            execution_id  = request.execution_id,
            workflow_id   = request.workflow_id,
            broker_id     = request.broker_id,
            instrument    = request.instrument,
            exchange      = request.exchange,
            order_type    = request.order_type,
            side          = request.side,
            status        = status,
            order_state   = request.order_state,
            quantity      = request.quantity,
            limit_price   = request.limit_price,
            tags          = request.tags,
            metadata      = dict(request.metadata),
        )
        _log.info("OrderBookEntry created.", order_id=entry.order_id)
        return entry

    def create_from_params(
        self,
        order_id:      str,
        instrument:    str  = "",
        exchange:      str  = "",
        order_type:    str  = "",
        side:          str  = "",
        portfolio_id:  str  = "",
        strategy_id:   str  = "",
        workflow_id:   str  = "",
        execution_id:  str  = "",
        order_state:   str  = "",
        **kwargs: object,
    ) -> OrderBookEntry:
        req = OrderAddRequest(
            order_id     = order_id,
            instrument   = instrument,
            exchange     = exchange,
            order_type   = order_type,
            side         = side,
            portfolio_id = portfolio_id,
            strategy_id  = strategy_id,
            workflow_id  = workflow_id,
            execution_id = execution_id,
            order_state  = order_state,
        )
        return self.create(req)
