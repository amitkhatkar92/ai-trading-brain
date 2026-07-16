"""tests/unit/iios/execution/lifecycle/test_order_lifecycle.py
==================================================
Complete test suite for iios.execution.lifecycle

Parts
-----
 1  OrderState — enum values + state machine rules
 2  OrderTransition — immutable record + factory
 3  OrderEvent — immutable event + event_type_for_state
 4  OrderContext — immutable + with_broker / with_parent
 5  OrderMetadata — mutable + version tracking
 6  OrderHistory — append-only + thread safety + eviction
 7  OrderStatistics — transition + fill tracking
 8  Order — properties + _apply_transition + _apply_fill
 9  OrderValidation — new / transition / fill validation
10  OrderFactory — all order types + clone + error paths
11  OrderRegistry — full lifecycle + concurrency
12  Integration — end-to-end state machine traversal
13  Thread Safety — concurrent operations
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.lifecycle import (
    ACTOR_BROKER, ACTOR_EXCHANGE, ACTOR_SYSTEM, ACTOR_VALIDATOR,
    ACTIVE_STATES, CANCELLABLE_STATES, FILL_STATES, RECOVERABLE_STATES,
    TERMINAL_STATES, VALID_TRANSITIONS, VERSION,
    Order, OrderContext, OrderEvent, OrderEventType, OrderFactory,
    OrderHistory, OrderMetadata, OrderRegistry, OrderSide, OrderState,
    OrderStatistics, OrderTransition, OrderType, OrderValidator,
    RegistryStatistics, TimeInForce, ValidationResult,
    allowed_next, can_transition, event_type_for_state, is_terminal,
    make_event, make_transition,
    DuplicateOrderError, InvalidFillError, InvalidTransitionError,
    OrderNotFoundError, OrderTerminalError, OrderValidationError,
    RegistryCapacityError, RegistryNotRunningError,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx() -> OrderContext:
    return OrderContext(
        strategy_id  = "STRAT-001",
        portfolio_id = "PORT-001",
        decision_id  = "DEC-001",
        workflow_id  = "WF-001",
    )


@pytest.fixture
def factory() -> OrderFactory:
    return OrderFactory()


@pytest.fixture
def order(factory: OrderFactory, ctx: OrderContext) -> Order:
    return factory.create_limit_order(
        context     = ctx,
        instrument  = "RELIANCE",
        exchange    = "NSE",
        side        = OrderSide.BUY,
        quantity    = Decimal("100"),
        limit_price = Decimal("2800.00"),
    )


@pytest.fixture
def registry() -> OrderRegistry:
    reg = OrderRegistry()
    reg.start()
    yield reg
    if reg.is_running:
        reg.stop()


# ──────────────────────────────────────────────────────────────────────────────
#  PART 1 — OrderState
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderState:

    def test_all_14_states_defined(self):
        states = {s.value for s in OrderState}
        assert "CREATED"            in states
        assert "VALIDATED"          in states
        assert "PENDING_SUBMISSION" in states
        assert "SUBMITTED"          in states
        assert "ACKNOWLEDGED"       in states
        assert "PARTIALLY_FILLED"   in states
        assert "FILLED"             in states
        assert "CANCEL_PENDING"     in states
        assert "CANCELLED"          in states
        assert "REJECTED"           in states
        assert "EXPIRED"            in states
        assert "FAILED"             in states
        assert "RECOVERING"         in states
        assert "RECOVERED"          in states
        assert len(states) == 14

    def test_filled_is_terminal(self):
        assert is_terminal(OrderState.FILLED)
        assert OrderState.FILLED in TERMINAL_STATES

    def test_only_filled_is_terminal(self):
        # All other states have at least one outgoing transition
        for state in OrderState:
            if state != OrderState.FILLED:
                assert len(VALID_TRANSITIONS[state]) > 0, (
                    f"{state.value} should not be terminal"
                )

    def test_active_states(self):
        for s in ACTIVE_STATES:
            assert s in {
                OrderState.PENDING_SUBMISSION,
                OrderState.SUBMITTED,
                OrderState.ACKNOWLEDGED,
                OrderState.PARTIALLY_FILLED,
                OrderState.CANCEL_PENDING,
            }

    def test_recoverable_states(self):
        assert OrderState.CANCELLED  in RECOVERABLE_STATES
        assert OrderState.REJECTED   in RECOVERABLE_STATES
        assert OrderState.EXPIRED    in RECOVERABLE_STATES
        assert OrderState.FAILED     in RECOVERABLE_STATES

    def test_can_transition_valid(self):
        assert can_transition(OrderState.CREATED,   OrderState.VALIDATED)
        assert can_transition(OrderState.VALIDATED, OrderState.PENDING_SUBMISSION)
        assert can_transition(OrderState.PENDING_SUBMISSION, OrderState.SUBMITTED)
        assert can_transition(OrderState.SUBMITTED, OrderState.ACKNOWLEDGED)
        assert can_transition(OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED)
        assert can_transition(OrderState.PARTIALLY_FILLED, OrderState.FILLED)
        assert can_transition(OrderState.FAILED,    OrderState.RECOVERING)
        assert can_transition(OrderState.RECOVERING, OrderState.RECOVERED)
        assert can_transition(OrderState.RECOVERED, OrderState.PENDING_SUBMISSION)

    def test_can_transition_invalid(self):
        assert not can_transition(OrderState.FILLED,   OrderState.CANCELLED)
        assert not can_transition(OrderState.CREATED,  OrderState.FILLED)
        assert not can_transition(OrderState.VALIDATED, OrderState.FILLED)
        assert not can_transition(OrderState.FILLED,   OrderState.RECOVERING)

    def test_allowed_next_filled_is_empty(self):
        assert allowed_next(OrderState.FILLED) == frozenset()

    def test_cancel_pending_can_return_to_acknowledged(self):
        # Exchange rejects cancel — order is still live
        assert can_transition(OrderState.CANCEL_PENDING, OrderState.ACKNOWLEDGED)

    def test_partially_filled_to_partially_filled(self):
        # Multiple partial fills
        assert can_transition(OrderState.PARTIALLY_FILLED, OrderState.PARTIALLY_FILLED)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 2 — OrderTransition
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderTransition:

    def test_make_transition_populates_fields(self):
        t = make_transition(
            order_id   = "ORD-001",
            from_state = OrderState.CREATED,
            to_state   = OrderState.VALIDATED,
            reason     = "passed",
            actor      = ACTOR_VALIDATOR,
        )
        assert t.order_id   == "ORD-001"
        assert t.from_state == OrderState.CREATED
        assert t.to_state   == OrderState.VALIDATED
        assert t.reason     == "passed"
        assert t.actor      == ACTOR_VALIDATOR
        assert isinstance(t.transition_id, str) and len(t.transition_id) > 0
        assert t.occurred_at > 0

    def test_make_transition_accepts_custom_occurred_at(self):
        ts = 1_700_000_000.0
        t  = make_transition("O", OrderState.CREATED, OrderState.VALIDATED,
                              "r", "actor", occurred_at=ts)
        assert t.occurred_at == ts

    def test_make_transition_accepts_metadata(self):
        t = make_transition("O", OrderState.CREATED, OrderState.REJECTED,
                            "rejected", "broker",
                            metadata={"ref": "BRK-123"})
        assert t.metadata["ref"] == "BRK-123"

    def test_transition_is_immutable(self):
        t = make_transition("O", OrderState.CREATED, OrderState.VALIDATED,
                            "r", "actor")
        with pytest.raises((AttributeError, TypeError)):
            t.reason = "changed"  # type: ignore[misc]

    def test_to_dict_contains_state_values(self):
        t = make_transition("O", OrderState.CREATED, OrderState.VALIDATED,
                            "r", "actor")
        d = t.to_dict()
        assert d["from_state"] == "CREATED"
        assert d["to_state"]   == "VALIDATED"

    def test_repr_shows_arrow(self):
        t = make_transition("O", OrderState.CREATED, OrderState.VALIDATED,
                            "r", "actor")
        assert "→" in repr(t)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 3 — OrderEvent
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderEvent:

    def test_make_event_populates_fields(self):
        ev = make_event("ORD-001", OrderEventType.ORDER_CREATED)
        assert ev.order_id   == "ORD-001"
        assert ev.event_type == OrderEventType.ORDER_CREATED
        assert isinstance(ev.event_id, str) and len(ev.event_id) > 0
        assert ev.transition is None

    def test_event_type_for_all_states(self):
        for state in OrderState:
            et = event_type_for_state(state)
            assert isinstance(et, OrderEventType)

    def test_filled_state_maps_to_order_filled(self):
        assert event_type_for_state(OrderState.FILLED) == OrderEventType.ORDER_FILLED

    def test_event_is_immutable(self):
        ev = make_event("O", OrderEventType.ORDER_FILLED)
        with pytest.raises((AttributeError, TypeError)):
            ev.order_id = "changed"  # type: ignore[misc]

    def test_event_to_dict(self):
        ev = make_event("O", OrderEventType.ORDER_VALIDATED)
        d  = ev.to_dict()
        assert d["order_id"]   == "O"
        assert d["event_type"] == "ORDER_VALIDATED"
        assert d["transition"] is None

    def test_event_with_payload(self):
        ev = make_event("O", OrderEventType.ORDER_PARTIALLY_FILLED,
                        payload={"fill_qty": "10"})
        assert ev.payload["fill_qty"] == "10"


# ──────────────────────────────────────────────────────────────────────────────
#  PART 4 — OrderContext
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderContext:

    def test_context_fields(self, ctx: OrderContext):
        assert ctx.strategy_id  == "STRAT-001"
        assert ctx.portfolio_id == "PORT-001"
        assert ctx.decision_id  == "DEC-001"
        assert ctx.workflow_id  == "WF-001"
        assert ctx.broker_id    == ""
        assert ctx.parent_order_id is None

    def test_with_broker(self, ctx: OrderContext):
        ctx2 = ctx.with_broker("BROKER-XYZ")
        assert ctx2.broker_id   == "BROKER-XYZ"
        assert ctx.broker_id    == ""            # original unchanged
        assert ctx2.strategy_id == ctx.strategy_id

    def test_with_parent(self, ctx: OrderContext):
        ctx2 = ctx.with_parent("PARENT-001")
        assert ctx2.parent_order_id == "PARENT-001"
        assert ctx.parent_order_id  is None

    def test_context_is_immutable(self, ctx: OrderContext):
        with pytest.raises((AttributeError, TypeError)):
            ctx.strategy_id = "changed"  # type: ignore[misc]

    def test_to_dict(self, ctx: OrderContext):
        d = ctx.to_dict()
        assert d["strategy_id"]  == "STRAT-001"
        assert d["broker_id"]    == ""
        assert d["parent_order_id"] is None


# ──────────────────────────────────────────────────────────────────────────────
#  PART 5 — OrderMetadata
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderMetadata:

    def test_initial_version_is_1(self):
        m = OrderMetadata(source="test")
        assert m.version == 1

    def test_bump_version_increments(self):
        m = OrderMetadata(source="test")
        m.bump_version()
        assert m.version == 2

    def test_add_tag(self):
        m = OrderMetadata(source="test")
        m.add_tag("urgent")
        assert "urgent" in m.tags
        assert m.version == 2

    def test_remove_tag(self):
        m = OrderMetadata(source="test", tags=frozenset({"urgent", "retail"}))
        m.remove_tag("urgent")
        assert "urgent" not in m.tags
        assert "retail" in m.tags

    def test_set_note(self):
        m = OrderMetadata(source="test")
        m.set_note("strategic buy")
        assert m.notes == "strategic buy"

    def test_set_custom(self):
        m = OrderMetadata(source="test")
        m.set_custom("desk", "equity_flow")
        assert m.custom["desk"] == "equity_flow"

    def test_to_dict(self):
        m = OrderMetadata(source="factory")
        d = m.to_dict()
        assert d["source"]  == "factory"
        assert d["version"] == 1
        assert isinstance(d["tags"], list)

    def test_bump_version_sets_updated_at(self):
        m = OrderMetadata(source="test")
        before = m.updated_at
        time.sleep(0.001)
        m.bump_version()
        assert m.updated_at >= before


# ──────────────────────────────────────────────────────────────────────────────
#  PART 6 — OrderHistory
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderHistory:

    def _t(self, from_s: OrderState, to_s: OrderState, order_id: str = "O") -> OrderTransition:
        return make_transition(order_id, from_s, to_s, "r", "actor")

    def test_initial_state_empty(self):
        h = OrderHistory("O")
        assert h.count() == 0
        assert h.first() is None
        assert h.last()  is None

    def test_record_and_retrieve(self):
        h = OrderHistory("O")
        t = self._t(OrderState.CREATED, OrderState.VALIDATED)
        h.record(t)
        assert h.count() == 1
        assert h.last()  == t
        assert h.first() == t

    def test_entries_returns_tuple(self):
        h = OrderHistory("O")
        h.record(self._t(OrderState.CREATED, OrderState.VALIDATED))
        assert isinstance(h.entries(), tuple)

    def test_states_visited(self):
        h = OrderHistory("O")
        h.record(self._t(OrderState.CREATED, OrderState.VALIDATED))
        h.record(self._t(OrderState.VALIDATED, OrderState.PENDING_SUBMISSION))
        sv = h.states_visited()
        assert OrderState.VALIDATED in sv
        assert OrderState.PENDING_SUBMISSION in sv

    def test_record_wrong_order_id_raises(self):
        h = OrderHistory("O")
        t = make_transition("X", OrderState.CREATED, OrderState.VALIDATED, "r", "a")
        with pytest.raises(ValueError, match="order_id"):
            h.record(t)

    def test_total_recorded_vs_retained(self):
        h = OrderHistory("O", max_entries=3)
        for from_s, to_s in [
            (OrderState.CREATED, OrderState.VALIDATED),
            (OrderState.VALIDATED, OrderState.PENDING_SUBMISSION),
            (OrderState.PENDING_SUBMISSION, OrderState.SUBMITTED),
            (OrderState.SUBMITTED, OrderState.ACKNOWLEDGED),
        ]:
            h.record(make_transition("O", from_s, to_s, "r", "a"))
        assert h.count()         == 3   # ring-buffer limit
        assert h.total_recorded  == 4
        assert h.evicted_count   == 1

    def test_thread_safety(self):
        h   = OrderHistory("O", max_entries=1_000)
        errors: list = []

        def worker():
            for from_s, to_s in [(OrderState.CREATED, OrderState.VALIDATED),
                                   (OrderState.VALIDATED, OrderState.PENDING_SUBMISSION)]:
                try:
                    h.record(make_transition("O", from_s, to_s, "r", "a"))
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_iter(self):
        h = OrderHistory("O")
        h.record(self._t(OrderState.CREATED, OrderState.VALIDATED))
        entries = list(h)
        assert len(entries) == 1

    def test_len(self):
        h = OrderHistory("O")
        h.record(self._t(OrderState.CREATED, OrderState.VALIDATED))
        assert len(h) == 1


# ──────────────────────────────────────────────────────────────────────────────
#  PART 7 — OrderStatistics
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderStatistics:

    def test_initial_state(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        assert s.fill_pct          == 0.0
        assert s.partial_fill_count == 0
        assert s.retry_count        == 0
        assert s.cancellation_count == 0
        assert s.submitted_at      is None
        assert s.execution_time_sec is None

    def test_on_transition_submitted_records_time(self):
        s  = OrderStatistics(order_id="O", created_at=time.time())
        t  = make_transition("O", OrderState.CREATED, OrderState.SUBMITTED,
                             "r", "actor")
        s.on_transition(t)
        assert s.submitted_at == t.occurred_at

    def test_on_transition_recovering_increments_retry(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        t = make_transition("O", OrderState.FAILED, OrderState.RECOVERING,
                            "recover", "system")
        s.on_transition(t)
        assert s.retry_count == 1

    def test_on_transition_cancel_pending_increments_cancellation(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        t = make_transition("O", OrderState.ACKNOWLEDGED, OrderState.CANCEL_PENDING,
                            "user cancel", "user")
        s.on_transition(t)
        assert s.cancellation_count == 1

    def test_on_transition_failed_increments_failure(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        t = make_transition("O", OrderState.SUBMITTED, OrderState.FAILED,
                            "network error", "system")
        s.on_transition(t)
        assert s.failure_count == 1

    def test_on_transition_rejected_increments_rejection(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        t = make_transition("O", OrderState.SUBMITTED, OrderState.REJECTED,
                            "insufficient margin", "broker")
        s.on_transition(t)
        assert s.rejection_count == 1

    def test_on_fill_updates_fill_pct(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        s.on_fill(
            fill_qty=Decimal("50"), total_qty=Decimal("100"),
            filled_qty=Decimal("50"), occurred_at=time.time(),
        )
        assert abs(s.fill_pct - 50.0) < 0.001

    def test_on_fill_complete_sets_filled_at(self):
        s   = OrderStatistics(order_id="O", created_at=time.time())
        now = time.time()
        s.on_fill(
            fill_qty=Decimal("100"), total_qty=Decimal("100"),
            filled_qty=Decimal("100"), occurred_at=now,
        )
        assert s.filled_at == now

    def test_execution_time_sec(self):
        s        = OrderStatistics(order_id="O", created_at=time.time())
        sub_time = time.time()
        s.on_transition(make_transition("O", OrderState.CREATED, OrderState.SUBMITTED,
                                        "r", "a", occurred_at=sub_time))
        fill_time = sub_time + 1.5
        s.on_fill(Decimal("100"), Decimal("100"), Decimal("100"),
                  occurred_at=fill_time)
        assert abs(s.execution_time_sec - 1.5) < 0.01

    def test_state_durations_accumulated(self):
        s    = OrderStatistics(order_id="O", created_at=time.time())
        now  = time.time()
        t1   = make_transition("O", OrderState.CREATED, OrderState.VALIDATED,
                               "r", "a", occurred_at=now)
        t2   = make_transition("O", OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                               "r", "a", occurred_at=now + 1.0)
        s.on_transition(t1)
        s.on_transition(t2)
        durations = s.state_durations
        # VALIDATED state was entered at t1.occurred_at and exited at t2.occurred_at
        # so its duration should be ~1.0 second
        assert "VALIDATED" in durations
        assert durations["VALIDATED"] == pytest.approx(1.0, abs=0.05)

    def test_to_dict(self):
        s = OrderStatistics(order_id="O", created_at=time.time())
        d = s.to_dict()
        assert d["order_id"]    == "O"
        assert d["fill_pct"]    == 0.0
        assert d["retry_count"] == 0


# ──────────────────────────────────────────────────────────────────────────────
#  PART 8 — Order
# ──────────────────────────────────────────────────────────────────────────────

class TestOrder:

    def test_initial_state_is_created(self, order: Order):
        assert order.state == OrderState.CREATED

    def test_remaining_quantity_equals_quantity(self, order: Order):
        assert order.remaining_quantity == order.quantity

    def test_fill_pct_zero_initially(self, order: Order):
        assert order.fill_pct == 0.0

    def test_is_not_terminal_initially(self, order: Order):
        assert not order.is_terminal

    def test_is_not_active_initially(self, order: Order):
        # CREATED is not in ACTIVE_STATES
        assert not order.is_active

    def test_parent_order_id_from_context(self, ctx: OrderContext, factory: OrderFactory):
        ctx2 = ctx.with_parent("PARENT-001")
        o    = factory.create_market_order(
            context=ctx2, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        assert o.parent_order_id == "PARENT-001"

    def test_apply_transition_updates_state(self, order: Order):
        t = make_transition(order.order_id, OrderState.CREATED,
                            OrderState.VALIDATED, "passed", "validator")
        order._apply_transition(t)
        assert order.state == OrderState.VALIDATED

    def test_apply_transition_records_to_history(self, order: Order):
        t = make_transition(order.order_id, OrderState.CREATED,
                            OrderState.VALIDATED, "passed", "validator")
        order._apply_transition(t)
        assert order.history.count() == 1
        assert order.history.last()  == t

    def test_apply_fill_updates_filled_quantity(self, order: Order):
        order._apply_fill(Decimal("30"), Decimal("2800"), time.time())
        assert order.filled_quantity   == Decimal("30")
        assert order.remaining_quantity == Decimal("70")

    def test_apply_fill_computes_average_price(self, order: Order):
        order._apply_fill(Decimal("50"), Decimal("2800"), time.time())
        order._apply_fill(Decimal("50"), Decimal("2900"), time.time())
        assert order.average_price == pytest.approx(Decimal("2850"), abs=Decimal("1"))

    def test_apply_fill_fills_completely(self, order: Order):
        order._apply_fill(Decimal("100"), Decimal("2800"), time.time())
        assert order.remaining_quantity == Decimal("0")
        assert abs(order.fill_pct - 100.0) < 0.001

    def test_add_child(self, order: Order):
        order._add_child("CHILD-001")
        assert "CHILD-001" in order.child_order_ids

    def test_add_child_no_duplicates(self, order: Order):
        order._add_child("CHILD-001")
        order._add_child("CHILD-001")
        assert order.child_order_ids.count("CHILD-001") == 1

    def test_to_dict_fields(self, order: Order):
        d = order.to_dict()
        assert d["state"]            == "CREATED"
        assert d["instrument"]       == "RELIANCE"
        assert d["side"]             == "BUY"
        assert d["is_terminal"]      is False
        assert "context"             in d
        assert "metadata"            in d
        assert "statistics"          in d

    def test_repr(self, order: Order):
        r = repr(order)
        assert "RELIANCE" in r
        assert "CREATED"  in r


# ──────────────────────────────────────────────────────────────────────────────
#  PART 9 — OrderValidation
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderValidation:

    @pytest.fixture
    def validator(self) -> OrderValidator:
        return OrderValidator()

    def test_valid_order_passes(self, order: Order, validator: OrderValidator):
        result = validator.validate_new(order)
        assert result.passed
        assert len(result.errors) == 0

    def test_invalid_quantity_zero(self, factory: OrderFactory,
                                   ctx: OrderContext, validator: OrderValidator):
        # Build order manually to bypass factory validation
        o = Order(
            order_id   = "O-BAD",
            context    = ctx,
            instrument = "TCS",
            exchange   = "NSE",
            side       = OrderSide.BUY,
            order_type = OrderType.MARKET,
            quantity   = Decimal("0"),
        )
        result = validator.validate_new(o)
        assert not result.passed
        assert any("positive" in e for e in result.errors)

    def test_invalid_empty_order_id(self, ctx: OrderContext, validator: OrderValidator):
        o = Order(
            order_id   = "",
            context    = ctx,
            instrument = "TCS",
            exchange   = "NSE",
            side       = OrderSide.BUY,
            order_type = OrderType.MARKET,
            quantity   = Decimal("10"),
        )
        result = validator.validate_new(o)
        assert not result.passed
        assert any("order_id" in e for e in result.errors)

    def test_limit_order_requires_limit_price(self, ctx: OrderContext,
                                               validator: OrderValidator):
        o = Order(
            order_id   = "O-LIM",
            context    = ctx,
            instrument = "TCS",
            exchange   = "NSE",
            side       = OrderSide.BUY,
            order_type = OrderType.LIMIT,
            quantity   = Decimal("10"),
            limit_price = None,
        )
        result = validator.validate_new(o)
        assert not result.passed
        assert any("limit_price" in e for e in result.errors)

    def test_stop_order_requires_stop_price(self, ctx: OrderContext,
                                             validator: OrderValidator):
        o = Order(
            order_id   = "O-STOP",
            context    = ctx,
            instrument = "TCS",
            exchange   = "NSE",
            side       = OrderSide.SELL,
            order_type = OrderType.STOP,
            quantity   = Decimal("10"),
            stop_price = None,
        )
        result = validator.validate_new(o)
        assert not result.passed

    def test_valid_transition(self, order: Order, validator: OrderValidator):
        result = validator.validate_transition(order, OrderState.VALIDATED)
        assert result.passed

    def test_invalid_transition_direct_to_filled(self, order: Order,
                                                  validator: OrderValidator):
        result = validator.validate_transition(order, OrderState.FILLED)
        assert not result.passed

    def test_terminal_order_cannot_transition(self, order: Order,
                                               validator: OrderValidator):
        order._apply_transition(
            make_transition(order.order_id, OrderState.CREATED,
                            OrderState.FILLED, "r", "a")
        )
        # Manually force terminal state for this test
        # (CREATED → FILLED is invalid, but we're testing the terminal guard)
        # Instead, apply a valid chain to reach FILLED:
        order2 = Order(
            order_id=order.order_id + "2", context=order.context,
            instrument=order.instrument, exchange=order.exchange,
            side=order.side, order_type=order.order_type,
            quantity=order.quantity, limit_price=order.limit_price,
        )
        # Force FILLED state for test
        object.__setattr__(order2, "state", OrderState.FILLED) if hasattr(order2, "__dict__") else None
        order2.state = OrderState.FILLED  # force for test
        result = validator.validate_transition(order2, OrderState.RECOVERING)
        assert not result.passed

    def test_valid_fill(self, order: Order, validator: OrderValidator):
        # Place order in ACKNOWLEDGED state first
        order.state = OrderState.ACKNOWLEDGED
        result = validator.validate_fill(order, Decimal("50"), Decimal("2800"))
        assert result.passed

    def test_overfill_rejected(self, order: Order, validator: OrderValidator):
        order.state = OrderState.ACKNOWLEDGED
        result = validator.validate_fill(order, Decimal("200"), Decimal("2800"))
        assert not result.passed
        assert any("remaining_quantity" in e or "exceed" in e for e in result.errors)

    def test_negative_fill_price_rejected(self, order: Order,
                                           validator: OrderValidator):
        order.state = OrderState.ACKNOWLEDGED
        result = validator.validate_fill(order, Decimal("10"), Decimal("-100"))
        assert not result.passed

    def test_validation_result_bool(self):
        assert bool(ValidationResult.ok())
        assert not bool(ValidationResult.fail("error"))


# ──────────────────────────────────────────────────────────────────────────────
#  PART 10 — OrderFactory
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderFactory:

    def test_create_market_order(self, factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("50"),
        )
        assert o.order_type == OrderType.MARKET
        assert o.limit_price is None
        assert o.stop_price  is None
        assert o.state       == OrderState.CREATED

    def test_create_limit_order(self, factory: OrderFactory, ctx: OrderContext):
        o = factory.create_limit_order(
            context=ctx, instrument="INFY", exchange="NSE",
            side=OrderSide.SELL, quantity=Decimal("25"),
            limit_price=Decimal("1500"),
        )
        assert o.order_type  == OrderType.LIMIT
        assert o.limit_price == Decimal("1500")

    def test_create_stop_order(self, factory: OrderFactory, ctx: OrderContext):
        o = factory.create_stop_order(
            context=ctx, instrument="HDFCBANK", exchange="NSE",
            side=OrderSide.SELL, quantity=Decimal("10"),
            stop_price=Decimal("1600"),
        )
        assert o.order_type == OrderType.STOP
        assert o.stop_price == Decimal("1600")

    def test_create_stop_limit_order(self, factory: OrderFactory, ctx: OrderContext):
        o = factory.create_stop_limit_order(
            context=ctx, instrument="WIPRO", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("20"),
            stop_price=Decimal("400"), limit_price=Decimal("405"),
        )
        assert o.order_type  == OrderType.STOP_LIMIT
        assert o.stop_price  == Decimal("400")
        assert o.limit_price == Decimal("405")

    def test_custom_order_id(self, factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("5"),
            order_id="MY-ORDER-001",
        )
        assert o.order_id == "MY-ORDER-001"

    def test_factory_validates_and_raises_on_invalid(self, factory: OrderFactory,
                                                       ctx: OrderContext):
        with pytest.raises(OrderValidationError):
            factory.create_market_order(
                context=ctx, instrument="TCS", exchange="NSE",
                side=OrderSide.BUY, quantity=Decimal("0"),  # invalid
            )

    def test_clone_produces_new_order_id(self, factory: OrderFactory,
                                          order: Order):
        clone = factory.clone(order)
        assert clone.order_id != order.order_id
        assert clone.state    == OrderState.CREATED
        assert clone.filled_quantity == Decimal("0")

    def test_clone_accepts_custom_id(self, factory: OrderFactory, order: Order):
        clone = factory.clone(order, new_order_id="CLONE-001")
        assert clone.order_id == "CLONE-001"

    def test_created_order_quantity_is_decimal(self, factory: OrderFactory,
                                               ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("100"),
        )
        assert isinstance(o.quantity, Decimal)

    def test_system_id_and_version(self, factory: OrderFactory):
        assert factory.SYSTEM_ID.startswith("iios:execution:lifecycle")
        assert factory.VERSION == "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
#  PART 11 — OrderRegistry
# ──────────────────────────────────────────────────────────────────────────────

class TestOrderRegistry:

    def test_registry_not_running_before_start(self):
        reg = OrderRegistry()
        assert not reg.is_running

    def test_registry_running_after_start(self, registry: OrderRegistry):
        assert registry.is_running

    def test_register_and_get(self, registry: OrderRegistry, order: Order):
        registry.register(order)
        retrieved = registry.get(order.order_id)
        assert retrieved.order_id == order.order_id

    def test_register_duplicate_raises(self, registry: OrderRegistry, order: Order):
        registry.register(order)
        with pytest.raises(DuplicateOrderError):
            registry.register(order)

    def test_get_not_found_raises(self, registry: OrderRegistry):
        with pytest.raises(OrderNotFoundError):
            registry.get("NONEXISTENT")

    def test_register_when_not_running_raises(self, order: Order):
        reg = OrderRegistry()
        with pytest.raises(RegistryNotRunningError):
            reg.register(order)

    def test_capacity_exceeded_raises(self, factory: OrderFactory, ctx: OrderContext):
        reg = OrderRegistry(max_orders=2)
        reg.start()
        try:
            for i in range(2):
                o = factory.create_market_order(
                    context=ctx, instrument="TCS", exchange="NSE",
                    side=OrderSide.BUY, quantity=Decimal("10"),
                    order_id=f"ORD-{i}",
                )
                reg.register(o)
            extra = factory.create_market_order(
                context=ctx, instrument="TCS", exchange="NSE",
                side=OrderSide.BUY, quantity=Decimal("10"),
                order_id="ORD-EXTRA",
            )
            with pytest.raises(RegistryCapacityError):
                reg.register(extra)
        finally:
            reg.stop()

    def test_apply_transition_valid(self, registry: OrderRegistry, order: Order):
        registry.register(order)
        updated, transition, event = registry.apply_transition(
            order.order_id, OrderState.VALIDATED,
            reason="passed", actor=ACTOR_VALIDATOR,
        )
        assert updated.state       == OrderState.VALIDATED
        assert transition.to_state == OrderState.VALIDATED
        assert event.event_type    == OrderEventType.ORDER_VALIDATED

    def test_apply_transition_invalid_raises(self, registry: OrderRegistry,
                                              order: Order):
        registry.register(order)
        with pytest.raises(InvalidTransitionError):
            registry.apply_transition(
                order.order_id, OrderState.FILLED,
                reason="skip", actor=ACTOR_SYSTEM,
            )

    def test_apply_transition_on_terminal_raises(self, registry: OrderRegistry,
                                                  factory: OrderFactory,
                                                  ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        # Force to FILLED via the fill mechanism
        # Validate + pending + submit + acknowledge first
        for to_s, reason in [
            (OrderState.VALIDATED, "ok"),
            (OrderState.PENDING_SUBMISSION, "queued"),
            (OrderState.SUBMITTED, "sent"),
            (OrderState.ACKNOWLEDGED, "ack"),
        ]:
            registry.apply_transition(o.order_id, to_s, reason=reason, actor=ACTOR_SYSTEM)
        registry.apply_fill(o.order_id, Decimal("10"), Decimal("3000"))
        assert o.state == OrderState.FILLED
        with pytest.raises(OrderTerminalError):
            registry.apply_transition(o.order_id, OrderState.RECOVERING,
                                      reason="try", actor=ACTOR_SYSTEM)

    def test_apply_fill_partial(self, registry: OrderRegistry,
                                 factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("100"),
        )
        registry.register(o)
        # Advance to ACKNOWLEDGED
        for to_s in [OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                     OrderState.SUBMITTED, OrderState.ACKNOWLEDGED]:
            registry.apply_transition(o.order_id, to_s, reason="ok",
                                      actor=ACTOR_SYSTEM)
        updated, _, event = registry.apply_fill(o.order_id, Decimal("40"),
                                                 Decimal("3000"))
        assert updated.state         == OrderState.PARTIALLY_FILLED
        assert updated.filled_quantity == Decimal("40")
        assert event.event_type == OrderEventType.ORDER_PARTIALLY_FILLED

    def test_apply_fill_complete(self, registry: OrderRegistry,
                                  factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        for to_s in [OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                     OrderState.SUBMITTED, OrderState.ACKNOWLEDGED]:
            registry.apply_transition(o.order_id, to_s, reason="ok",
                                      actor=ACTOR_SYSTEM)
        updated, _, event = registry.apply_fill(o.order_id, Decimal("10"),
                                                 Decimal("3000"))
        assert updated.state == OrderState.FILLED
        assert event.event_type == OrderEventType.ORDER_FILLED

    def test_apply_fill_overfill_raises(self, registry: OrderRegistry,
                                         factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        for to_s in [OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                     OrderState.SUBMITTED, OrderState.ACKNOWLEDGED]:
            registry.apply_transition(o.order_id, to_s, reason="ok",
                                      actor=ACTOR_SYSTEM)
        with pytest.raises(InvalidFillError):
            registry.apply_fill(o.order_id, Decimal("99"), Decimal("3000"))

    def test_get_by_portfolio(self, registry: OrderRegistry,
                               factory: OrderFactory, ctx: OrderContext):
        for i in range(3):
            o = factory.create_market_order(
                context=ctx, instrument="TCS", exchange="NSE",
                side=OrderSide.BUY, quantity=Decimal("10"),
                order_id=f"P-ORD-{i}",
            )
            registry.register(o)
        orders = registry.get_by_portfolio("PORT-001")
        assert len(orders) >= 3

    def test_get_by_strategy(self, registry: OrderRegistry,
                              factory: OrderFactory, ctx: OrderContext):
        for i in range(2):
            o = factory.create_market_order(
                context=ctx, instrument="TCS", exchange="NSE",
                side=OrderSide.BUY, quantity=Decimal("10"),
                order_id=f"S-ORD-{i}",
            )
            registry.register(o)
        orders = registry.get_by_strategy("STRAT-001")
        assert len(orders) >= 2

    def test_get_active_returns_active_orders(self, registry: OrderRegistry,
                                               factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="ok", actor=ACTOR_SYSTEM)
        active = registry.get_active()
        assert any(a.order_id == o.order_id for a in active)

    def test_listener_called_on_transition(self, registry: OrderRegistry,
                                            order: Order):
        events: list[OrderEvent] = []
        registry.add_listener(events.append)
        registry.register(order)
        registry.apply_transition(order.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)
        assert len(events) == 1
        assert events[0].event_type == OrderEventType.ORDER_VALIDATED

    def test_listener_removed(self, registry: OrderRegistry, order: Order):
        events: list[OrderEvent] = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        registry.register(order)
        registry.apply_transition(order.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)
        assert len(events) == 0

    def test_statistics(self, registry: OrderRegistry, order: Order):
        registry.register(order)
        stats = registry.statistics()
        assert isinstance(stats, RegistryStatistics)
        assert stats.total_registered >= 1
        assert stats.capacity == registry._max_orders

    def test_contains(self, registry: OrderRegistry, order: Order):
        assert not registry.contains(order.order_id)
        registry.register(order)
        assert registry.contains(order.order_id)

    def test_count(self, registry: OrderRegistry, order: Order):
        before = registry.count()
        registry.register(order)
        assert registry.count() == before + 1

    def test_system_id_and_version(self, registry: OrderRegistry):
        assert registry.SYSTEM_ID.startswith("iios:execution:lifecycle")
        assert registry.VERSION == "1.0.0"

    def test_faulty_listener_does_not_crash_registry(self, registry: OrderRegistry,
                                                       order: Order):
        def bad_listener(event: OrderEvent) -> None:
            raise RuntimeError("listener error")

        registry.add_listener(bad_listener)
        registry.register(order)
        # Should not raise
        registry.apply_transition(order.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 12 — Integration: end-to-end lifecycle traversal
# ──────────────────────────────────────────────────────────────────────────────

class TestStateMachineIntegration:

    def _advance_to(
        self,
        registry: OrderRegistry,
        order: Order,
        target: OrderState,
    ) -> None:
        """Advance order through states up to and including *target*."""
        path = [
            (OrderState.CREATED,            OrderState.VALIDATED),
            (OrderState.VALIDATED,          OrderState.PENDING_SUBMISSION),
            (OrderState.PENDING_SUBMISSION, OrderState.SUBMITTED),
            (OrderState.SUBMITTED,          OrderState.ACKNOWLEDGED),
        ]
        for from_s, to_s in path:
            if order.state == from_s:
                registry.apply_transition(order.order_id, to_s,
                                          reason="integration", actor=ACTOR_SYSTEM)
            if order.state == target:
                return

    def test_happy_path_to_fill(self, registry: OrderRegistry,
                                 factory: OrderFactory, ctx: OrderContext):
        o = factory.create_limit_order(
            context=ctx, instrument="RELIANCE", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("50"),
            limit_price=Decimal("2800"),
        )
        registry.register(o)
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_VALIDATOR)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="queued", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.SUBMITTED,
                                  reason="sent", actor=ACTOR_BROKER)
        registry.apply_transition(o.order_id, OrderState.ACKNOWLEDGED,
                                  reason="ack", actor=ACTOR_EXCHANGE)
        # Two partial fills then complete
        registry.apply_fill(o.order_id, Decimal("20"), Decimal("2800"))
        registry.apply_fill(o.order_id, Decimal("30"), Decimal("2795"))
        assert o.state == OrderState.FILLED
        assert o.filled_quantity == Decimal("50")
        assert o.is_terminal
        assert not o.is_active
        assert o.statistics.partial_fill_count == 1

    def test_cancel_flow(self, registry: OrderRegistry,
                          factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="INFY", exchange="NSE",
            side=OrderSide.SELL, quantity=Decimal("30"),
        )
        registry.register(o)
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_VALIDATOR)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="queued", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.SUBMITTED,
                                  reason="sent", actor=ACTOR_BROKER)
        registry.apply_transition(o.order_id, OrderState.ACKNOWLEDGED,
                                  reason="ack", actor=ACTOR_EXCHANGE)
        registry.apply_transition(o.order_id, OrderState.CANCEL_PENDING,
                                  reason="user cancel", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.CANCELLED,
                                  reason="confirmed", actor=ACTOR_EXCHANGE)
        assert o.state == OrderState.CANCELLED

    def test_recovery_flow(self, registry: OrderRegistry,
                            factory: OrderFactory, ctx: OrderContext):
        o = factory.create_market_order(
            context=ctx, instrument="WIPRO", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("15"),
        )
        registry.register(o)
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_VALIDATOR)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="queued", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.FAILED,
                                  reason="network timeout", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.RECOVERING,
                                  reason="recovery initiated", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.RECOVERED,
                                  reason="recovery succeeded", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="resubmit", actor=ACTOR_SYSTEM)
        assert o.state              == OrderState.PENDING_SUBMISSION
        assert o.statistics.retry_count == 1

    def test_history_contains_all_transitions(self, registry: OrderRegistry,
                                               factory: OrderFactory, ctx: OrderContext):
        o = factory.create_limit_order(
            context=ctx, instrument="HDFC", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
            limit_price=Decimal("1700"),
        )
        registry.register(o)
        for to_s in [OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                     OrderState.SUBMITTED, OrderState.ACKNOWLEDGED]:
            registry.apply_transition(o.order_id, to_s,
                                      reason="ok", actor=ACTOR_SYSTEM)
        registry.apply_fill(o.order_id, Decimal("10"), Decimal("1700"))
        # History: VALIDATED, PENDING_SUBMISSION, SUBMITTED, ACKNOWLEDGED,
        #           + transition from fill → FILLED
        assert o.history.count() >= 5
        assert OrderState.FILLED in o.history.states_visited()

    def test_cancel_pending_to_filled_race(self, registry: OrderRegistry,
                                            factory: OrderFactory, ctx: OrderContext):
        """Simulates an order filled during a cancel race."""
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        for to_s in [OrderState.VALIDATED, OrderState.PENDING_SUBMISSION,
                     OrderState.SUBMITTED, OrderState.ACKNOWLEDGED]:
            registry.apply_transition(o.order_id, to_s,
                                      reason="ok", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.CANCEL_PENDING,
                                  reason="cancel initiated", actor=ACTOR_SYSTEM)
        # Exchange fills the order before cancel reaches it
        registry.apply_fill(o.order_id, Decimal("10"), Decimal("3000"))
        assert o.state == OrderState.FILLED


# ──────────────────────────────────────────────────────────────────────────────
#  PART 13 — Thread Safety
# ──────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_concurrent_registrations(self, registry: OrderRegistry,
                                       factory: OrderFactory, ctx: OrderContext):
        """Register N orders from N threads; all must succeed."""
        n      = 50
        errors: list = []

        def worker(i: int) -> None:
            try:
                o = factory.create_market_order(
                    context=ctx, instrument="TCS", exchange="NSE",
                    side=OrderSide.BUY, quantity=Decimal("10"),
                    order_id=f"CONC-{i:04d}",
                )
                registry.register(o)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert registry.count() >= n

    def test_concurrent_transitions_on_same_order(self, registry: OrderRegistry,
                                                    factory: OrderFactory,
                                                    ctx: OrderContext):
        """
        Only one thread should win each transition; the rest should
        receive InvalidTransitionError (order already advanced).
        """
        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        # Advance to SUBMITTED so concurrent attempts to ACKNOWLEDGED are valid
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.PENDING_SUBMISSION,
                                  reason="ok", actor=ACTOR_SYSTEM)
        registry.apply_transition(o.order_id, OrderState.SUBMITTED,
                                  reason="ok", actor=ACTOR_SYSTEM)

        successes: list = []
        failures:  list = []

        def try_ack():
            try:
                registry.apply_transition(o.order_id, OrderState.ACKNOWLEDGED,
                                          reason="ack", actor=ACTOR_EXCHANGE)
                successes.append(1)
            except (InvalidTransitionError, OrderTerminalError):
                failures.append(1)

        threads = [threading.Thread(target=try_ack) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should succeed
        assert len(successes) == 1
        assert o.state == OrderState.ACKNOWLEDGED

    def test_concurrent_listeners(self, registry: OrderRegistry,
                                   factory: OrderFactory, ctx: OrderContext):
        """Multiple listeners registered concurrently should all fire."""
        events: list = []
        lock         = threading.Lock()

        def make_listener(n: int):
            def listener(ev: OrderEvent) -> None:
                with lock:
                    events.append(n)
            return listener

        for i in range(5):
            registry.add_listener(make_listener(i))

        o = factory.create_market_order(
            context=ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        registry.register(o)
        registry.apply_transition(o.order_id, OrderState.VALIDATED,
                                  reason="ok", actor=ACTOR_SYSTEM)
        assert len(events) == 5
