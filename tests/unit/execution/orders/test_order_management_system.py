"""tests/unit/execution/orders/test_order_management_system.py

Comprehensive test suite for the OMS layer.
~155 tests across all subsystems.
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import pytest

from iios.execution.orders import (
    CANCELLABLE_STATUSES,
    DEFAULT_MAX_ORDERS,
    DEFAULT_MAX_QUEUE_SIZE,
    FillStatus,
    InvalidOrderStatusError,
    LiveOrderStatistics,
    OMSCapacityError,
    OMSError,
    OMSNotInitializedError,
    Order,
    OrderAlreadyExistsError,
    OrderExecution,
    OrderFactory,
    OrderFillError,
    OrderHistory,
    OrderManagementSystem,
    OrderManager,
    OrderMetadata,
    OrderMode,
    OrderMonitor,
    OrderNotFoundError,
    OrderPriority,
    OrderQueue,
    OrderRegistry,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatistics,
    OrderStatus,
    OrderStatusTransition,
    OrderTerminalError,
    OrderTracker,
    OrderType,
    OrderValidationError,
    OverfillError,
    PriorityQueue,
    QueueFullError,
    QueueManager,
    QueueMonitor,
    QueueType,
    StatusTracker,
    TERMINAL_STATUSES,
    TimeInForce,
    ValidationEngine,
    ValidationReport,
    VALID_TRANSITIONS,
    ExecutionTracker,
    LifecycleEngine,
    OrderLifecycle,
    OrderValidator,
    get_oms,
    order_session,
    order_stage_scope,
    reset_oms,
    OMS_VERSION,
    OMS_SYSTEM_ID,
)
from iios.execution.orders.order_context import (
    OrderContextState,
    clear_order_context,
    get_order_context,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singletons():
    reset_oms()
    yield
    reset_oms()


def make_request(**overrides: Any) -> OrderRequest:
    """Return a minimal valid OrderRequest with optional field overrides."""
    defaults: dict[str, Any] = {
        "ticker":       "RELIANCE",
        "quantity":     10.0,
        "side":         OrderSide.BUY,
        "order_type":   OrderType.MARKET,
        "portfolio_id": "P001",
    }
    defaults.update(overrides)
    return OrderRequest(**defaults)


@pytest.fixture
def oms():
    inst = OrderManagementSystem()
    inst.initialize()
    yield inst
    inst.shutdown()


@pytest.fixture
def manager():
    return OrderManager()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────


class TestConstants:
    def test_order_status_lowercase(self):
        assert OrderStatus.DRAFT.value == "draft"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.ARCHIVED.value == "archived"

    def test_order_type_lowercase(self):
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"

    def test_terminal_statuses(self):
        assert OrderStatus.FILLED in TERMINAL_STATUSES
        assert OrderStatus.CANCELLED in TERMINAL_STATUSES
        assert OrderStatus.DRAFT not in TERMINAL_STATUSES

    def test_valid_transitions_draft(self):
        assert OrderStatus.CREATED in VALID_TRANSITIONS[OrderStatus.DRAFT]
        assert OrderStatus.CANCELLED in VALID_TRANSITIONS[OrderStatus.DRAFT]

    def test_valid_transitions_acknowledged_includes_modified(self):
        assert OrderStatus.MODIFIED in VALID_TRANSITIONS[OrderStatus.ACKNOWLEDGED]

    def test_cancellable_statuses(self):
        assert OrderStatus.VALIDATED in CANCELLABLE_STATUSES
        assert OrderStatus.QUEUED in CANCELLABLE_STATUSES
        assert OrderStatus.FILLED not in CANCELLABLE_STATUSES


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────


class TestExceptions:
    def test_order_not_found_message(self):
        exc = OrderNotFoundError(order_id="X-01")
        assert "X-01" in str(exc)
        assert exc.order_id == "X-01"

    def test_order_already_exists(self):
        exc = OrderAlreadyExistsError(order_id="O-99")
        assert "O-99" in str(exc)

    def test_invalid_order_status(self):
        exc = InvalidOrderStatusError(
            order_id="O-1", from_status="draft", to_status="filled"
        )
        assert "draft" in str(exc) and "filled" in str(exc)
        assert exc.from_status == "draft"
        assert exc.to_status == "filled"

    def test_order_terminal(self):
        exc = OrderTerminalError(order_id="O-2", status="filled")
        assert exc.order_id == "O-2"

    def test_order_validation_error(self):
        exc = OrderValidationError("bad", errors=["field X missing"])
        assert exc.errors == ["field X missing"]

    def test_queue_full(self):
        exc = QueueFullError(queue_name="priority", capacity=1000)
        assert exc.queue_name == "priority"
        assert exc.capacity == 1000

    def test_overfill(self):
        exc = OverfillError(order_id="O-3", requested=200.0, remaining=100.0)
        assert exc.requested == 200.0
        assert exc.remaining == 100.0

    def test_exception_hierarchy(self):
        assert issubclass(OrderNotFoundError, OMSError)
        assert issubclass(QueueFullError, OMSError)


# ─────────────────────────────────────────────────────────────────────────────
# 3. OrderContext
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderContext:
    def test_session_context_created(self):
        with order_session("req-1") as ctx:
            assert ctx.request_id == "req-1"
            assert get_order_context() is ctx

    def test_context_cleared_after_session(self):
        with order_session("req-2"):
            pass
        assert get_order_context() is None

    def test_stage_scope_sets_stage(self):
        with order_session("req-3") as ctx:
            with order_stage_scope("validation") as sctx:
                assert sctx is ctx
                assert ctx.current_stage == "validation"
            assert ctx.current_stage == ""

    def test_stage_scope_without_parent(self):
        with order_stage_scope("routing") as ctx:
            assert ctx.current_stage == "routing"
        assert get_order_context() is None

    def test_context_state_elapsed(self):
        ctx = OrderContextState()
        time.sleep(0.01)
        assert ctx.elapsed_ms() >= 10.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Order dataclass
# ─────────────────────────────────────────────────────────────────────────────


class TestOrder:
    def test_defaults(self):
        o = Order(side=OrderSide.BUY)
        assert o.status == OrderStatus.DRAFT
        assert o.fill_status == FillStatus.UNFILLED
        assert o.filled_quantity == 0.0

    def test_valid_transition(self):
        o = Order(side=OrderSide.BUY)
        o.transition_to(OrderStatus.CREATED)
        assert o.status == OrderStatus.CREATED

    def test_invalid_transition_raises(self):
        o = Order(side=OrderSide.BUY)
        with pytest.raises(InvalidOrderStatusError):
            o.transition_to(OrderStatus.FILLED)

    def test_terminal_raises_on_transition(self):
        # ARCHIVED is a hard terminal — no further transitions allowed.
        o = Order(side=OrderSide.BUY)
        o.status = OrderStatus.ARCHIVED
        with pytest.raises(OrderTerminalError):
            o.transition_to(OrderStatus.FILLED)

    def test_record_fill_partial(self):
        o = Order(side=OrderSide.BUY, quantity=100.0)
        o.record_fill(50.0, 200.0)
        assert o.filled_quantity == 50.0
        assert o.remaining_quantity == 50.0
        assert o.fill_status == FillStatus.PARTIAL
        assert o.avg_fill_price == 200.0

    def test_record_fill_complete(self):
        o = Order(side=OrderSide.BUY, quantity=100.0)
        o.record_fill(100.0, 200.0)
        assert o.fill_status == FillStatus.COMPLETE
        assert o.remaining_quantity == pytest.approx(0.0)

    def test_overfill_raises(self):
        o = Order(side=OrderSide.BUY, quantity=10.0)
        with pytest.raises(OverfillError):
            o.record_fill(20.0, 100.0)

    def test_fill_zero_raises(self):
        o = Order(side=OrderSide.BUY, quantity=10.0)
        with pytest.raises(OrderFillError):
            o.record_fill(0.0, 100.0)

    def test_to_dict_keys(self):
        o = Order(side=OrderSide.SELL, ticker="TCS", quantity=5.0)
        d = o.to_dict()
        assert d["ticker"] == "TCS"
        assert d["side"] == "sell"
        assert "order_id" in d

    def test_fill_pct(self):
        o = Order(side=OrderSide.BUY, quantity=200.0)
        o.record_fill(100.0, 10.0)
        assert o.fill_pct() == pytest.approx(50.0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. OrderRequest
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderRequest:
    def test_defaults(self):
        r = OrderRequest()
        assert r.order_type == OrderType.MARKET
        assert r.side == OrderSide.BUY

    def test_to_dict(self):
        r = make_request()
        d = r.to_dict()
        assert d["ticker"] == "RELIANCE"
        assert d["quantity"] == 10.0

    def test_unique_ids(self):
        r1, r2 = OrderRequest(), OrderRequest()
        assert r1.request_id != r2.request_id


# ─────────────────────────────────────────────────────────────────────────────
# 6. OrderResponse
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderResponse:
    def test_defaults(self):
        r = OrderResponse()
        assert r.success is True
        assert r.errors == []

    def test_to_dict(self):
        r = OrderResponse(order_id="O-1", success=True)
        d = r.to_dict()
        assert d["order_id"] == "O-1"
        assert d["success"] is True

    def test_response_with_order(self):
        order = Order(side=OrderSide.BUY, ticker="INFY")
        r = OrderResponse(order_id=order.order_id, order=order)
        d = r.to_dict()
        assert d["order"] is not None
        assert d["order"]["ticker"] == "INFY"


# ─────────────────────────────────────────────────────────────────────────────
# 7. OrderExecution
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderExecution:
    def test_fill_value_computed(self):
        e = OrderExecution(order_id="O", fill_quantity=10.0, fill_price=150.0)
        assert e.fill_value == pytest.approx(1500.0)

    def test_net_value(self):
        e = OrderExecution(fill_quantity=10.0, fill_price=100.0, commission=5.0)
        assert e.net_value() == pytest.approx(995.0)

    def test_to_dict(self):
        e = OrderExecution(order_id="O-1", fill_quantity=5.0, fill_price=200.0)
        d = e.to_dict()
        assert d["fill_quantity"] == 5.0
        assert d["order_id"] == "O-1"

    def test_unique_fill_ids(self):
        e1 = OrderExecution()
        e2 = OrderExecution()
        assert e1.fill_id != e2.fill_id


# ─────────────────────────────────────────────────────────────────────────────
# 8. OrderHistory
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderHistory:
    def test_add_and_retrieve_transition(self):
        h  = OrderHistory()
        tr = OrderStatusTransition(order_id="O-1")
        h.add_transition("O-1", tr)
        assert len(h.get_transitions("O-1")) == 1

    def test_add_and_retrieve_execution(self):
        h  = OrderHistory()
        ex = OrderExecution(order_id="O-2", fill_quantity=5.0, fill_price=100.0)
        h.add_execution("O-2", ex)
        execs = h.get_executions("O-2")
        assert len(execs) == 1
        assert execs[0].fill_quantity == 5.0

    def test_empty_for_unknown_order(self):
        h = OrderHistory()
        assert h.get_transitions("NO-SUCH") == []
        assert h.get_executions("NO-SUCH") == []

    def test_multiple_orders(self):
        h = OrderHistory()
        for i in range(5):
            h.add_transition(f"O-{i}", OrderStatusTransition(order_id=f"O-{i}"))
        assert h.order_count() == 5

    def test_thread_safety(self):
        h = OrderHistory()
        errors: list[Exception] = []

        def worker(n: int) -> None:
            try:
                for i in range(20):
                    h.add_transition(f"O-{n}-{i}", OrderStatusTransition())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# 9. OrderStatistics
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderStatistics:
    def test_defaults(self):
        s = OrderStatistics()
        assert s.orders_total == 0
        assert s.fill_rate == 0.0

    def test_record_fill_latency(self):
        s = OrderStatistics()
        s.record_fill_latency(100.0)
        s.record_fill_latency(200.0)
        assert s.avg_fill_latency_ms == pytest.approx(150.0)

    def test_recompute_rates(self):
        s = OrderStatistics()
        s.orders_submitted = 10
        s.orders_filled    = 8
        s.orders_cancelled = 2
        s.recompute_rates()
        assert s.fill_rate   == pytest.approx(0.8)
        assert s.cancel_rate == pytest.approx(0.2)

    def test_to_dict(self):
        s = OrderStatistics()
        d = s.to_dict()
        assert "orders_total" in d
        assert "fill_rate" in d


# ─────────────────────────────────────────────────────────────────────────────
# 10. Validation rules
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationRules:
    def test_ticker_rule_pass(self):
        v = OrderValidator()
        r = make_request(ticker="RELIANCE")
        report = v.validate(r)
        errors = [e for e in report.errors if "ticker" in e.lower() or "asset" in e.lower()]
        assert errors == []

    def test_ticker_rule_fail(self):
        v = OrderValidator()
        r = make_request(ticker="", asset_id="")
        report = v.validate(r)
        assert not report.passed

    def test_quantity_rule_zero(self):
        v = OrderValidator()
        r = make_request(quantity=0.0)
        report = v.validate(r)
        assert not report.passed

    def test_quantity_rule_negative(self):
        v = OrderValidator()
        r = make_request(quantity=-1.0)
        report = v.validate(r)
        assert not report.passed

    def test_limit_requires_price(self):
        v = OrderValidator()
        r = make_request(order_type=OrderType.LIMIT, price=None, limit_price=None)
        report = v.validate(r)
        assert not report.passed

    def test_limit_with_price_passes(self):
        v = OrderValidator()
        r = make_request(order_type=OrderType.LIMIT, price=200.0)
        report = v.validate(r)
        assert report.passed

    def test_stop_requires_stop_price(self):
        v = OrderValidator()
        r = make_request(order_type=OrderType.STOP, stop_price=None)
        report = v.validate(r)
        assert not report.passed

    def test_portfolio_rule_fail(self):
        v = OrderValidator()
        r = make_request(portfolio_id="")
        report = v.validate(r)
        assert not report.passed


# ─────────────────────────────────────────────────────────────────────────────
# 11. ValidationReport
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationReport:
    def test_passed_report(self):
        v = OrderValidator()
        r = make_request()
        report = v.validate(r)
        assert report.passed

    def test_failed_report(self):
        v = OrderValidator()
        r = make_request(quantity=0.0)
        report = v.validate(r)
        assert not report.passed
        assert report.error_count > 0

    def test_to_dict(self):
        v = OrderValidator()
        r = make_request()
        report = v.validate(r)
        d = report.to_dict()
        assert "passed" in d
        assert "errors" in d

    def test_warnings_present(self):
        v = OrderValidator()
        # market order with price set → slippage warning
        r = make_request(order_type=OrderType.MARKET, max_slippage_pct=0.50)
        report = v.validate(r)
        assert report.warning_count > 0


# ─────────────────────────────────────────────────────────────────────────────
# 12. OrderValidator
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderValidator:
    def test_validate_valid_request(self):
        v = OrderValidator()
        assert v.validate(make_request()).passed

    def test_validate_missing_ticker(self):
        v = OrderValidator()
        assert not v.validate(make_request(ticker="", asset_id="")).passed

    def test_validate_zero_qty(self):
        v = OrderValidator()
        assert not v.validate(make_request(quantity=0.0)).passed

    def test_rule_count(self):
        v = OrderValidator()
        assert len(v.rules) > 0

    def test_add_rule_increases_count(self):
        from iios.execution.orders.validation.validation_rules import TickerRule
        v = OrderValidator()
        n = len(v.rules)
        v.add_rule(TickerRule())
        assert len(v.rules) == n + 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. ValidationEngine
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationEngine:
    def test_validate_passes(self):
        ve = ValidationEngine()
        assert ve.validate(make_request()).passed

    def test_validate_fails(self):
        ve = ValidationEngine()
        assert not ve.validate(make_request(quantity=-1.0)).passed

    def test_metrics_updated(self):
        ve = ValidationEngine()
        ve.validate(make_request())
        ve.validate(make_request(quantity=0.0))
        assert ve.total_validated == 2

    def test_stats(self):
        ve = ValidationEngine()
        ve.validate(make_request())
        s = ve.stats()
        assert "total_validated" in s


# ─────────────────────────────────────────────────────────────────────────────
# 14. OrderQueue
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderQueue:
    def test_enqueue_dequeue_fifo(self):
        q = OrderQueue()
        o1 = Order(side=OrderSide.BUY, ticker="A")
        o2 = Order(side=OrderSide.BUY, ticker="B")
        q.enqueue(o1)
        q.enqueue(o2)
        assert q.dequeue() is o1
        assert q.dequeue() is o2

    def test_peek(self):
        q = OrderQueue()
        o = Order(side=OrderSide.BUY)
        q.enqueue(o)
        assert q.peek() is o
        assert len(q) == 1

    def test_remove(self):
        q = OrderQueue()
        o = Order(side=OrderSide.BUY)
        q.enqueue(o)
        assert q.remove(o.order_id)
        assert q.is_empty()

    def test_queue_full(self):
        q = OrderQueue(max_size=1)
        q.enqueue(Order(side=OrderSide.BUY))
        with pytest.raises(QueueFullError):
            q.enqueue(Order(side=OrderSide.BUY))

    def test_dequeue_empty_returns_none(self):
        q = OrderQueue()
        assert q.dequeue() is None

    def test_stats(self):
        q = OrderQueue(name="test")
        q.enqueue(Order(side=OrderSide.BUY))
        s = q.stats()
        assert s["size"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 15. PriorityQueue
# ─────────────────────────────────────────────────────────────────────────────


class TestPriorityQueue:
    def test_priority_ordering(self):
        pq = PriorityQueue()
        low  = Order(side=OrderSide.BUY, priority=OrderPriority.LOW)
        high = Order(side=OrderSide.BUY, priority=OrderPriority.HIGH)
        crit = Order(side=OrderSide.BUY, priority=OrderPriority.CRITICAL)
        pq.enqueue(low)
        pq.enqueue(high)
        pq.enqueue(crit)
        assert pq.dequeue() is crit
        assert pq.dequeue() is high
        assert pq.dequeue() is low

    def test_fifo_within_same_priority(self):
        pq = PriorityQueue()
        o1 = Order(side=OrderSide.BUY, priority=OrderPriority.NORMAL)
        o2 = Order(side=OrderSide.BUY, priority=OrderPriority.NORMAL)
        pq.enqueue(o1)
        pq.enqueue(o2)
        assert pq.dequeue() is o1

    def test_empty_dequeue_returns_none(self):
        pq = PriorityQueue()
        assert pq.dequeue() is None

    def test_stats(self):
        pq = PriorityQueue()
        pq.enqueue(Order(side=OrderSide.BUY))
        s = pq.stats()
        assert s["size"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 16. QueueManager
# ─────────────────────────────────────────────────────────────────────────────


class TestQueueManager:
    def test_enqueue_priority(self):
        qm = QueueManager()
        o  = Order(side=OrderSide.BUY)
        qm.enqueue(o, QueueType.PRIORITY)
        assert qm.total_pending() == 1

    def test_dequeue_priority(self):
        qm = QueueManager()
        o  = Order(side=OrderSide.BUY)
        qm.enqueue(o, QueueType.PRIORITY)
        out = qm.dequeue(QueueType.PRIORITY)
        assert out is o

    def test_enqueue_fifo(self):
        qm = QueueManager()
        o  = Order(side=OrderSide.BUY)
        qm.enqueue(o, QueueType.FIFO)
        assert qm.dequeue(QueueType.FIFO) is o

    def test_retry_increments_count(self):
        qm = QueueManager()
        o  = Order(side=OrderSide.BUY)
        o.retry_count = 0
        qm.enqueue(o, QueueType.RETRY)
        assert o.retry_count == 1

    def test_stats_keys(self):
        qm = QueueManager()
        s  = qm.stats()
        assert "priority" in s
        assert "fifo" in s


# ─────────────────────────────────────────────────────────────────────────────
# 17. StatusTracker
# ─────────────────────────────────────────────────────────────────────────────


class TestStatusTracker:
    def test_increment(self):
        st = StatusTracker()
        st.increment(OrderStatus.DRAFT)
        assert st.count(OrderStatus.DRAFT) == 1

    def test_move(self):
        st = StatusTracker()
        st.increment(OrderStatus.DRAFT)
        st.move(OrderStatus.DRAFT, OrderStatus.CREATED)
        assert st.count(OrderStatus.DRAFT) == 0
        assert st.count(OrderStatus.CREATED) == 1

    def test_snapshot(self):
        st = StatusTracker()
        st.increment(OrderStatus.DRAFT)
        s = st.snapshot()
        assert "draft" in s

    def test_total(self):
        st = StatusTracker()
        st.increment(OrderStatus.DRAFT)
        st.increment(OrderStatus.CREATED)
        assert st.total() == 2


# ─────────────────────────────────────────────────────────────────────────────
# 18. ExecutionTracker
# ─────────────────────────────────────────────────────────────────────────────


class TestExecutionTracker:
    def test_record(self):
        et = ExecutionTracker()
        e  = OrderExecution(fill_quantity=10.0, fill_price=100.0)
        et.record(e, 50.0)
        assert et.total_fills == 1

    def test_avg_latency(self):
        et = ExecutionTracker()
        et.record(OrderExecution(fill_quantity=1.0, fill_price=1.0), 100.0)
        et.record(OrderExecution(fill_quantity=1.0, fill_price=1.0), 200.0)
        assert et.avg_latency_ms == pytest.approx(150.0)

    def test_to_dict(self):
        et = ExecutionTracker()
        d  = et.to_dict()
        assert "total_fills" in d

    def test_reset(self):
        et = ExecutionTracker()
        et.record(OrderExecution(fill_quantity=1.0, fill_price=1.0), 10.0)
        et.reset()
        assert et.total_fills == 0


# ─────────────────────────────────────────────────────────────────────────────
# 19. OrderTracker
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderTracker:
    def test_track_and_get(self):
        ot = OrderTracker()
        o  = Order(side=OrderSide.BUY)
        ot.track(o)
        assert ot.get(o.order_id) is o

    def test_update(self):
        ot = OrderTracker()
        o  = Order(side=OrderSide.BUY, ticker="X")
        ot.track(o)
        o.ticker = "Y"
        ot.update(o)
        assert ot.get(o.order_id).ticker == "Y"

    def test_record_fill(self):
        ot = OrderTracker()
        o  = Order(side=OrderSide.BUY)
        ot.track(o)
        e  = OrderExecution(order_id=o.order_id, fill_quantity=5.0, fill_price=100.0)
        ot.record_fill(o.order_id, e)
        assert len(ot.fills(o.order_id)) == 1

    def test_not_found_raises(self):
        ot = OrderTracker()
        with pytest.raises(OrderNotFoundError):
            ot.get("NO-SUCH")

    def test_to_dict(self):
        ot = OrderTracker()
        d  = ot.to_dict()
        assert "tracked" in d


# ─────────────────────────────────────────────────────────────────────────────
# 20. LifecycleEngine
# ─────────────────────────────────────────────────────────────────────────────


class TestLifecycleEngine:
    def _make_engine(self):
        return LifecycleEngine(OrderHistory())

    def test_create(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        assert o.status == OrderStatus.CREATED

    def test_validate(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        le.validate(o)
        assert o.status == OrderStatus.VALIDATED

    def test_approve(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        le.validate(o)
        le.approve(o)
        assert o.status == OrderStatus.APPROVED

    def test_enqueue_and_submit(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        le.validate(o)
        le.approve(o)
        le.enqueue(o)
        le.submit(o)
        assert o.status == OrderStatus.SUBMITTED

    def test_fill(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        le.validate(o)
        le.approve(o)
        le.enqueue(o)
        le.submit(o)
        le.acknowledge(o)
        le.advance(o, OrderStatus.FILLED, reason="done")
        assert o.status == OrderStatus.FILLED

    def test_cancel(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        le.create(o)
        le.advance(o, OrderStatus.CANCELLED)
        assert o.status == OrderStatus.CANCELLED

    def test_invalid_transition_raises(self):
        le = self._make_engine()
        o  = Order(side=OrderSide.BUY)
        with pytest.raises(InvalidOrderStatusError):
            le.advance(o, OrderStatus.FILLED)

    def test_hook_called(self):
        le  = self._make_engine()
        called: list[str] = []
        le.register_hook(lambda o, t: called.append(t.to_status.value))
        o = Order(side=OrderSide.BUY)
        le.create(o)
        assert "created" in called


# ─────────────────────────────────────────────────────────────────────────────
# 21. OrderFactory
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderFactory:
    def test_create_from_request(self):
        f = OrderFactory()
        r = make_request(ticker="INFY", quantity=50.0)
        o = f.create(r)
        assert o.ticker == "INFY"
        assert o.quantity == 50.0
        assert o.request_id == r.request_id

    def test_clone_new_id(self):
        f = OrderFactory()
        o = f.create(make_request())
        c = f.clone(o)
        assert c.order_id != o.order_id
        assert c.parent_order_id == o.order_id

    def test_clone_copies_fields(self):
        f = OrderFactory()
        o = f.create(make_request(ticker="WIPRO"))
        c = f.clone(o)
        assert c.ticker == "WIPRO"

    def test_created_order_is_draft(self):
        f = OrderFactory()
        o = f.create(make_request())
        assert o.status == OrderStatus.DRAFT


# ─────────────────────────────────────────────────────────────────────────────
# 22. OrderRegistry
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderRegistry:
    def test_register_and_get(self):
        reg = OrderRegistry()
        o   = Order(side=OrderSide.BUY)
        reg.register(o)
        assert reg.get(o.order_id) is o

    def test_not_found_raises(self):
        reg = OrderRegistry()
        with pytest.raises(OrderNotFoundError):
            reg.get("NO-SUCH")

    def test_duplicate_raises(self):
        reg = OrderRegistry()
        o   = Order(side=OrderSide.BUY)
        reg.register(o)
        with pytest.raises(OrderAlreadyExistsError):
            reg.register(o)

    def test_update(self):
        reg = OrderRegistry()
        o   = Order(side=OrderSide.BUY, ticker="A")
        reg.register(o)
        o.ticker = "B"
        reg.update(o)
        assert reg.get(o.order_id).ticker == "B"

    def test_get_by_status(self):
        reg = OrderRegistry()
        o   = Order(side=OrderSide.BUY)
        reg.register(o)
        result = reg.get_by_status(OrderStatus.DRAFT)
        assert any(x.order_id == o.order_id for x in result)

    def test_get_by_portfolio(self):
        reg = OrderRegistry()
        o   = Order(side=OrderSide.BUY, portfolio_id="PORT-1")
        reg.register(o)
        result = reg.get_by_portfolio("PORT-1")
        assert len(result) == 1

    def test_capacity_exceeded(self):
        reg = OrderRegistry(max_orders=2)
        reg.register(Order(side=OrderSide.BUY))
        reg.register(Order(side=OrderSide.BUY))
        with pytest.raises(OMSCapacityError):
            reg.register(Order(side=OrderSide.BUY))

    def test_statistics(self):
        reg = OrderRegistry()
        reg.register(Order(side=OrderSide.BUY))
        s = reg.statistics()
        assert s["total_orders"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 23. OrderManager — core workflows
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderManager:
    def test_create_order(self, manager):
        o = manager.create_order(make_request())
        assert o.status == OrderStatus.VALIDATED

    def test_create_order_invalid_ticker(self, manager):
        with pytest.raises(OrderValidationError):
            manager.create_order(make_request(ticker="", asset_id=""))

    def test_create_order_zero_qty(self, manager):
        with pytest.raises(OrderValidationError):
            manager.create_order(make_request(quantity=0.0))

    def test_submit_order(self, manager):
        o = manager.create_order(make_request())
        resp = manager.submit_order(o.order_id)
        assert resp.success is True
        assert manager.get_order(o.order_id).status == OrderStatus.SUBMITTED

    def test_acknowledge_order(self, manager):
        o = manager.create_order(make_request())
        manager.submit_order(o.order_id)
        manager.acknowledge_order(o.order_id)
        assert manager.get_order(o.order_id).status == OrderStatus.ACKNOWLEDGED

    def test_fill_partial(self, manager):
        o = manager.create_order(make_request(quantity=100.0))
        manager.submit_order(o.order_id)
        filled = manager.fill_order(o.order_id, 50.0, 200.0)
        assert filled.status == OrderStatus.PARTIALLY_FILLED
        assert filled.filled_quantity == 50.0

    def test_fill_complete(self, manager):
        o = manager.create_order(make_request(quantity=100.0))
        manager.submit_order(o.order_id)
        filled = manager.fill_order(o.order_id, 100.0, 200.0)
        assert filled.status == OrderStatus.FILLED

    def test_cancel_validated(self, manager):
        o = manager.create_order(make_request())
        resp = manager.cancel_order(o.order_id, reason="user cancel")
        assert resp.success is True
        assert manager.get_order(o.order_id).status == OrderStatus.CANCELLED

    def test_cancel_terminal_raises(self, manager):
        o = manager.create_order(make_request(quantity=10.0))
        manager.submit_order(o.order_id)
        manager.fill_order(o.order_id, 10.0, 100.0)
        with pytest.raises(InvalidOrderStatusError):
            manager.cancel_order(o.order_id)

    def test_reject_order(self, manager):
        o = manager.create_order(make_request())
        manager.submit_order(o.order_id)
        rejected = manager.reject_order(o.order_id)
        assert rejected.status == OrderStatus.REJECTED

    def test_expire_order(self, manager):
        o = manager.create_order(make_request())
        manager.submit_order(o.order_id)
        manager.acknowledge_order(o.order_id)
        expired = manager.expire_order(o.order_id)
        assert expired.status == OrderStatus.EXPIRED

    def test_archive_order(self, manager):
        o = manager.create_order(make_request())
        manager.cancel_order(o.order_id)
        archived = manager.archive_order(o.order_id)
        assert archived.status == OrderStatus.ARCHIVED

    def test_get_orders_by_portfolio(self, manager):
        manager.create_order(make_request(portfolio_id="PX"))
        manager.create_order(make_request(portfolio_id="PX"))
        manager.create_order(make_request(portfolio_id="PY"))
        assert len(manager.get_orders_by_portfolio("PX")) == 2

    def test_statistics(self, manager):
        manager.create_order(make_request())
        s = manager.statistics()
        assert "registry" in s

    def test_health(self, manager):
        h = manager.health()
        assert "healthy" in h
        assert "registry_count" in h


# ─────────────────────────────────────────────────────────────────────────────
# 24. OrderManagementSystem — full workflows
# ─────────────────────────────────────────────────────────────────────────────


class TestOrderManagementSystem:
    def test_initialize_shutdown(self, oms):
        assert oms.is_running is True
        oms.shutdown()
        assert oms.is_running is False

    def test_requires_running(self):
        inst = OrderManagementSystem()
        with pytest.raises(OMSNotInitializedError):
            inst.create_order(make_request())

    def test_full_lifecycle(self, oms):
        req = make_request(quantity=50.0)
        o   = oms.create_order(req)
        assert o.status == OrderStatus.VALIDATED

        oms.submit_order(o.order_id)
        o = oms.get_order(o.order_id)
        assert o.status == OrderStatus.SUBMITTED

        oms.fill_order(o.order_id, 50.0, 100.0)
        o = oms.get_order(o.order_id)
        assert o.status == OrderStatus.FILLED

    def test_cancel_flow(self, oms):
        o    = oms.create_order(make_request())
        resp = oms.cancel_order(o.order_id, reason="test")
        assert resp.success
        assert oms.get_order(o.order_id).status == OrderStatus.CANCELLED

    def test_partial_then_complete_fill(self, oms):
        o = oms.create_order(make_request(quantity=100.0))
        oms.submit_order(o.order_id)
        oms.fill_order(o.order_id, 30.0, 10.0)
        oms.fill_order(o.order_id, 70.0, 10.0)
        o = oms.get_order(o.order_id)
        assert o.status == OrderStatus.FILLED

    def test_reject_flow(self, oms):
        o = oms.create_order(make_request())
        oms.submit_order(o.order_id)
        oms.reject_order(o.order_id)
        assert oms.get_order(o.order_id).status == OrderStatus.REJECTED

    def test_health_keys(self, oms):
        h = oms.health()
        assert h["running"] is True
        assert h["version"] == OMS_VERSION
        assert "uptime_sec" in h

    def test_stats(self, oms):
        oms.create_order(make_request())
        s = oms.stats()
        assert "registry" in s

    def test_get_orders_by_portfolio(self, oms):
        oms.create_order(make_request(portfolio_id="P-99"))
        oms.create_order(make_request(portfolio_id="P-99"))
        orders = oms.get_orders_by_portfolio("P-99")
        assert len(orders) == 2

    def test_multiple_orders_independent(self, oms):
        o1 = oms.create_order(make_request(ticker="RELIANCE"))
        o2 = oms.create_order(make_request(ticker="TCS"))
        oms.cancel_order(o1.order_id)
        o2_fresh = oms.get_order(o2.order_id)
        assert o2_fresh.status == OrderStatus.VALIDATED


# ─────────────────────────────────────────────────────────────────────────────
# 25. Async variants
# ─────────────────────────────────────────────────────────────────────────────


class TestAsync:
    def test_create_order_async(self, oms):
        async def run():
            return await oms.create_order_async(make_request())

        o = asyncio.run(run())
        assert o.status == OrderStatus.VALIDATED

    def test_submit_order_async(self, oms):
        async def run():
            o    = await oms.create_order_async(make_request())
            resp = await oms.submit_order_async(o.order_id)
            return o.order_id, resp

        oid, resp = asyncio.run(run())
        assert resp.success
        assert oms.get_order(oid).status == OrderStatus.SUBMITTED

    def test_cancel_order_async(self, oms):
        async def run():
            o    = await oms.create_order_async(make_request())
            resp = await oms.cancel_order_async(o.order_id, reason="async cancel")
            return resp

        resp = asyncio.run(run())
        assert resp.success


# ─────────────────────────────────────────────────────────────────────────────
# 26. Singletons
# ─────────────────────────────────────────────────────────────────────────────


class TestSingletons:
    def test_get_oms_returns_same_instance(self):
        a = get_oms()
        b = get_oms()
        assert a is b

    def test_reset_oms_creates_new_instance(self):
        a = get_oms()
        reset_oms()
        b = get_oms()
        assert a is not b

    def test_oms_is_running_after_get(self):
        oms = get_oms()
        assert oms.is_running is True


# ─────────────────────────────────────────────────────────────────────────────
# 27. Concurrency
# ─────────────────────────────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_creates(self, oms):
        errors: list[Exception] = []

        def worker(_: int) -> None:
            try:
                oms.create_order(make_request())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(oms.get_active_orders()) == 20

    def test_concurrent_fills(self, oms):
        # Create one order and do multiple partial fills from threads
        order = oms.create_order(make_request(quantity=100.0))
        oms.submit_order(order.order_id)
        errors: list[Exception] = []

        def fill_worker() -> None:
            try:
                oms.fill_order(order.order_id, 5.0, 100.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=fill_worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Some fills may have been rejected due to overfill; no unexpected errors
        unexpected = [e for e in errors if not isinstance(e, (OverfillError, InvalidOrderStatusError))]
        assert not unexpected

    def test_concurrent_registry(self):
        reg    = OrderRegistry()
        errors: list[Exception] = []

        def register_worker(n: int) -> None:
            try:
                for i in range(10):
                    reg.register(Order(side=OrderSide.BUY))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert reg.count() == 50


# ─────────────────────────────────────────────────────────────────────────────
# 28. Package imports
# ─────────────────────────────────────────────────────────────────────────────


class TestPackageImports:
    def test_top_level_import(self):
        import iios.execution.orders as oms_pkg  # noqa: F401
        assert hasattr(oms_pkg, "OrderManagementSystem")
        assert hasattr(oms_pkg, "get_oms")
        assert hasattr(oms_pkg, "Order")

    def test_constants_accessible(self):
        from iios.execution.orders import OMS_VERSION, OMS_SYSTEM_ID
        assert OMS_VERSION == "1.0.0"
        assert "oms" in OMS_SYSTEM_ID

    def test_version(self):
        oms = get_oms()
        assert oms.version == OMS_VERSION
