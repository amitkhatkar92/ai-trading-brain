"""tests/unit/investment/portfolio/core/test_events.py

Tests for portfolio events, event dispatcher, and event history.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.core.event_dispatcher import EventDispatcher
from iios.investment.portfolio.core.event_history import EventHistory, EventRecord
from iios.investment.portfolio.core.portfolio_events import (
    AllocationChangedEvent,
    EventPriority,
    FrameworkStartedEvent,
    PerformanceAlertEvent,
    PortfolioArchivedEvent,
    PortfolioEvent,
    PortfolioEventType,
    PortfolioFailedEvent,
    PortfolioInitializedEvent,
    PortfolioRegisteredEvent,
    RiskAlertEvent,
)


def _make_event(
    event_type:   PortfolioEventType = PortfolioEventType.PORTFOLIO_UPDATED,
    portfolio_id: str = "P1",
) -> PortfolioEvent:
    return PortfolioEvent(event_type=event_type, portfolio_id=portfolio_id)


class TestPortfolioEventTypes:
    def test_is_alert(self):
        assert PortfolioEventType.RISK_ALERT.is_alert
        assert not PortfolioEventType.PORTFOLIO_ACTIVATED.is_alert

    def test_is_lifecycle(self):
        assert PortfolioEventType.PORTFOLIO_INITIALIZED.is_lifecycle
        assert not PortfolioEventType.PORTFOLIO_REBALANCED.is_lifecycle

    def test_risk_alert_priority(self):
        ev = RiskAlertEvent(portfolio_id="P1", alert_type="drawdown",
                            threshold=0.20, current_value=0.22)
        assert ev.priority == EventPriority.CRITICAL

    def test_failed_event_priority(self):
        ev = PortfolioFailedEvent(portfolio_id="P1", error="crash")
        assert ev.priority == EventPriority.CRITICAL

    def test_event_to_dict(self):
        ev = _make_event()
        d = ev.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "portfolio_id" in d

    def test_allocation_changed_event(self):
        ev = AllocationChangedEvent(
            portfolio_id = "P1",
            symbol       = "INFY",
            old_weight   = 0.05,
            new_weight   = 0.10,
        )
        assert ev.event_type == PortfolioEventType.ALLOCATION_CHANGED
        assert ev.symbol == "INFY"

    def test_framework_started_event(self):
        ev = FrameworkStartedEvent(framework_version="1.0.0")
        assert ev.portfolio_id == "framework"

    def test_performance_alert_event(self):
        ev = PerformanceAlertEvent(
            portfolio_id  = "P1",
            metric        = "sharpe_ratio",
            threshold     = 0.5,
            current_value = 0.2,
        )
        d = ev.to_dict()
        assert d["event_type"] == "performance_alert"

    def test_event_is_frozen(self):
        ev = _make_event()
        with pytest.raises((AttributeError, TypeError)):
            ev.portfolio_id = "changed"  # type: ignore


class TestEventHistory:
    def test_record_and_count(self):
        h = EventHistory()
        ev = _make_event()
        h.record(ev)
        assert h.count() == 1

    def test_recent(self):
        h = EventHistory()
        for i in range(10):
            h.record(_make_event(portfolio_id=f"P{i}"))
        assert len(h.recent(5)) == 5

    def test_for_portfolio(self):
        h = EventHistory()
        h.record(_make_event(portfolio_id="A"))
        h.record(_make_event(portfolio_id="B"))
        h.record(_make_event(portfolio_id="A"))
        recs = h.for_portfolio("A")
        assert len(recs) == 2

    def test_by_type(self):
        h = EventHistory()
        h.record(_make_event(PortfolioEventType.PORTFOLIO_REBALANCED))
        h.record(_make_event(PortfolioEventType.PORTFOLIO_UPDATED))
        recs = h.by_type(PortfolioEventType.PORTFOLIO_REBALANCED)
        assert len(recs) == 1

    def test_since(self):
        import time
        h = EventHistory()
        t0 = time.time()
        h.record(_make_event())
        recs = h.since(t0 - 1.0)
        assert len(recs) == 1

    def test_max_size_rolling(self):
        h = EventHistory(max_size=3)
        for i in range(5):
            h.record(_make_event(portfolio_id=f"P{i}"))
        assert h.count() == 3

    def test_failure_rate(self):
        h = EventHistory()
        ev = _make_event()
        h.record(ev, failed_count=1)
        h.record(ev, failed_count=0)
        assert h.failure_rate() == pytest.approx(0.5)

    def test_reset(self):
        h = EventHistory()
        h.record(_make_event())
        h.reset()
        assert h.count() == 0

    def test_latest_for_portfolio(self):
        h = EventHistory()
        h.record(_make_event(portfolio_id="X"))
        h.record(_make_event(portfolio_id="Y"))
        latest = h.latest_for_portfolio("X")
        assert latest is not None
        assert latest.portfolio_id == "X"


class TestEventDispatcher:
    def test_subscribe_and_dispatch(self):
        received = []
        d = EventDispatcher()
        d.subscribe(lambda e: received.append(e))
        d.dispatch(_make_event())
        assert len(received) == 1

    def test_filter_by_type(self):
        received = []
        d = EventDispatcher()
        d.subscribe(
            lambda e: received.append(e),
            event_types={PortfolioEventType.PORTFOLIO_REBALANCED},
        )
        d.dispatch(_make_event(PortfolioEventType.PORTFOLIO_UPDATED))
        d.dispatch(_make_event(PortfolioEventType.PORTFOLIO_REBALANCED))
        assert len(received) == 1

    def test_filter_by_portfolio(self):
        received = []
        d = EventDispatcher()
        d.subscribe(lambda e: received.append(e), portfolio_ids={"P1"})
        d.dispatch(_make_event(portfolio_id="P1"))
        d.dispatch(_make_event(portfolio_id="P2"))
        assert len(received) == 1

    def test_unsubscribe(self):
        received = []
        d = EventDispatcher()
        hid = d.subscribe(lambda e: received.append(e))
        d.unsubscribe(hid)
        d.dispatch(_make_event())
        assert len(received) == 0

    def test_priority_ordering(self):
        order = []
        d = EventDispatcher()
        d.subscribe(lambda e: order.append("normal"),  priority=EventPriority.NORMAL)
        d.subscribe(lambda e: order.append("critical"), priority=EventPriority.CRITICAL)
        d.subscribe(lambda e: order.append("low"),      priority=EventPriority.LOW)
        d.dispatch(_make_event())
        assert order == ["critical", "normal", "low"]

    def test_handler_exception_isolated(self):
        received = []
        d = EventDispatcher()
        d.subscribe(lambda e: (_ for _ in ()).throw(ValueError("boom")))
        d.subscribe(lambda e: received.append(e))
        count = d.dispatch(_make_event())
        assert count >= 1  # second handler still called
        assert len(received) == 1

    def test_dispatch_many(self):
        received = []
        d = EventDispatcher()
        d.subscribe(lambda e: received.append(e))
        d.dispatch_many([_make_event(), _make_event(), _make_event()])
        assert len(received) == 3

    def test_subscription_count(self):
        d = EventDispatcher()
        d.subscribe(lambda e: None)
        d.subscribe(lambda e: None)
        assert d.subscription_count() == 2

    def test_history_records_dispatch(self):
        d = EventDispatcher()
        d.dispatch(_make_event())
        assert d.history.count() == 1

    def test_unsubscribe_returns_false_on_unknown(self):
        d = EventDispatcher()
        assert not d.unsubscribe("nonexistent-id")
