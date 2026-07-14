"""tests/unit/investment/portfolio/core/test_framework.py

Tests for PortfolioFramework — lifecycle, creation, query, events,
concurrency, and statistics.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.portfolio.core.portfolio_events import (
    PortfolioEventType,
    PortfolioRegisteredEvent,
)
from iios.investment.portfolio.core.portfolio_framework import (
    FrameworkStatistics,
    PortfolioFramework,
)
from iios.investment.portfolio.core.portfolio_types import (
    FrameworkStatus,
    PortfolioDomain,
    PortfolioLifecycleState,
)


class TestFrameworkLifecycle:
    def test_start_sets_running(self, framework):
        assert framework.status == FrameworkStatus.RUNNING
        assert framework.is_running

    def test_stop_sets_stopped(self, framework):
        framework.stop()
        assert framework.status == FrameworkStatus.STOPPED

    def test_double_start_safe(self):
        PortfolioFramework.reset_instance()
        fw = PortfolioFramework(environment="paper")
        fw.start()
        fw.start()
        assert fw.is_running
        fw.stop()
        PortfolioFramework.reset_instance()

    def test_stop_without_start_safe(self):
        PortfolioFramework.reset_instance()
        fw = PortfolioFramework(environment="paper")
        fw.stop()  # should not raise
        PortfolioFramework.reset_instance()

    def test_create_before_start_raises(self):
        PortfolioFramework.reset_instance()
        fw = PortfolioFramework(environment="paper")
        fw.register_class(
            __import__(
                "tests.unit.investment.portfolio.core.conftest",
                fromlist=["_MinimalPortfolio"]
            )._MinimalPortfolio,
            domain=PortfolioDomain.SWING,
        )
        with pytest.raises(RuntimeError):
            fw.create_portfolio("_MinimalPortfolio")
        PortfolioFramework.reset_instance()

    def test_singleton(self):
        PortfolioFramework.reset_instance()
        fw1 = PortfolioFramework.get_instance()
        fw2 = PortfolioFramework.get_instance()
        assert fw1 is fw2
        PortfolioFramework.reset_instance()


class TestPortfolioCreation:
    def test_create_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio", name="My Swing")
        assert p is not None
        assert p.name == "My Swing"

    def test_created_portfolio_in_list(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        assert p.portfolio_id in framework.list_portfolios()

    def test_unknown_class_raises(self, framework):
        with pytest.raises(RuntimeError):
            framework.create_portfolio("NonExistentClass")

    def test_explicit_portfolio_id(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio", portfolio_id="MYID")
        assert p.portfolio_id == "MYID"

    def test_long_term_domain(self, framework):
        p = framework.create_portfolio("_LongTermPortfolio")
        assert p.metadata.domain == PortfolioDomain.LONG_TERM


class TestPortfolioLifecycleManagement:
    def test_initialize_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        assert p.lifecycle_state == PortfolioLifecycleState.INITIALIZED

    def test_prepare_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        assert p.lifecycle_state == PortfolioLifecycleState.READY

    def test_construct_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        assert p.lifecycle_state == PortfolioLifecycleState.ACTIVE

    def test_archive_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        framework.archive_portfolio(p.portfolio_id, reason="test")
        # Portfolio removed from active list
        assert p.portfolio_id not in framework.list_portfolios()

    def test_pause_and_resume(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        framework.pause_portfolio(p.portfolio_id, reason="maintenance")
        assert p.lifecycle_state == PortfolioLifecycleState.PAUSED
        framework.resume_portfolio(p.portfolio_id)
        assert p.lifecycle_state == PortfolioLifecycleState.ACTIVE

    def test_monitor_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        framework.monitor_portfolio(p.portfolio_id)
        assert p.state_snapshot.monitor_count == 1

    def test_evaluate_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        framework.evaluate_portfolio(p.portfolio_id)
        assert p.state_snapshot.evaluate_count == 1

    def test_failing_initialize_dispatches_failed_event(self, framework):
        received = []
        framework.subscribe_events(
            lambda e: received.append(e),
            event_types={PortfolioEventType.PORTFOLIO_FAILED},
        )
        p = framework.create_portfolio("_FailingPortfolio")
        with pytest.raises(RuntimeError):
            framework.initialize_portfolio(p.portfolio_id)
        assert len(received) == 1


class TestPortfolioQueryAPI:
    def test_get_portfolio(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        assert framework.get_portfolio(p.portfolio_id) is p

    def test_get_portfolio_missing_returns_none(self, framework):
        assert framework.get_portfolio("nonexistent") is None

    def test_portfolio_details(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        d = framework.portfolio_details(p.portfolio_id)
        assert d["portfolio_id"] == p.portfolio_id

    def test_portfolio_state(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        d = framework.portfolio_state(p.portfolio_id)
        assert "lifecycle_state" in d

    def test_portfolio_lifecycle(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        d = framework.portfolio_lifecycle(p.portfolio_id)
        assert "current_state" in d

    def test_portfolio_history(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        h = framework.portfolio_history(p.portfolio_id)
        assert isinstance(h, list)
        assert len(h) >= 1

    def test_portfolio_capabilities(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        caps = framework.portfolio_capabilities(p.portfolio_id)
        assert isinstance(caps, list)

    def test_portfolio_configuration_after_init(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        cfg_dict = framework.portfolio_configuration(p.portfolio_id)
        assert cfg_dict is not None
        assert "capital_limits" in cfg_dict

    def test_portfolios_by_domain(self, framework):
        framework.create_portfolio("_MinimalPortfolio")
        framework.create_portfolio("_LongTermPortfolio")
        swing = framework.portfolios_by_domain(PortfolioDomain.SWING)
        assert len(swing) >= 1

    def test_missing_portfolio_raises_on_details(self, framework):
        with pytest.raises(KeyError):
            framework.portfolio_details("nonexistent")


class TestFrameworkEvents:
    def test_subscribe_and_receive(self, framework, events_received):
        framework.subscribe_events(lambda e: events_received.append(e))
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        # At minimum, a PORTFOLIO_REGISTERED and PORTFOLIO_INITIALIZED event
        assert len(events_received) >= 1

    def test_unsubscribe(self, framework):
        received = []
        hid = framework.subscribe_events(lambda e: received.append(e))
        framework.unsubscribe_events(hid)
        framework.create_portfolio("_MinimalPortfolio")
        assert len(received) == 0

    def test_event_history_populated(self, framework):
        framework.create_portfolio("_MinimalPortfolio")
        assert framework.event_history.count() >= 1

    def test_publish_custom_event(self, framework):
        from iios.investment.portfolio.core.portfolio_events import PortfolioEvent
        received = []
        framework.subscribe_events(lambda e: received.append(e))
        ev = PortfolioEvent(portfolio_id="P1",
                            event_type=PortfolioEventType.PORTFOLIO_UPDATED)
        framework.publish_event(ev)
        assert len(received) >= 1


class TestFrameworkStatistics:
    def test_initial_stats(self, framework):
        stats = framework.stats()
        assert isinstance(stats, FrameworkStatistics)
        assert stats.status == FrameworkStatus.RUNNING.value

    def test_registered_classes_count(self, framework):
        stats = framework.stats()
        assert stats.registered_classes >= 3

    def test_total_portfolios_increments(self, framework):
        before = framework.stats().total_portfolios
        framework.create_portfolio("_MinimalPortfolio")
        after = framework.stats().total_portfolios
        assert after == before + 1

    def test_archived_count_increments(self, framework):
        p = framework.create_portfolio("_MinimalPortfolio")
        framework.initialize_portfolio(p.portfolio_id)
        framework.prepare_portfolio(p.portfolio_id)
        framework.construct_portfolio(p.portfolio_id)
        before = framework.stats().archived_portfolios
        framework.archive_portfolio(p.portfolio_id)
        after = framework.stats().archived_portfolios
        assert after == before + 1

    def test_uptime_positive_after_start(self, framework):
        import time
        time.sleep(0.01)
        stats = framework.stats()
        assert stats.uptime_seconds > 0.0

    def test_stats_to_dict(self, framework):
        d = framework.stats().to_dict()
        assert "framework_version" in d
        assert "active_portfolios" in d
        assert "uptime_seconds" in d


class TestFrameworkConcurrency:
    def test_concurrent_portfolio_creation(self, framework):
        errors = []
        portfolios = []
        lock = threading.Lock()

        def create():
            try:
                p = framework.create_portfolio("_MinimalPortfolio")
                with lock:
                    portfolios.append(p.portfolio_id)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=create) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(portfolios) == 10

    def test_concurrent_event_dispatch(self, framework):
        received = []
        lock = threading.Lock()

        def handler(e):
            with lock:
                received.append(e)

        framework.subscribe_events(handler)

        from iios.investment.portfolio.core.portfolio_events import PortfolioEvent

        def dispatch():
            framework.publish_event(
                PortfolioEvent(portfolio_id="X",
                               event_type=PortfolioEventType.PORTFOLIO_UPDATED)
            )

        threads = [threading.Thread(target=dispatch) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(received) == 20
