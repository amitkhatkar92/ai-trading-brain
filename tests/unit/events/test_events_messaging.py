"""
tests/unit/events/test_events_messaging.py
============================================
Comprehensive test-suite for the IIOS Event & Messaging Framework.
Target: ≥120 tests across all components.
"""

from __future__ import annotations

import time
import threading
import pytest

# ── helpers ────────────────────────────────────────────────────────────────────

def _make_event(event_type: str = "test.event", payload: dict | None = None, **kwargs):
    from iios.events import make_event_id, EventMetadata, Event
    meta = EventMetadata(
        event_id=make_event_id(),
        event_type=event_type,
        source="test",
        **kwargs,
    )
    return Event(metadata=meta, payload=dict(payload or {}))


def _make_message(payload: dict | None = None, **kw):
    from iios.events.messaging.message import Message, MessageEnvelope, MessageType
    env = MessageEnvelope(message_type=MessageType.EVENT, source="test", **kw)
    return Message(payload=dict(payload or {}), envelope=env)


def _make_command(command_type: str = "test.cmd", payload: dict | None = None):
    from iios.events.messaging.message import Command, MessageEnvelope, MessageType
    env = MessageEnvelope(message_type=MessageType.COMMAND, source="test")
    return Command(command_type=command_type, payload=dict(payload or {}), source="test", envelope=env)


def _make_query(query_type: str = "test.query", params: dict | None = None, timeout: float = 30.0):
    from iios.events.messaging.message import Query, MessageEnvelope, MessageType
    env = MessageEnvelope(message_type=MessageType.QUERY, source="test")
    return Query(query_type=query_type, parameters=dict(params or {}), source="test", reply_to="", timeout=timeout, envelope=env)


# ══════════════════════════════════════════════════════════════════════════════
# 1. EventMetadata & Event
# ══════════════════════════════════════════════════════════════════════════════

class TestEventMetadata:
    def test_make_event_id_unique(self):
        from iios.events import make_event_id
        ids = {make_event_id() for _ in range(100)}
        assert len(ids) == 100

    def test_make_correlation_id(self):
        from iios.events import make_correlation_id
        c = make_correlation_id()
        assert isinstance(c, str) and len(c) == 36

    def test_metadata_defaults(self):
        from iios.events import EventMetadata, make_event_id
        m = EventMetadata(event_id=make_event_id(), event_type="x", source="s")
        assert m.retry_count == 0
        assert m.max_retries == 3
        assert not m.is_expired

    def test_metadata_child(self):
        from iios.events import EventMetadata, make_event_id
        m = EventMetadata(event_id=make_event_id(), event_type="parent", source="s")
        child = m.child("child.event")
        assert child.causation_id == m.event_id
        assert child.correlation_id == m.correlation_id
        assert child.event_type == "child.event"

    def test_event_is_expired(self):
        from iios.events import EventMetadata, Event, make_event_id
        meta = EventMetadata(
            event_id=make_event_id(), event_type="x", source="s",
            ttl=0.001,
        )
        time.sleep(0.05)
        event = Event(metadata=meta, payload={})
        assert event.is_expired

    def test_event_priority_ordering(self):
        from iios.events import EventPriority
        e1 = _make_event(priority=EventPriority.CRITICAL)
        e2 = _make_event(priority=EventPriority.LOW)
        assert e1 < e2   # lower value = higher priority

    def test_event_payload_preserved(self):
        e = _make_event(payload={"amount": 42})
        assert e.payload["amount"] == 42


# ══════════════════════════════════════════════════════════════════════════════
# 2. EventPriority / MessagePriority
# ══════════════════════════════════════════════════════════════════════════════

class TestEventPriority:
    def test_from_str_event(self):
        from iios.events import EventPriority
        assert EventPriority.from_str("high") == EventPriority.HIGH
        assert EventPriority.from_str("CRITICAL") == EventPriority.CRITICAL

    def test_from_str_fallback(self):
        from iios.events import EventPriority
        assert EventPriority.from_str("unknown") == EventPriority.NORMAL

    def test_message_priority_order(self):
        from iios.events import MessagePriority
        assert MessagePriority.URGENT < MessagePriority.NORMAL
        assert MessagePriority.NORMAL < MessagePriority.DEFERRED

    def test_from_str_message(self):
        from iios.events import MessagePriority
        assert MessagePriority.from_str("urgent") == MessagePriority.URGENT


# ══════════════════════════════════════════════════════════════════════════════
# 3. EventContext
# ══════════════════════════════════════════════════════════════════════════════

