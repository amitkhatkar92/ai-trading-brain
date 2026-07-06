"""
tests/unit/infrastructure/test_event_bus.py
===========================================
Tests for the iios.infrastructure.events subpackage.
"""

from __future__ import annotations

import time
import threading
import pytest

from iios.infrastructure.events import (
    EventBus, get_event_bus, reset_event_bus,
    EventQueue, DeadLetterQueue,
    EventRouter,
    EventPublisher,
    EventDispatcher,
    Subscriber, SubscriberDescriptor,
)
from iios.infrastructure.infrastructure_constants import EventPriority
from iios.infrastructure.infrastructure_models import EventEnvelope
from iios.infrastructure.infrastructure_exceptions import EventBusError


# ---------------------------------------------------------------------------
# EventQueue
# ---------------------------------------------------------------------------

class TestEventQueue:
    def test_basic_put_get(self):
        q = EventQueue(maxsize=10)
        env = EventEnvelope(event_type="test", payload=1, priority=50)
        q.put(env)
        out = q.get(block=False)
        assert out.event_type == "test"

    def test_priority_ordering(self):
        q = EventQueue(maxsize=10)
        low = EventEnvelope(event_type="low", payload=None, priority=EventPriority.LOW.value)
        high = EventEnvelope(event_type="high", payload=None, priority=EventPriority.HIGH.value)
        q.put(low)
        q.put(high)
        first = q.get(block=False)
        # Higher priority should come first (EventEnvelope inverts for min-heap)
        assert first.priority >= q.get(block=False).priority

    def test_stats(self):
        q = EventQueue(maxsize=10)
        env = EventEnvelope(event_type="x", payload=None, priority=50)
        q.put(env)
        q.get(block=False)
        assert q.total_enqueued == 1
        assert q.total_dequeued == 1


# ---------------------------------------------------------------------------
# DeadLetterQueue
# ---------------------------------------------------------------------------

class TestDeadLetterQueue:
    def test_add_and_all(self):
        dlq = DeadLetterQueue()
        env = EventEnvelope(event_type="fail", payload=None, priority=50)
        dlq.add(env, "boom", subscriber="handler")
        assert len(dlq.all()) == 1
        assert dlq.all()[0].failure_reason == "boom"

    def test_drain(self):
        dlq = DeadLetterQueue()
        for i in range(5):
            env = EventEnvelope(event_type=f"e{i}", payload=None, priority=50)
            dlq.add(env, "err")
        drained = dlq.drain(3)
        assert len(drained) == 3
        assert dlq.size == 2

    def test_capacity_cap(self):
        dlq = DeadLetterQueue(maxsize=3)
        for i in range(10):
            env = EventEnvelope(event_type=f"e{i}", payload=None, priority=50)
            dlq.add(env, "err")
        assert dlq.size == 3  # capped at maxsize


# ---------------------------------------------------------------------------
# EventRouter
# ---------------------------------------------------------------------------

class TestEventRouter:
    def _make_descriptor(self, event_type: str) -> SubscriberDescriptor:
        return SubscriberDescriptor(event_type=event_type, handler=lambda e: None)

    def test_exact_match(self):
        router = EventRouter()
        d = self._make_descriptor("market.price")
        router.add(d)
        env = EventEnvelope(event_type="market.price", payload=None, priority=50)
        matches = router.route(env)
        assert d in matches

    def test_wildcard_match(self):
        router = EventRouter()
        d = self._make_descriptor("*")
        router.add(d)
        env = EventEnvelope(event_type="anything", payload=None, priority=50)
        assert d in router.route(env)

    def test_prefix_glob_match(self):
        router = EventRouter()
        d = self._make_descriptor("market.*")
        router.add(d)
        env = EventEnvelope(event_type="market.price", payload=None, priority=50)
        assert d in router.route(env)
        env2 = EventEnvelope(event_type="risk.breach", payload=None, priority=50)
        assert d not in router.route(env2)

    def test_no_match(self):
        router = EventRouter()
        d = self._make_descriptor("risk.breach")
        router.add(d)
        env = EventEnvelope(event_type="market.price", payload=None, priority=50)
        assert d not in router.route(env)

    def test_remove(self):
        router = EventRouter()
        d = self._make_descriptor("risk.breach")
        router.add(d)
        router.remove(d.subscription_id)
        env = EventEnvelope(event_type="risk.breach", payload=None, priority=50)
        assert router.route(env) == []

    def test_disabled_subscriber_excluded(self):
        router = EventRouter()
        d = self._make_descriptor("risk.breach")
        d.enabled = False
        router.add(d)
        env = EventEnvelope(event_type="risk.breach", payload=None, priority=50)
        assert router.route(env) == []


