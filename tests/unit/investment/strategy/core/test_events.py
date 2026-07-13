"""tests/unit/investment/strategy/core/test_events.py
Tests for StrategyEvent, EventHistory, and EventDispatcher.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.strategy.core import (
    EventDispatcher, EventHistory, StrategyEvent, StrategyEventType,
)


# ── StrategyEvent ─────────────────────────────────────────────────────────────

class TestStrategyEvent:
    def test_event_id_prefixed(self):
        ev = StrategyEvent(
            event_type=StrategyEventType.STRATEGY_REGISTERED,
            strategy_id="s1",
        )
        assert ev.event_id.startswith("sev-")

    def test_to_dict_keys(self):
        ev = StrategyEvent(
            event_type=StrategyEventType.SIGNAL_GENERATED,
            strategy_id="s1",
        )
        d = ev.to_dict()
        assert all(k in d for k in [
            "event_id", "event_type", "strategy_id",
            "session_id", "severity", "payload", "occurred_at",
        ])

    def test_timezone_aware(self):
        ev = StrategyEvent(
            event_type=StrategyEventType.ERROR, strategy_id="x"
        )
        assert ev.occurred_at.tzinfo is not None


# ── EventHistory ──────────────────────────────────────────────────────────────

class TestEventHistory:
    def _event(self, sid: str, et=StrategyEventType.STRATEGY_READY) -> StrategyEvent:
        return StrategyEvent(event_type=et, strategy_id=sid)

    def test_record_and_for_strategy(self):
        h = EventHistory()
        ev = self._event("A")
        h.record(ev)
        events = h.for_strategy("A")
        assert len(events) == 1
        assert events[0] is ev

    def test_for_strategy_empty_when_none(self):
        h = EventHistory()
        assert h.for_strategy("unknown") == []

    def test_recent(self):
        h = EventHistory()
        for i in range(10):
            h.record(self._event(f"s{i}"))
        assert len(h.recent(5)) == 5

    def test_filter(self):
        h = EventHistory()
        h.record(self._event("A", StrategyEventType.STRATEGY_READY))
        h.record(self._event("A", StrategyEventType.ERROR))
        errors = h.filter(lambda e: e.event_type == StrategyEventType.ERROR)
        assert len(errors) == 1

    def test_total_count(self):
        h = EventHistory()
        for _ in range(5):
            h.record(self._event("A"))
        assert h.total_count() == 5

    def test_strategy_count(self):
        h = EventHistory()
        h.record(self._event("A"))
        h.record(self._event("A"))
        h.record(self._event("B"))
        assert h.strategy_count("A") == 2
        assert h.strategy_count("B") == 1

    def test_clear_by_strategy(self):
        h = EventHistory()
        h.record(self._event("A"))
        h.record(self._event("B"))
        h.clear("A")
        assert h.strategy_count("A") == 0
        assert h.strategy_count("B") == 1

    def test_clear_all(self):
        h = EventHistory()
        h.record(self._event("A"))
        h.clear()
        assert h.total_count() == 0

    def test_filter_by_event_type(self):
        h = EventHistory()
        h.record(self._event("A", StrategyEventType.SIGNAL_GENERATED))
        h.record(self._event("A", StrategyEventType.SIGNAL_REJECTED))
        signals = h.for_strategy(
            "A", event_type=StrategyEventType.SIGNAL_GENERATED
        )
        assert len(signals) == 1

    def test_max_per_strategy_ring_buffer(self):
        h = EventHistory(max_per_strategy=3)
        for _ in range(10):
            h.record(self._event("A"))
        assert h.strategy_count("A") == 3

    def test_max_global_ring_buffer(self):
        h = EventHistory(max_global=5)
        for i in range(10):
            h.record(self._event(f"s{i}"))
        assert h.total_count() == 5


# ── EventDispatcher ───────────────────────────────────────────────────────────

class TestEventDispatcher:
    def test_emit_and_subscribe(self):
        d = EventDispatcher()
        received = []
        d.subscribe(received.append)
        d.emit(StrategyEventType.STRATEGY_READY, strategy_id="s1")
        assert len(received) == 1
        assert received[0].strategy_id == "s1"

    def test_subscribe_specific_event_type(self):
        d = EventDispatcher()
        received = []
        d.subscribe(
            received.append,
            event_types=[StrategyEventType.ERROR],
        )
        d.emit(StrategyEventType.STRATEGY_READY, strategy_id="s")
        d.emit(StrategyEventType.ERROR, strategy_id="s")
        assert len(received) == 1
        assert received[0].event_type == StrategyEventType.ERROR

    def test_unsubscribe_global(self):
        d = EventDispatcher()
        received = []
        d.subscribe(received.append)
        d.unsubscribe(received.append)
        d.emit(StrategyEventType.STRATEGY_READY, strategy_id="s")
        assert len(received) == 0

    def test_unsubscribe_specific(self):
        d = EventDispatcher()
        received = []
        d.subscribe(received.append, [StrategyEventType.ERROR])
        d.unsubscribe(received.append, [StrategyEventType.ERROR])
        d.emit(StrategyEventType.ERROR, strategy_id="s")
        assert len(received) == 0

    def test_handler_exception_does_not_propagate(self):
        d = EventDispatcher()

        def bad_handler(ev):
            raise RuntimeError("boom")

        d.subscribe(bad_handler)
        # Should not raise
        d.emit(StrategyEventType.STRATEGY_READY, strategy_id="s")

    def test_emit_records_to_history(self):
        d = EventDispatcher()
        d.emit(StrategyEventType.STRATEGY_READY, strategy_id="s")
        assert d.history.total_count() == 1

    def test_publish_calls_both_specific_and_global(self):
        d = EventDispatcher()
        specific = []
        global_ = []
        d.subscribe(specific.append, [StrategyEventType.ERROR])
        d.subscribe(global_.append)
        d.emit(StrategyEventType.ERROR, strategy_id="s")
        assert len(specific) == 1
        assert len(global_) == 1

    def test_concurrent_emit(self):
        d = EventDispatcher()
        results = []
        d.subscribe(results.append)
        threads = [
            threading.Thread(
                target=d.emit,
                args=(StrategyEventType.STRATEGY_READY, f"s{i}"),
            )
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 20
