"""tests/unit/investment/decision/core/test_events.py
Tests for DecisionEvent, EventDispatcher, EventHistory.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.decision.core.decision_constants import (
    DecisionEventType,
)
from iios.investment.decision.core.decision_events import (
    DecisionEvent,
    EventDispatcher,
    EventHistory,
    make_event,
)


# ===========================================================================
# make_event + DecisionEvent
# ===========================================================================

class TestDecisionEvent:
    def test_make_event_fields(self):
        ev = make_event(
            event_type=DecisionEventType.CREATED,
            decision_id="D1",
            payload={"score": 80},
            source="test",
        )
        assert ev.event_type   == DecisionEventType.CREATED
        assert ev.decision_id  == "D1"
        assert ev.payload["score"] == 80
        assert ev.source       == "test"
        assert ev.event_id

    def test_make_event_defaults(self):
        ev = make_event(DecisionEventType.SCORED, "D2")
        assert ev.payload == {}
        assert ev.source  == "framework"

    def test_to_dict(self):
        ev = make_event(DecisionEventType.PUBLISHED, "D3")
        d  = ev.to_dict()
        assert "event_id"    in d
        assert "event_type"  in d
        assert "occurred_at" in d


# ===========================================================================
# EventDispatcher
# ===========================================================================

class TestEventDispatcher:
    def test_subscribe_and_receive(self):
        disp   = EventDispatcher()
        received = []
        disp.subscribe(lambda e: received.append(e))
        ev = make_event(DecisionEventType.CREATED, "D1")
        disp.dispatch(ev)
        assert len(received) == 1
        assert received[0] is ev

    def test_unsubscribe_stops_delivery(self):
        disp     = EventDispatcher()
        received = []
        hid      = disp.subscribe(lambda e: received.append(e))
        disp.dispatch(make_event(DecisionEventType.CREATED, "D1"))
        disp.unsubscribe(hid)
        disp.dispatch(make_event(DecisionEventType.SCORED, "D1"))
        assert len(received) == 1

    def test_type_filter_receives_only_matching(self):
        disp     = EventDispatcher()
        received = []
        disp.subscribe(lambda e: received.append(e), event_type=DecisionEventType.APPROVED)
        disp.dispatch(make_event(DecisionEventType.CREATED, "D1"))
        disp.dispatch(make_event(DecisionEventType.APPROVED, "D1"))
        assert len(received) == 1
        assert received[0].event_type == DecisionEventType.APPROVED

    def test_multiple_subscribers(self):
        disp = EventDispatcher()
        a, b = [], []
        disp.subscribe(lambda e: a.append(e))
        disp.subscribe(lambda e: b.append(e))
        disp.dispatch(make_event(DecisionEventType.PUBLISHED, "D2"))
        assert len(a) == 1
        assert len(b) == 1

    def test_bad_subscriber_does_not_crash(self):
        disp = EventDispatcher()
        disp.subscribe(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        ev = make_event(DecisionEventType.CREATED, "D3")
        disp.dispatch(ev)  # should NOT raise

    def test_dispatch_simple(self):
        disp     = EventDispatcher()
        received = []
        disp.subscribe(lambda e: received.append(e))
        disp.dispatch_simple(DecisionEventType.SCORED, "D4", {"score": 77})
        assert len(received) == 1
        assert received[0].payload["score"] == 77

    def test_history_stores_events(self):
        disp = EventDispatcher()
        disp.dispatch(make_event(DecisionEventType.CREATED, "D5"))
        assert disp.count() == 1

    def test_history_filter_by_decision(self):
        disp = EventDispatcher()
        disp.dispatch(make_event(DecisionEventType.CREATED, "D5"))
        disp.dispatch(make_event(DecisionEventType.CREATED, "D6"))
        h = disp.history(decision_id="D5")
        assert all(e.decision_id == "D5" for e in h)

    def test_history_filter_by_type(self):
        disp = EventDispatcher()
        disp.dispatch(make_event(DecisionEventType.CREATED,  "D7"))
        disp.dispatch(make_event(DecisionEventType.APPROVED, "D7"))
        h = disp.history(event_type=DecisionEventType.APPROVED)
        assert all(e.event_type == DecisionEventType.APPROVED for e in h)

    def test_max_history_ring(self):
        disp = EventDispatcher(max_history=3)
        for i in range(5):
            disp.dispatch(make_event(DecisionEventType.CREATED, f"D{i}"))
        assert disp.count() == 3

    def test_thread_safety(self):
        """Multiple threads dispatching simultaneously should not corrupt."""
        disp  = EventDispatcher()
        lock  = threading.Lock()
        count = [0]

        def handler(e):
            with lock:
                count[0] += 1

        disp.subscribe(handler)

        threads = [
            threading.Thread(
                target=lambda: disp.dispatch(make_event(DecisionEventType.CREATED, "T"))
            )
            for _ in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert count[0] == 50


# ===========================================================================
# EventHistory
# ===========================================================================

class TestEventHistory:
    def test_record_and_for_decision(self):
        hist = EventHistory()
        ev   = make_event(DecisionEventType.CREATED, "D1")
        hist.record(ev)
        assert ev in hist.for_decision("D1")

    def test_by_type(self):
        hist = EventHistory()
        hist.record(make_event(DecisionEventType.CREATED,  "D1"))
        hist.record(make_event(DecisionEventType.APPROVED, "D1"))
        typed = hist.by_type(DecisionEventType.APPROVED)
        assert len(typed) == 1

    def test_recent(self):
        hist = EventHistory()
        for i in range(10):
            hist.record(make_event(DecisionEventType.SCORED, f"D{i}"))
        assert len(hist.recent(5)) == 5

    def test_count(self):
        hist = EventHistory()
        hist.record(make_event(DecisionEventType.PUBLISHED, "D1"))
        assert hist.count() == 1

    def test_max_size_ring(self):
        hist = EventHistory(max_size=3)
        for i in range(5):
            hist.record(make_event(DecisionEventType.CREATED, f"D{i}"))
        assert hist.count() == 3