class TestEventContext:
    def test_push_pop(self):
        from iios.events import push_event, pop_event, current_event, get_event_context
        ctx = get_event_context()
        ctx.reset()
        e = _make_event()
        assert current_event() is None
        push_event(e)
        assert current_event() is e
        pop_event()
        assert current_event() is None

    def test_event_scope_cm(self):
        from iios.events import event_scope, current_event, get_event_context
        ctx = get_event_context()
        ctx.reset()
        e = _make_event()
        with event_scope(e):
            assert current_event() is e
        assert current_event() is None

    def test_span_recording(self):
        from iios.events import get_event_context
        ctx = get_event_context()
        ctx.reset()
        e = _make_event("span.test")
        with ctx.span("my_handler", e) as span:
            time.sleep(0.01)
        spans = ctx.spans()
        assert len(spans) >= 1
        assert spans[-1].handler_name == "my_handler"
        assert spans[-1].duration_ms >= 5


# ══════════════════════════════════════════════════════════════════════════════
# 4. EventFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestEventFactory:
    def test_create(self):
        from iios.events import EventFactory
        f = EventFactory("src")
        e = f.create("order.placed", {"qty": 10})
        assert e.event_type == "order.placed"
        assert e.payload["qty"] == 10

    def test_sticky(self):
        from iios.events import EventFactory
        f = EventFactory("src")
        e = f.sticky("price.update", {"price": 100})
        assert e.metadata.sticky is True

    def test_once(self):
        from iios.events import EventFactory
        f = EventFactory("src")
        e = f.once("one.shot", {})
        assert e.metadata.one_time is True

    def test_delayed(self):
        from iios.events import EventFactory
        f = EventFactory("src")
        e = f.delayed("late.event", 60, {})
        # is_due should be False (scheduled in the future)
        assert e.metadata.is_due is False

    def test_child_of(self):
        from iios.events import EventFactory
        f = EventFactory("src")
        parent = f.create("parent", {})
        child = f.child_of(parent, "child", {})
        assert child.metadata.causation_id == parent.event_id

    def test_make_classmethod(self):
        from iios.events import EventFactory
        e = EventFactory.make("ping", {"x": 1}, source="test")
        assert e.event_type == "ping"


# ══════════════════════════════════════════════════════════════════════════════
# 5. EventRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestEventRegistry:
    def setup_method(self):
        from iios.events import reset_event_registry
        reset_event_registry()

    def test_register_and_get(self):
        from iios.events import get_event_registry, EventTypeDescriptor
        reg = get_event_registry()
        reg.register(EventTypeDescriptor(event_type="test.ev", description="Test"))
        assert reg.has("test.ev")
        desc = reg.get("test.ev")
        assert desc is not None
        assert desc.description == "Test"

    def test_unregister(self):
        from iios.events import get_event_registry, EventTypeDescriptor
        reg = get_event_registry()
        reg.register(EventTypeDescriptor(event_type="temp.ev"))
        assert reg.has("temp.ev")
        reg.unregister("temp.ev")
        assert not reg.has("temp.ev")

    def test_validate_with_validator(self):
        from iios.events import get_event_registry, EventTypeDescriptor
        reg = get_event_registry()
        reg.register(EventTypeDescriptor(
            event_type="validated.ev",
            validator=lambda p: "price" in p,
        ))
        assert reg.validate_payload("validated.ev", {"price": 100})
        assert not reg.validate_payload("validated.ev", {"qty": 5})

    def test_list_by_owner(self):
        from iios.events import get_event_registry, EventTypeDescriptor
        reg = get_event_registry()
        reg.register(EventTypeDescriptor(event_type="a.ev", owner="team_a"))
        reg.register(EventTypeDescriptor(event_type="b.ev", owner="team_b"))
        owned = reg.list_by_owner("team_a")
        assert any(d.event_type == "a.ev" for d in owned)

    def test_singleton(self):
        from iios.events import get_event_registry
        r1 = get_event_registry()
        r2 = get_event_registry()
        assert r1 is r2


# ══════════════════════════════════════════════════════════════════════════════
# 6. EventDispatcher
# ══════════════════════════════════════════════════════════════════════════════

