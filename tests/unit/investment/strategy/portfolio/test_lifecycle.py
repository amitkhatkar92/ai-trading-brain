"""tests/unit/investment/strategy/portfolio/test_lifecycle.py
Tests for PortfolioEvents, PortfolioLifecycle, and PortfolioMonitor.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import StrategyAllocation
from iios.investment.strategy.portfolio.portfolio_events import (
    PortfolioEvent, PortfolioEventType, PortfolioEventBus
)
from iios.investment.strategy.portfolio.portfolio_lifecycle import PortfolioLifecycle
from iios.investment.strategy.portfolio.portfolio_monitor import (
    PortfolioMonitor, AlertSeverity
)
from iios.investment.strategy.portfolio.portfolio_registry import PortfolioRegistry
from iios.investment.strategy.portfolio.construction_constraints import DEFAULT_CONSTRAINTS


def _make_portfolio(pid: str = "p1") -> StrategyPortfolio:
    return StrategyPortfolio(pid, "Test", PortfolioType.EQUAL_WEIGHT)


def _add_active_allocations(portfolio: StrategyPortfolio, n: int = 3, weight: float = None) -> None:
    w = weight if weight is not None else (1.0 / n)
    for i in range(n):
        portfolio.add_strategy(StrategyAllocation(f"s{i}", f"S{i}", w, w))


# ── PortfolioEventBus ─────────────────────────────────────────────────────────

class TestPortfolioEventBus:
    def test_subscribe_and_emit(self):
        bus = PortfolioEventBus()
        received: List[PortfolioEvent] = []
        bus.subscribe(received.append)
        event = PortfolioEvent(
            event_id="e1",
            event_type=PortfolioEventType.CREATED,
            portfolio_id="p1",
            payload={"reason": "test"},
        )
        bus.emit(event)
        assert len(received) == 1
        assert received[0].event_type == PortfolioEventType.CREATED

    def test_typed_subscription(self):
        bus = PortfolioEventBus()
        received: List[PortfolioEvent] = []
        bus.subscribe(received.append, event_type=PortfolioEventType.ARCHIVED)

        bus.emit(PortfolioEvent("e1", PortfolioEventType.CREATED, "p1", {}))
        bus.emit(PortfolioEvent("e2", PortfolioEventType.ARCHIVED, "p1", {}))
        assert len(received) == 1
        assert received[0].event_type == PortfolioEventType.ARCHIVED

    def test_unsubscribe_global(self):
        bus = PortfolioEventBus()
        received: List[PortfolioEvent] = []
        bus.subscribe(received.append)
        bus.unsubscribe(received.append)
        bus.emit(PortfolioEvent("e1", PortfolioEventType.CREATED, "p1", {}))
        assert len(received) == 0

    def test_handler_exception_does_not_propagate(self):
        bus = PortfolioEventBus()
        def bad_handler(event):
            raise RuntimeError("fail")
        bus.subscribe(bad_handler)
        bus.emit(PortfolioEvent("e1", PortfolioEventType.CREATED, "p1", {}))  # should not raise


# ── PortfolioLifecycle ────────────────────────────────────────────────────────

class TestPortfolioLifecycle:
    def test_valid_transition_created_to_optimized(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        ok = lc.transition(p, PortfolioState.OPTIMIZED, reason="test")
        assert ok is True
        assert p.state == PortfolioState.OPTIMIZED

    def test_invalid_transition_returns_false(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        ok = lc.transition(p, PortfolioState.ACTIVE, reason="test")
        assert ok is False
        assert p.state == PortfolioState.CREATED

    def test_full_lifecycle(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        assert lc.transition(p, PortfolioState.OPTIMIZED)
        assert lc.approve(p)
        assert lc.activate(p)
        assert p.state == PortfolioState.ACTIVE

    def test_archive_from_active(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        lc.transition(p, PortfolioState.OPTIMIZED)
        lc.approve(p)
        lc.activate(p)
        ok = lc.archive(p, reason="decommission")
        assert ok is True
        assert p.state == PortfolioState.ARCHIVED

    def test_cannot_transition_from_archived(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        p.state = PortfolioState.ARCHIVED
        ok = lc.transition(p, PortfolioState.ACTIVE)
        assert ok is False

    def test_events_emitted_on_transition(self):
        bus = PortfolioEventBus()
        events: List[PortfolioEvent] = []
        bus.subscribe(events.append)
        lc = PortfolioLifecycle(event_bus=bus)
        p  = _make_portfolio()
        lc.transition(p, PortfolioState.OPTIMIZED)
        assert len(events) >= 1
        assert events[0].event_type == PortfolioEventType.OPTIMIZED

    def test_pause_and_resume(self):
        p  = _make_portfolio()
        lc = PortfolioLifecycle()
        lc.transition(p, PortfolioState.OPTIMIZED)
        lc.approve(p)
        lc.activate(p)
        lc.pause(p)
        assert p.state == PortfolioState.PAUSED
        ok = lc.activate(p)
        assert ok is True


# ── PortfolioMonitor ──────────────────────────────────────────────────────────

class TestPortfolioMonitor:
    def _setup(self):
        reg = PortfolioRegistry()
        mon = PortfolioMonitor(reg)
        return reg, mon

    def test_no_alerts_for_healthy_portfolio(self):
        reg, mon = self._setup()
        p = _make_portfolio()
        p.state = PortfolioState.ACTIVE
        _add_active_allocations(p, n=3)
        reg.register(p)
        alerts = mon.run_health_check()
        # Should have no CRITICAL alerts
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical) == 0

    def test_alert_for_weight_drift(self):
        reg, mon = self._setup()
        p = _make_portfolio()
        p.state = PortfolioState.ACTIVE
        # Add allocations with heavy drift
        p.add_strategy(StrategyAllocation("s1", "S1", weight=0.70, target_weight=0.33))
        p.add_strategy(StrategyAllocation("s2", "S2", weight=0.20, target_weight=0.33))
        p.add_strategy(StrategyAllocation("s3", "S3", weight=0.10, target_weight=0.33))
        reg.register(p)
        alerts = mon.run_health_check()
        assert any(a.severity == AlertSeverity.WARNING for a in alerts)

    def test_alert_for_below_min_strategies(self):
        reg, mon = self._setup()
        p = _make_portfolio()
        p.state = PortfolioState.ACTIVE
        # Only 1 active strategy (below min of 2)
        p.add_strategy(StrategyAllocation("s1", "S1", 1.0, 1.0))
        reg.register(p)
        alerts = mon.run_health_check()
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical) >= 1

    def test_alert_history_stored(self):
        reg, mon = self._setup()
        p = _make_portfolio()
        p.state = PortfolioState.ACTIVE
        p.add_strategy(StrategyAllocation("s1", "S1", 1.0, 1.0))
        reg.register(p)
        mon.run_health_check()
        history = mon.alert_history("p1")
        assert len(history) >= 1
