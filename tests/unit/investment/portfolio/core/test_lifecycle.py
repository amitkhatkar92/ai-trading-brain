"""tests/unit/investment/portfolio/core/test_lifecycle.py

Tests for PortfolioLifecycle, PortfolioStateStore, PortfolioSession,
SessionManager, and BasePortfolio lifecycle hooks.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.core.portfolio_lifecycle import (
    LifecycleError,
    LifecycleTransition,
    PortfolioLifecycle,
)
from iios.investment.portfolio.core.portfolio_session import (
    PortfolioSession,
    SessionManager,
    SessionState,
)
from iios.investment.portfolio.core.portfolio_state import (
    PortfolioStateSnapshot,
    PortfolioStateStore,
)
from iios.investment.portfolio.core.portfolio_types import PortfolioLifecycleState


class TestPortfolioLifecycle:
    def test_initial_state_is_registered(self):
        lc = PortfolioLifecycle("P1")
        assert lc.current_state == PortfolioLifecycleState.REGISTERED

    def test_valid_transition(self):
        lc = PortfolioLifecycle("P1")
        rec = lc.transition(PortfolioLifecycleState.INITIALIZED)
        assert lc.current_state == PortfolioLifecycleState.INITIALIZED
        assert isinstance(rec, LifecycleTransition)

    def test_invalid_transition_raises(self):
        lc = PortfolioLifecycle("P1")
        with pytest.raises(LifecycleError):
            lc.transition(PortfolioLifecycleState.ACTIVE)

    def test_full_path(self):
        lc = PortfolioLifecycle("P1")
        lc.transition(PortfolioLifecycleState.INITIALIZED)
        lc.transition(PortfolioLifecycleState.READY)
        lc.transition(PortfolioLifecycleState.CONSTRUCTED)
        lc.transition(PortfolioLifecycleState.ACTIVE)
        assert lc.current_state == PortfolioLifecycleState.ACTIVE
        assert lc.is_operational

    def test_terminal_state_blocks_transitions(self):
        lc = PortfolioLifecycle("P1")
        lc.force_to(PortfolioLifecycleState.ARCHIVED)
        with pytest.raises(LifecycleError):
            lc.transition(PortfolioLifecycleState.ACTIVE)

    def test_history_recorded(self):
        lc = PortfolioLifecycle("P1")
        lc.transition(PortfolioLifecycleState.INITIALIZED)
        lc.transition(PortfolioLifecycleState.READY)
        assert len(lc.history()) == 2

    def test_last_transition(self):
        lc = PortfolioLifecycle("P1")
        lc.transition(PortfolioLifecycleState.INITIALIZED)
        last = lc.last_transition()
        assert last is not None
        assert last.to_state == PortfolioLifecycleState.INITIALIZED

    def test_can_transition_to(self):
        lc = PortfolioLifecycle("P1")
        assert lc.can_transition_to(PortfolioLifecycleState.INITIALIZED)
        assert not lc.can_transition_to(PortfolioLifecycleState.ACTIVE)

    def test_transitions_to_filter(self):
        lc = PortfolioLifecycle("P1")
        lc.transition(PortfolioLifecycleState.INITIALIZED)
        hits = lc.transitions_to(PortfolioLifecycleState.INITIALIZED)
        assert len(hits) == 1

    def test_force_to(self):
        lc = PortfolioLifecycle("P1")
        lc.force_to(PortfolioLifecycleState.PAUSED)
        assert lc.current_state == PortfolioLifecycleState.PAUSED

    def test_to_dict(self):
        lc = PortfolioLifecycle("P1")
        d = lc.to_dict()
        assert "current_state" in d
        assert d["portfolio_id"] == "P1"

    def test_time_in_state(self):
        lc = PortfolioLifecycle("P1")
        assert lc.time_in_current_state_seconds() >= 0.0

    def test_failed_transition_from_active(self):
        lc = PortfolioLifecycle("P1")
        lc.force_to(PortfolioLifecycleState.ACTIVE)
        lc.transition(PortfolioLifecycleState.FAILED)
        assert lc.current_state == PortfolioLifecycleState.FAILED


class TestPortfolioStateStore:
    def test_initial_version_zero(self):
        s = PortfolioStateStore("P1")
        assert s.version == 0

    def test_mark_configured_bumps_version(self):
        s = PortfolioStateStore("P1")
        s.mark_configured()
        assert s.version == 1
        snap = s.snapshot()
        assert snap.is_configured

    def test_mark_validated(self):
        s = PortfolioStateStore("P1")
        s.mark_validated()
        assert s.snapshot().is_validated

    def test_mark_constructed(self):
        s = PortfolioStateStore("P1")
        s.mark_constructed()
        snap = s.snapshot()
        assert snap.is_constructed
        assert snap.last_construct_at is not None

    def test_record_rebalance(self):
        s = PortfolioStateStore("P1")
        s.record_rebalance()
        s.record_rebalance()
        snap = s.snapshot()
        assert snap.rebalance_count == 2

    def test_record_error(self):
        s = PortfolioStateStore("P1")
        s.record_error("something bad")
        snap = s.snapshot()
        assert snap.error_count == 1
        assert snap.last_error == "something bad"

    def test_clear_error(self):
        s = PortfolioStateStore("P1")
        s.record_error("err")
        s.clear_error()
        assert s.snapshot().last_error is None

    def test_set_attribute(self):
        s = PortfolioStateStore("P1")
        s.set_attribute("my_key", 42)
        assert s.snapshot().attributes["my_key"] == 42

    def test_snapshot_is_frozen(self):
        s = PortfolioStateStore("P1")
        snap = s.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.version = 999  # type: ignore

    def test_snapshot_to_dict(self):
        s = PortfolioStateStore("P1")
        d = s.snapshot().to_dict()
        assert "lifecycle_state" in d
        assert "version" in d


class TestPortfolioSession:
    def test_open_session(self):
        sess = PortfolioSession("P1")
        assert sess.is_open
        assert sess.state == SessionState.OPEN

    def test_close_session(self):
        sess = PortfolioSession("P1")
        rec = sess.close(reason="test")
        assert rec.session_state == SessionState.CLOSED
        assert rec.duration_seconds >= 0.0

    def test_close_twice_raises(self):
        sess = PortfolioSession("P1")
        sess.close()
        with pytest.raises(RuntimeError):
            sess.close()

    def test_record_operations(self):
        sess = PortfolioSession("P1")
        sess.record_rebalance()
        sess.record_evaluate()
        sess.record_monitor()
        sess.record_error()
        rec = sess.close()
        assert rec.rebalance_count == 1
        assert rec.evaluate_count == 1
        assert rec.error_count == 1
        assert not rec.is_healthy

    def test_failed_close(self):
        sess = PortfolioSession("P1")
        rec = sess.close(failed=True)
        assert rec.session_state == SessionState.FAILED

    def test_record_to_dict(self):
        sess = PortfolioSession("P1")
        rec = sess.close()
        d = rec.to_dict()
        assert "session_id" in d
        assert "duration_seconds" in d


class TestSessionManager:
    def test_open_session(self):
        mgr = SessionManager()
        sess = mgr.open_session("P1")
        assert sess.is_open
        assert mgr.active_count() == 1

    def test_get_active_session(self):
        mgr = SessionManager()
        mgr.open_session("P1")
        s = mgr.get_active_session("P1")
        assert s is not None

    def test_close_session(self):
        mgr = SessionManager()
        mgr.open_session("P1")
        rec = mgr.close_session("P1", reason="done")
        assert rec is not None
        assert rec.portfolio_id == "P1"
        assert mgr.active_count() == 0

    def test_supersede_on_reopen(self):
        mgr = SessionManager()
        mgr.open_session("P1")
        mgr.open_session("P1")  # supersedes first
        assert mgr.active_count() == 1

    def test_records_for(self):
        mgr = SessionManager()
        mgr.open_session("P1")
        mgr.close_session("P1")
        mgr.open_session("P1")
        mgr.close_session("P1")
        recs = mgr.records_for("P1")
        assert len(recs) == 2

    def test_recent_records(self):
        mgr = SessionManager()
        for _ in range(5):
            mgr.open_session("P1")
            mgr.close_session("P1")
        assert len(mgr.recent_records(3)) == 3


class TestBasePortfolioLifecycle:
    def test_initialize_transitions_to_initialized(self, swing_portfolio):
        swing_portfolio._framework_initialize()
        assert swing_portfolio.lifecycle_state == PortfolioLifecycleState.INITIALIZED

    def test_ready_transitions_to_ready(self, swing_portfolio):
        swing_portfolio._framework_initialize()
        swing_portfolio._framework_ready()
        assert swing_portfolio.lifecycle_state == PortfolioLifecycleState.READY

    def test_construct_transitions_to_active(self, swing_portfolio):
        swing_portfolio._framework_initialize()
        swing_portfolio._framework_ready()
        swing_portfolio._framework_construct()
        swing_portfolio._framework_activate()
        assert swing_portfolio.lifecycle_state == PortfolioLifecycleState.ACTIVE

    def test_failing_initialize(self, failing_portfolio):
        with pytest.raises(RuntimeError):
            failing_portfolio._framework_initialize()
        assert failing_portfolio.lifecycle_state == PortfolioLifecycleState.FAILED

    def test_state_records_rebalance(self, swing_portfolio):
        swing_portfolio._framework_initialize()
        swing_portfolio._framework_ready()
        swing_portfolio._framework_construct()
        swing_portfolio._framework_activate()
        swing_portfolio._framework_rebalance()
        snap = swing_portfolio.state_snapshot
        assert snap.rebalance_count == 1

    def test_get_info(self, swing_portfolio):
        d = swing_portfolio.get_info()
        assert d["portfolio_id"] == "TEST-SWING-001"
        assert "lifecycle_state" in d

    def test_repr(self, swing_portfolio):
        r = repr(swing_portfolio)
        assert "_MinimalPortfolio" in r