class TestEventDispatcher:
    def test_basic_dispatch(self):
        from iios.events import EventDispatcher
        disp = EventDispatcher()
        results = []
        disp.subscribe("ev.type", lambda e: results.append(e))
        e = _make_event("ev.type")
        r = disp.dispatch(e)
        assert r.succeeded == 1
        assert len(results) == 1

    def test_wildcard_dispatch(self):
        from iios.events import EventDispatcher, WILDCARD
        disp = EventDispatcher()
        seen = []
        disp.subscribe(WILDCARD, lambda e: seen.append(e.event_type))
        disp.dispatch(_make_event("a.b"))
        disp.dispatch(_make_event("c.d"))
        assert len(seen) == 2

    def test_one_time_subscriber(self):
        from iios.events import EventDispatcher
        disp = EventDispatcher()
        count = [0]
        disp.subscribe("once.ev", lambda e: count.__setitem__(0, count[0] + 1), one_time=True)
        disp.dispatch(_make_event("once.ev"))
        disp.dispatch(_make_event("once.ev"))
        assert count[0] == 1

    def test_handler_failure_isolated(self):
        from iios.events import EventDispatcher
        disp = EventDispatcher(isolate_failures=True)
        results = []
        disp.subscribe("x", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        disp.subscribe("x", lambda e: results.append("ok"))
        r = disp.dispatch(_make_event("x"))
        assert r.failed == 1
        assert r.succeeded == 1
        assert results == ["ok"]

    def test_subscriber_predicate(self):
        from iios.events import EventDispatcher
        disp = EventDispatcher()
        received = []
        disp.subscribe(
            "pred.ev",
            lambda e: received.append(e),
            predicate=lambda e: e.payload.get("value", 0) > 5,
        )
        disp.dispatch(_make_event("pred.ev", {"value": 3}))
        disp.dispatch(_make_event("pred.ev", {"value": 10}))
        assert len(received) == 1

    def test_priority_ordering(self):
        from iios.events import EventDispatcher
        order = []
        disp = EventDispatcher()
        disp.subscribe("p.ev", lambda e: order.append("low"), priority=100)
        disp.subscribe("p.ev", lambda e: order.append("high"), priority=1)
        disp.dispatch(_make_event("p.ev"))
        assert order == ["high", "low"]


# ══════════════════════════════════════════════════════════════════════════════
# 7. EventRouter
# ══════════════════════════════════════════════════════════════════════════════

class TestEventRouter:
    def test_route_by_pattern(self):
        from iios.events import EventRouter, RouteRule
        router = EventRouter()
        router.add_rule(RouteRule(name="orders", pattern="order.*", destination="order_queue"))
        e = _make_event("order.placed")
        destinations = router.route(e)
        assert "order_queue" in destinations

    def test_no_match_default(self):
        from iios.events import EventRouter
        router = EventRouter(default_destination="fallback")
        e = _make_event("unknown.event")
        assert router.route_first(e) == "fallback"

    def test_no_route_raises(self):
        from iios.events import EventRouter, NoRouteError
        router = EventRouter()
        with pytest.raises(NoRouteError):
            router.route_first(_make_event("no.route"))

    def test_remove_rule(self):
        from iios.events import EventRouter, RouteRule
        router = EventRouter()
        router.add_rule(RouteRule(name="r1", pattern="a.*", destination="d1"))
        router.remove_rule("r1")
        e = _make_event("a.test")
        assert not router.has_route(e)


# ══════════════════════════════════════════════════════════════════════════════
# 8. EventBus
# ══════════════════════════════════════════════════════════════════════════════

class TestEventBus:
    def setup_method(self):
        from iios.events import reset_event_bus
        reset_event_bus()

    def teardown_method(self):
        from iios.events import get_event_bus
        try:
            get_event_bus().stop()
        except Exception:
            pass
        from iios.events import reset_event_bus
        reset_event_bus()

    def test_subscribe_and_publish(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        received = []
        bus.subscribe("ev.x", lambda e: received.append(e))
        r = bus.publish(_make_event("ev.x"))
        assert r.succeeded == 1
        assert len(received) == 1

    def test_broadcast(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        count = [0]
        bus.subscribe("*", lambda e: count.__setitem__(0, count[0] + 1))
        n = bus.broadcast(_make_event("any.type"))
        assert n >= 1

    def test_sticky_event(self):
        from iios.events import get_event_bus, EventFactory
        bus = get_event_bus()
        f = EventFactory("test")
        sticky_e = f.sticky("price.update", {"price": 42})
        bus.publish(sticky_e)
        # Subscribe AFTER publish — should receive cached value
        late_results = []
        bus.subscribe_sticky("price.update", lambda e: late_results.append(e))
        assert len(late_results) == 1
        assert late_results[0].payload["price"] == 42

    def test_once_subscriber(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        count = [0]
        bus.subscribe_once("single.use", lambda e: count.__setitem__(0, count[0] + 1))
        bus.publish(_make_event("single.use"))
        bus.publish(_make_event("single.use"))
        assert count[0] == 1

    def test_unsubscribe(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        received = []
        sub_id = bus.subscribe("unsub.ev", lambda e: received.append(e))
        bus.publish(_make_event("unsub.ev"))
        bus.unsubscribe(sub_id)
        bus.publish(_make_event("unsub.ev"))
        assert len(received) == 1

    def test_history(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        for _ in range(3):
            bus.publish(_make_event("hist.ev"))
        h = bus.history()
        assert len(h) >= 3

    def test_dead_letter_queue(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        bus.subscribe("dlq.ev", lambda e: (_ for _ in ()).throw(RuntimeError("fail")))
        bus.publish(_make_event("dlq.ev"))
        dlq = bus.dead_letter_queue()
        assert len(dlq) >= 1

    def test_stats(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        bus.subscribe("stats.ev", lambda e: None)
        bus.publish(_make_event("stats.ev"))
        s = bus.stats()
        assert s.published >= 1

    def test_singleton(self):
        from iios.events import get_event_bus
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2


# ══════════════════════════════════════════════════════════════════════════════
# 9. EventManager
# ══════════════════════════════════════════════════════════════════════════════

class TestEventManager:
    def setup_method(self):
        from iios.events import reset_event_manager, reset_event_bus, reset_event_registry
        reset_event_bus()
        reset_event_registry()
        reset_event_manager()

    def teardown_method(self):
        from iios.events import get_event_bus
        try:
            get_event_bus().stop()
        except Exception:
            pass
        from iios.events import reset_event_manager, reset_event_bus, reset_event_registry
        reset_event_bus()
        reset_event_registry()
        reset_event_manager()

    def test_emit_and_receive(self):
        from iios.events import get_event_manager
        mgr = get_event_manager()
        received = []
        mgr.on("order.placed", lambda e: received.append(e))
        count = mgr.emit("order.placed", {"qty": 10})
        assert count >= 1
        assert received[0].payload["qty"] == 10

    def test_on_all(self):
        from iios.events import get_event_manager
        mgr = get_event_manager()
        captured = []
        mgr.on_all(lambda e: captured.append(e.event_type))
        mgr.emit("a.1", {})
        mgr.emit("b.2", {})
        assert "a.1" in captured
        assert "b.2" in captured

    def test_off(self):
        from iios.events import get_event_manager
        mgr = get_event_manager()
        hits = []
        sub = mgr.on("detach.ev", lambda e: hits.append(1))
        mgr.emit("detach.ev", {})
        mgr.off(sub)
        mgr.emit("detach.ev", {})
        assert len(hits) == 1

    def test_register_event(self):
        from iios.events import get_event_manager
        mgr = get_event_manager()
        mgr.register_event("custom.ev", description="A custom event", owner="team_x")
        assert mgr.registry.has("custom.ev")

    def test_emit_delayed(self):
        from iios.events import get_event_manager
        mgr = get_event_manager()
        received = []
        mgr.on("delayed.ev", lambda e: received.append(e))
        mgr.emit_delayed("delayed.ev", delay=0.05, payload={"late": True})
        time.sleep(0.15)
        # The bus scheduler should have fired it by now
        assert len(received) >= 1

    def test_singleton(self):
        from iios.events import get_event_manager
        m1 = get_event_manager()
        m2 = get_event_manager()
        assert m1 is m2


# ══════════════════════════════════════════════════════════════════════════════
# 10. Queue Types
# ══════════════════════════════════════════════════════════════════════════════

class TestFifoQueue:
    def test_put_get(self):
        from iios.events import FifoQueue
        q = FifoQueue()
        msg = _make_message({"x": 1})
        q.put(msg)
        got = q.get()
        assert got.payload["x"] == 1

    def test_queue_full(self):
        from iios.events import FifoQueue, QueueFullError
        q = FifoQueue(max_size=1)
        q.put(_make_message())
        with pytest.raises(QueueFullError):
            q.put(_make_message(), timeout=0.01)

    def test_queue_empty(self):
        from iios.events import FifoQueue, QueueEmptyError
        q = FifoQueue()
        with pytest.raises(QueueEmptyError):
            q.get_nowait()

    def test_stats(self):
        from iios.events import FifoQueue
        q = FifoQueue()
        q.put(_make_message())
        q.get()
        s = q.stats()
        assert s["total_enqueued"] == 1
        assert s["total_dequeued"] == 1


class TestPriorityQueue:
    def test_priority_order(self):
        from iios.events.messaging.message import Message, MessageEnvelope, MessageType
        from iios.events import PriorityQueue
        q = PriorityQueue()

        def _msg(prio: int) -> Message:
            env = MessageEnvelope(message_type=MessageType.EVENT, source="t", priority=prio)
            return Message(payload={}, envelope=env)

        q.put(_msg(100))  # low priority
        q.put(_msg(1))    # high priority
        first = q.get()
        assert first.envelope.priority == 1

    def test_empty_raises(self):
        from iios.events import PriorityQueue, QueueEmptyError
        q = PriorityQueue()
        with pytest.raises(QueueEmptyError):
            q.get(timeout=0.01)


class TestDelayQueue:
    def test_not_available_immediately(self):
        from iios.events import DelayQueue, QueueEmptyError
        q = DelayQueue()
        q.put(_make_message(), delay=60.0)
        assert q.drain_due() == []

    def test_available_after_delay(self):
        from iios.events import DelayQueue
        q = DelayQueue()
        q.put(_make_message({"key": "val"}), delay=0.02)
        time.sleep(0.05)
        due = q.drain_due()
        assert len(due) == 1
        assert due[0].payload["key"] == "val"


class TestRetryQueue:
    def test_retry_schedule(self):
        from iios.events import RetryQueue
        rq = RetryQueue(max_retries=2, base_delay=0.01)
        msg = _make_message()
        result = rq.schedule_retry(msg)
        assert result is True
        assert rq.size() == 1

    def test_dlq_after_max_retries(self):
        from iios.events import RetryQueue
        rq = RetryQueue(max_retries=1, base_delay=0.01)
        msg = _make_message()
        msg.envelope.retry_count = 1  # already at max
        result = rq.schedule_retry(msg)
        assert result is False
        assert len(rq.dead_letters()) == 1

    def test_drain_due(self):
        from iios.events import RetryQueue
        rq = RetryQueue(max_retries=3, base_delay=0.01)
        msg = _make_message()
        rq.schedule_retry(msg)
        time.sleep(0.05)
        due = rq.drain_due()
        assert len(due) == 1


class TestDeadLetterQueue:
    def test_put_and_size(self):
        from iios.events import DeadLetterQueue
        dlq = DeadLetterQueue()
        dlq.put(_make_message(), reason="test failure")
        assert dlq.size() == 1

    def test_drain(self):
        from iios.events import DeadLetterQueue
        dlq = DeadLetterQueue()
        dlq.put(_make_message(), reason="err")
        items = dlq.drain()
        assert len(items) == 1
        assert dlq.size() == 0


class TestBatchQueue:
    def test_returns_batch_when_full(self):
        from iios.events import BatchQueue
        bq = BatchQueue(batch_size=3)
        bq.put(_make_message())
        bq.put(_make_message())
        batch = bq.put(_make_message())
        assert batch is not None
        assert len(batch) == 3

    def test_flush(self):
        from iios.events import BatchQueue
        bq = BatchQueue(batch_size=10)
        bq.put(_make_message())
        bq.put(_make_message())
        batch = bq.flush()
        assert len(batch) == 2
        assert bq.size() == 0

    def test_should_flush_by_interval(self):
        from iios.events import BatchQueue
        bq = BatchQueue(batch_size=100, flush_interval=0.02)
        bq.put(_make_message())
        time.sleep(0.05)
        assert bq.should_flush()


class TestStreamingQueue:
    def test_iterate(self):
        from iios.events import StreamingQueue
        sq = StreamingQueue()
        msgs = [_make_message({"i": i}) for i in range(5)]
        for m in msgs:
            sq.put(m)
        sq.stop()
        collected = list(sq)
        assert len(collected) == 5

    def test_stream_chunks(self):
        from iios.events import StreamingQueue
        sq = StreamingQueue(chunk_size=3)
        for i in range(7):
            sq.put(_make_message())
        sq.stop()
        chunks = list(sq.stream_chunks())
        assert sum(len(c) for c in chunks) == 7


# ══════════════════════════════════════════════════════════════════════════════
# 11. Message, Command, Query, Response
# ══════════════════════════════════════════════════════════════════════════════

class TestMessage:
    def test_message_id(self):
        msg = _make_message()
        assert len(msg.message_id) == 36

    def test_expiry(self):
        from iios.events.messaging.message import Message, MessageEnvelope, MessageType
        env = MessageEnvelope(message_type=MessageType.EVENT, source="t", ttl=0.001)
        msg = Message(payload={}, envelope=env)
        time.sleep(0.05)
        assert msg.is_expired

    def test_can_retry(self):
        msg = _make_message()
        msg.envelope.retry_count = 1
        msg.envelope.max_retries = 3
        assert msg.can_retry

    def test_max_retries_exceeded(self):
        msg = _make_message()
        msg.envelope.retry_count = 3
        msg.envelope.max_retries = 3
        assert not msg.can_retry


class TestCommandMsg:
    def test_command_id(self):
        cmd = _make_command("order.place", {"qty": 5})
        assert cmd.command_id
        assert cmd.payload["qty"] == 5

    def test_correlation_chain(self):
        cmd = _make_command()
        assert cmd.correlation_id


class TestQueryMsg:
    def test_query_id(self):
        qry = _make_query("portfolio.positions")
        assert qry.query_id

    def test_parameters(self):
        qry = _make_query(params={"account": "ACC001"})
        assert qry.parameters["account"] == "ACC001"


class TestResponseMsg:
    def test_ok_response(self):
        from iios.events.messaging.message import Response
        r = Response.ok("corr-123", {"balance": 1000})
        assert r.success
        assert r.payload["balance"] == 1000
        assert r.correlation_id == "corr-123"

    def test_err_response(self):
        from iios.events.messaging.message import Response
        r = Response.err("corr-456", "Insufficient funds", "ERR_FUNDS")
        assert not r.success
        assert r.error == "Insufficient funds"
        assert r.error_code == "ERR_FUNDS"


# ══════════════════════════════════════════════════════════════════════════════
# 12. CommandBus
# ══════════════════════════════════════════════════════════════════════════════

class TestCommandBus:
    def setup_method(self):
        from iios.events import reset_command_bus
        reset_command_bus()

    def test_dispatch(self):
        from iios.events import get_command_bus, Response
        bus = get_command_bus()
        bus.register("order.place", lambda c: Response.ok(c.command_id, {"status": "ok"}))
        cmd = _make_command("order.place", {"qty": 5})
        resp = bus.dispatch(cmd)
        assert resp is not None
        assert resp.success

    def test_not_found(self):
        from iios.events import get_command_bus, CommandNotFoundError
        bus = get_command_bus()
        with pytest.raises(CommandNotFoundError):
            bus.dispatch(_make_command("missing.cmd"))

    def test_no_duplicate_registration(self):
        from iios.events import get_command_bus, CommandHandlerError
        bus = get_command_bus()
        bus.register("dup.cmd", lambda c: None)
        with pytest.raises(CommandHandlerError):
            bus.register("dup.cmd", lambda c: None, allow_override=False)

    def test_allow_override(self):
        from iios.events import get_command_bus
        bus = get_command_bus()
        bus.register("override.cmd", lambda c: None)
        bus.register("override.cmd", lambda c: None, allow_override=True)  # no error

    def test_stats(self):
        from iios.events import get_command_bus
        bus = get_command_bus()
        bus.register("stat.cmd", lambda c: None)
        bus.dispatch(_make_command("stat.cmd"))
        assert bus.stats().dispatched >= 1

    def test_singleton(self):
        from iios.events import get_command_bus
        assert get_command_bus() is get_command_bus()


# ══════════════════════════════════════════════════════════════════════════════
# 13. QueryBus
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryBus:
    def setup_method(self):
        from iios.events import reset_query_bus
        reset_query_bus()

    def test_execute(self):
        from iios.events import get_query_bus, Response
        bus = get_query_bus()
        bus.register("portfolio.positions", lambda q: Response.ok(q.query_id, {"positions": []}))
        qry = _make_query("portfolio.positions")
        resp = bus.execute(qry)
        assert resp.success

    def test_no_handler(self):
        from iios.events import get_query_bus, QueryError
        bus = get_query_bus()
        with pytest.raises(QueryError):
            bus.execute(_make_query("missing.query"))

    def test_stats(self):
        from iios.events import get_query_bus, Response
        bus = get_query_bus()
        bus.register("stats.q", lambda q: Response.ok(q.query_id, {}))
        bus.execute(_make_query("stats.q"))
        assert bus.stats().executed >= 1

    def test_singleton(self):
        from iios.events import get_query_bus
        assert get_query_bus() is get_query_bus()


# ══════════════════════════════════════════════════════════════════════════════
# 14. ResponseBus
# ══════════════════════════════════════════════════════════════════════════════

class TestResponseBus:
    def setup_method(self):
        from iios.events import reset_response_bus
        reset_response_bus()

    def teardown_method(self):
        from iios.events import reset_response_bus
        reset_response_bus()

    def test_route_and_wait(self):
        from iios.events import get_response_bus
        from iios.events.messaging.message import Response
        bus = get_response_bus()
        corr = "test-corr-1"
        bus.register(corr)

        def _send():
            time.sleep(0.02)
            bus.route(Response.ok(corr, {"data": 42}))

        t = threading.Thread(target=_send, daemon=True)
        t.start()
        resp = bus.wait(corr, timeout=1.0)
        assert resp.success
        assert resp.payload["data"] == 42

    def test_timeout(self):
        from iios.events import get_response_bus
        from iios.events import QueryTimeoutError
        bus = get_response_bus()
        bus.register("no-reply")
        with pytest.raises(QueryTimeoutError):
            bus.wait("no-reply", timeout=0.05)

    def test_cancel(self):
        from iios.events import get_response_bus
        bus = get_response_bus()
        bus.register("cancel-me")
        assert bus.cancel("cancel-me")
        assert bus.pending_count() == 0


# ══════════════════════════════════════════════════════════════════════════════
# 15. MessageDispatcher
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageDispatcher:
    def test_dispatch_to_handler(self):
        from iios.events import MessageDispatcher
        disp = MessageDispatcher()
        received = []
        disp.register("my.type", lambda m: received.append(m))
        msg = _make_message({"type": "my.type"})
        disp.dispatch(msg)
        assert len(received) == 1

    def test_dispatch_no_handler(self):
        from iios.events import MessageDispatcher
        disp = MessageDispatcher()
        # Should not raise, just return None
        result = disp.dispatch(_make_message({"type": "unregistered"}))
        assert result is None

    def test_expired_message_dropped(self):
        from iios.events.messaging.message import Message, MessageEnvelope, MessageType
        from iios.events import MessageDispatcher
        env = MessageEnvelope(message_type=MessageType.EVENT, source="t", ttl=0.001)
        msg = Message(payload={"type": "x"}, envelope=env)
        time.sleep(0.05)
        disp = MessageDispatcher()
        received = []
        disp.register("x", lambda m: received.append(m))
        disp.dispatch(msg)
        assert len(received) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 16. MessageRouter
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageRouter:
    def test_route_by_destination(self):
        from iios.events import MessageRouter, MessageRoute
        from iios.events.messaging.message import Message, MessageEnvelope, MessageType
        router = MessageRouter()
        router.add_route(MessageRoute(name="r1", pattern="order.*", destination="order_q"))
        env = MessageEnvelope(message_type=MessageType.EVENT, source="t", destination="order.place")
        msg = Message(payload={}, envelope=env)
        dests = router.route(msg)
        assert "order_q" in dests

    def test_default_destination(self):
        from iios.events import MessageRouter
        router = MessageRouter(default_destination="default_q")
        msg = _make_message()
        dests = router.route(msg)
        assert "default_q" in dests

    def test_no_route_raises(self):
        from iios.events import MessageRouter, NoRouteError
        router = MessageRouter()
        with pytest.raises(NoRouteError):
            router.route_first(_make_message())


# ══════════════════════════════════════════════════════════════════════════════
# 17. MessageFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageFactory:
    def test_message(self):
        from iios.events import MessageFactory
        f = MessageFactory("order_engine")
        msg = f.message({"order_id": "ORD001"})
        assert msg.payload["order_id"] == "ORD001"

    def test_command(self):
        from iios.events import MessageFactory
        f = MessageFactory("execution")
        cmd = f.command("order.place", {"qty": 5})
        assert cmd.command_type == "order.place"
        assert cmd.payload["qty"] == 5

    def test_query(self):
        from iios.events import MessageFactory
        f = MessageFactory("ui")
        qry = f.query("portfolio.nav", {"account": "ACC001"})
        assert qry.query_type == "portfolio.nav"

    def test_response_ok(self):
        from iios.events import MessageFactory
        f = MessageFactory()
        r = f.response_ok("c-1", {"value": 99})
        assert r.success

    def test_response_err(self):
        from iios.events import MessageFactory
        f = MessageFactory()
        r = f.response_err("c-2", "Not found", "ERR_404")
        assert not r.success
        assert r.error_code == "ERR_404"


# ══════════════════════════════════════════════════════════════════════════════
# 18. MessageRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageRegistry:
    def setup_method(self):
        from iios.events import reset_message_registry
        reset_message_registry()

    def test_register_and_has(self):
        from iios.events import get_message_registry, MessageTypeDescriptor
        reg = get_message_registry()
        reg.register(MessageTypeDescriptor(message_type="order.place"))
        assert reg.has("order.place")

    def test_validate(self):
        from iios.events import get_message_registry, MessageTypeDescriptor
        reg = get_message_registry()
        reg.register(MessageTypeDescriptor(
            message_type="v.msg",
            validator=lambda p: "amount" in p,
        ))
        assert reg.validate("v.msg", {"amount": 100})
        assert not reg.validate("v.msg", {"other": 1})

    def test_singleton(self):
        from iios.events import get_message_registry
        r1 = get_message_registry()
        r2 = get_message_registry()
        assert r1 is r2


# ══════════════════════════════════════════════════════════════════════════════
# 19. CommandHandlerBase
# ══════════════════════════════════════════════════════════════════════════════

class TestCommandHandlerBase:
    def setup_method(self):
        from iios.events import reset_command_bus
        reset_command_bus()

    def test_register_and_dispatch(self):
        from iios.events import CommandHandlerBase, get_command_bus, Response

        class EchoHandler(CommandHandlerBase):
            command_type = "echo"

            def handle(self, command):
                return Response.ok(command.command_id, {"echo": command.payload})

        h = EchoHandler()
        h.register()
        bus = get_command_bus()
        cmd = _make_command("echo", {"msg": "hello"})
        resp = bus.dispatch(cmd)
        assert resp.success
        assert resp.payload["echo"]["msg"] == "hello"


# ══════════════════════════════════════════════════════════════════════════════
# 20. WorkflowEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowEngine:
    def setup_method(self):
        from iios.events import reset_workflow_engine
        reset_workflow_engine()

    def test_pipeline_success(self):
        from iios.events import WorkflowPipeline, WorkflowStatus
        pipeline = WorkflowPipeline("test_pipeline")
        pipeline.step("step1", lambda ctx: ctx.update({"s1": True}) or "step1_done")
        pipeline.step("step2", lambda ctx: "step2_done")
        state = pipeline.execute({"initial": True})
        assert state.status == WorkflowStatus.COMPLETED
        assert len(state.step_results) == 2
        assert all(r.success for r in state.step_results)

    def test_pipeline_failure_stops(self):
        from iios.events import WorkflowPipeline, WorkflowStatus
        pipeline = WorkflowPipeline("fail_pipeline")
        pipeline.step("s1", lambda ctx: None)
        pipeline.step("s2", lambda ctx: (_ for _ in ()).throw(ValueError("oops")))
        pipeline.step("s3", lambda ctx: None)
        state = pipeline.execute()
        assert state.status == WorkflowStatus.FAILED
        assert len(state.step_results) == 2  # s3 never ran

    def test_saga_compensation(self):
        from iios.events import SagaWorkflow, WorkflowStatus
        compensated = []
        saga = SagaWorkflow("test_saga")
        saga.step(
            "s1",
            lambda ctx: ctx.update({"s1": "done"}) or "ok",
            compensate=lambda ctx: compensated.append("s1_comp"),
        )
        saga.step(
            "s2",
            lambda ctx: (_ for _ in ()).throw(RuntimeError("step2 fails")),
            compensate=lambda ctx: compensated.append("s2_comp"),
        )
        state = saga.execute()
        assert state.status == WorkflowStatus.COMPENSATED
        assert "s1_comp" in compensated

    def test_engine_register_and_execute(self):
        from iios.events import get_workflow_engine, WorkflowPipeline, WorkflowStatus
        engine = get_workflow_engine()
        pipeline = WorkflowPipeline("engine_test")
        pipeline.step("only", lambda ctx: "done")
        engine.register(pipeline)
        state = engine.execute("engine_test")
        assert state.status == WorkflowStatus.COMPLETED

    def test_engine_unknown_workflow(self):
        from iios.events import get_workflow_engine, WorkflowError
        engine = get_workflow_engine()
        with pytest.raises(WorkflowError):
            engine.execute("does_not_exist")

    def test_engine_history(self):
        from iios.events import get_workflow_engine, WorkflowPipeline
        engine = get_workflow_engine()
        p = WorkflowPipeline("hist_wf")
        p.step("s", lambda ctx: None)
        engine.register(p)
        engine.execute("hist_wf")
        engine.execute("hist_wf")
        assert len(engine.history()) >= 2

    def test_workflow_timeout(self):
        from iios.events import WorkflowPipeline, WorkflowStatus
        # step1 sleeps past the deadline; step2's pre-check fires timeout
        p = WorkflowPipeline("slow_pipeline", timeout=0.05)
        p.step("s1", lambda ctx: time.sleep(0.1))  # exceeds 0.05s deadline
        p.step("s2", lambda ctx: None)              # deadline check fires here
        state = p.execute()
        assert state.status in (WorkflowStatus.TIMED_OUT, WorkflowStatus.FAILED)

    def test_step_retry(self):
        from iios.events import WorkflowPipeline, WorkflowStatus
        attempt = [0]

        def flaky(ctx):
            attempt[0] += 1
            if attempt[0] < 2:
                raise RuntimeError("transient")
            return "ok"

        p = WorkflowPipeline("retry_pipeline")
        p.step("flaky", flaky, max_retries=2, retry_delay=0.01)
        state = p.execute()
        assert state.status == WorkflowStatus.COMPLETED
        assert attempt[0] == 2

    def test_singleton(self):
        from iios.events import get_workflow_engine
        e1 = get_workflow_engine()
        e2 = get_workflow_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════════════════════
# 21. Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def setup_method(self):
        from iios.events import reset_event_bus
        reset_event_bus()

    def teardown_method(self):
        from iios.events import get_event_bus
        try:
            get_event_bus().stop()
        except Exception:
            pass
        from iios.events import reset_event_bus
        reset_event_bus()

    def test_concurrent_publish(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        counter = [0]
        lock = threading.Lock()
        bus.subscribe("concurrent.ev", lambda e: (
            lock.acquire(), counter.__setitem__(0, counter[0] + 1), lock.release()
        ))
        threads = [
            threading.Thread(target=lambda: bus.publish(_make_event("concurrent.ev")))
            for _ in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert counter[0] == 20

    def test_concurrent_command_bus(self):
        from iios.events import get_command_bus, reset_command_bus, Response
        reset_command_bus()
        bus = get_command_bus()
        results = []
        lock = threading.Lock()
        bus.register("parallel.cmd", lambda c: Response.ok(c.command_id, {}))

        def _dispatch():
            r = bus.dispatch(_make_command("parallel.cmd"))
            with lock:
                results.append(r)

        threads = [threading.Thread(target=_dispatch) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 10


# ══════════════════════════════════════════════════════════════════════════════
# 22. Reliability
# ══════════════════════════════════════════════════════════════════════════════

class TestReliability:
    def setup_method(self):
        from iios.events import reset_event_bus
        reset_event_bus()

    def teardown_method(self):
        from iios.events import get_event_bus
        try:
            get_event_bus().stop()
        except Exception:
            pass
        from iios.events import reset_event_bus
        reset_event_bus()

    def test_idempotent_publish(self):
        """Same event_id published twice → second publish raises IdempotencyError."""
        from iios.events.event_bus import EventBus
        from iios.events import IdempotencyError
        bus = EventBus(detect_duplicates=True)
        received = []
        bus.subscribe("idem.ev", lambda e: received.append(e))
        e = _make_event("idem.ev")
        bus.publish(e)
        with pytest.raises(IdempotencyError):
            bus.publish(e)  # duplicate
        assert len(received) == 1
        bus.stop()

    def test_handler_error_goes_to_dlq(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        bus.subscribe("dlq.check", lambda e: (_ for _ in ()).throw(RuntimeError("always fails")))
        bus.publish(_make_event("dlq.check"))
        assert len(bus.dead_letter_queue()) >= 1

    def test_clear_dlq(self):
        from iios.events import get_event_bus
        bus = get_event_bus()
        bus.subscribe("dlq2.check", lambda e: (_ for _ in ()).throw(RuntimeError("fail")))
        bus.publish(_make_event("dlq2.check"))
        bus.clear_dlq()
        assert len(bus.dead_letter_queue()) == 0