# ---------------------------------------------------------------------------
# EventDispatcher
# ---------------------------------------------------------------------------

class TestEventDispatcher:
    def test_successful_dispatch(self):
        called = []
        desc = SubscriberDescriptor(
            event_type="x", handler=lambda e: called.append(e.payload)
        )
        dispatcher = EventDispatcher()
        env = EventEnvelope(event_type="x", payload=42, priority=50)
        results = dispatcher.dispatch(env, [desc])
        assert results[desc.subscription_id] is True
        assert called == [42]

    def test_failed_dispatch_goes_to_dlq(self):
        def bad_handler(e):
            raise ValueError("bad")

        desc = SubscriberDescriptor(event_type="x", handler=bad_handler, max_retries=1)
        dlq = DeadLetterQueue()
        dispatcher = EventDispatcher(dead_letter=dlq, backoff_base=0.0)
        env = EventEnvelope(event_type="x", payload=None, priority=50)
        results = dispatcher.dispatch(env, [desc])
        assert results[desc.subscription_id] is False
        assert dlq.size == 1

    def test_priority_order_dispatch(self):
        order = []
        d1 = SubscriberDescriptor(event_type="*", handler=lambda e: order.append("low"), priority=10)
        d2 = SubscriberDescriptor(event_type="*", handler=lambda e: order.append("high"), priority=100)
        dispatcher = EventDispatcher()
        env = EventEnvelope(event_type="x", payload=None, priority=50)
        dispatcher.dispatch(env, [d1, d2])
        assert order == ["high", "low"]


# ---------------------------------------------------------------------------
# EventPublisher
# ---------------------------------------------------------------------------

class TestEventPublisher:
    def test_publish_enqueues(self):
        q = EventQueue(maxsize=10)
        pub = EventPublisher(q, source="test")
        pub.publish("market.price", {"price": 100})
        assert q.qsize == 1
        assert pub.published_count == 1

    def test_publish_high(self):
        q = EventQueue(maxsize=10)
        pub = EventPublisher(q, source="test")
        env = pub.publish_high("urgent", payload=None)
        assert env.priority == EventPriority.HIGH.value

    def test_correlation_id_sticky(self):
        q = EventQueue(maxsize=10)
        pub = EventPublisher(q).set_correlation_id("trace-123")
        env = pub.publish("x", None)
        assert env.correlation_id == "trace-123"


# ---------------------------------------------------------------------------
# EventBus — integrated
# ---------------------------------------------------------------------------

class TestEventBus:
    def setup_method(self):
        reset_event_bus()

    def teardown_method(self):
        reset_event_bus()

    def test_start_stop(self):
        bus = EventBus()
        bus.start()
        assert bus.is_running
        bus.stop()
        assert not bus.is_running

    def test_subscribe_and_publish_sync(self):
        bus = EventBus()
        received = []
        bus.subscribe("price", lambda e: received.append(e.payload))
        bus.publish_sync("price", {"symbol": "RELIANCE"})
        assert len(received) == 1
        assert received[0]["symbol"] == "RELIANCE"

    def test_async_dispatch(self):
        bus = EventBus()
        bus.start()
        received = []
        event = threading.Event()

        def handler(e):
            received.append(e.payload)
            event.set()

        bus.subscribe("order.filled", handler)
        bus.publish("order.filled", {"qty": 10})

        assert event.wait(timeout=3.0), "Handler was not called within 3 seconds"
        assert received[0]["qty"] == 10
        bus.stop()

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        sub_id = bus.subscribe("x", lambda e: received.append(1))
        bus.unsubscribe(sub_id)
        bus.publish_sync("x", None)
        assert received == []

    def test_wildcard_subscriber(self):
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        bus.publish_sync("a", None)
        bus.publish_sync("b", None)
        assert set(received) == {"a", "b"}

    def test_global_singleton(self):
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2

    def test_stats(self):
        bus = EventBus()
        bus.publish_sync("x", None)
        stats = bus.stats()
        assert "queue_size" in stats

    def test_dead_letter_on_failure(self):
        bus = EventBus()

        def bad(e):
            raise RuntimeError("fail")

        bus.subscribe("boom", bad)
        bus.publish_sync("boom", None)
        assert len(bus.dead_letters()) == 1


class TestSubscriber:
    def test_class_subscriber(self):
        received = []

        class PriceSubscriber(Subscriber):
            event_type = "market.price"

            def handle(self, envelope):
                received.append(envelope.payload)

        bus = EventBus()
        sub = PriceSubscriber()
        bus.subscribe_class(sub)
        bus.publish_sync("market.price", {"price": 2000})
        assert received == [{"price": 2000}]
