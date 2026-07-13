"""tests/unit/investment/strategy/core/test_lifecycle.py
Tests for StrategyLifecycle, StrategySession, ExecutionHistory.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.core import (
    EventDispatcher, ExecutionHistory, LifecycleError,
    SessionMetrics, StrategySession, StrategyState,
    StrategyLifecycle, StrategyEventType,
)


# ── StrategyLifecycle ─────────────────────────────────────────────────────────

class TestStrategyLifecycle:
    @pytest.fixture
    def dispatcher(self):
        return EventDispatcher()

    def test_initial_state_emits_event(self, dispatcher):
        received = []
        dispatcher.subscribe(received.append)
        lc = StrategyLifecycle("s1", dispatcher, StrategyState.REGISTERED)
        assert any(e.event_type == StrategyEventType.STRATEGY_REGISTERED for e in received)

    def test_initial_state(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        assert lc.state == StrategyState.REGISTERED

    def test_valid_transition(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        lc.transition(StrategyState.LOADED)
        assert lc.state == StrategyState.LOADED

    def test_invalid_transition_raises(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        with pytest.raises(LifecycleError):
            lc.transition(StrategyState.RUNNING)

    def test_transition_increments_count(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        lc.transition(StrategyState.LOADED)
        lc.transition(StrategyState.INITIALIZED)
        assert lc.transition_count == 2

    def test_state_history(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        lc.transition(StrategyState.LOADED)
        hist = lc.state_history()
        assert len(hist) == 2
        assert hist[0][0] == StrategyState.REGISTERED
        assert hist[1][0] == StrategyState.LOADED

    def test_age_seconds_positive(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        assert lc.age_seconds >= 0.0

    def test_to_dict_keys(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher)
        d = lc.to_dict()
        assert all(k in d for k in [
            "strategy_id", "state", "entered_at",
            "transition_count", "age_seconds",
        ])

    def test_transition_emits_event(self, dispatcher):
        received = []
        dispatcher.subscribe(received.append)
        lc = StrategyLifecycle("s1", dispatcher)
        lc.transition(StrategyState.LOADED)
        assert any(e.event_type == StrategyEventType.STRATEGY_LOADED for e in received)

    def test_full_happy_path(self, dispatcher):
        lc = StrategyLifecycle("s1", dispatcher, StrategyState.LOADED)
        lc.transition(StrategyState.INITIALIZED)
        lc.transition(StrategyState.READY)
        lc.transition(StrategyState.RUNNING)
        lc.transition(StrategyState.READY)
        assert lc.state == StrategyState.READY


# ── SessionMetrics ────────────────────────────────────────────────────────────

class TestSessionMetrics:
    def test_defaults_zero(self):
        m = SessionMetrics()
        assert m.signals_generated == 0
        assert m.plan_produced is False

    def test_to_dict(self):
        m = SessionMetrics(signals_generated=5, plan_produced=True)
        d = m.to_dict()
        assert d["signals_generated"] == 5
        assert d["plan_produced"] is True


# ── StrategySession ───────────────────────────────────────────────────────────

class TestStrategySession:
    def test_session_id_prefixed(self):
        s = StrategySession()
        assert s.session_id.startswith("sess-")

    def test_initial_state_running(self):
        s = StrategySession()
        assert s.state == StrategyState.RUNNING

    def test_close_sets_completed(self):
        s = StrategySession()
        s.close(plan_id="plan-001")
        assert s.is_complete
        assert s.plan_id == "plan-001"
        assert s.state == StrategyState.COMPLETED

    def test_close_with_error(self):
        s = StrategySession()
        s.close(error="boom")
        assert s.state == StrategyState.FAILED
        assert s.error == "boom"
        assert not s.succeeded

    def test_succeeded_with_plan(self):
        s = StrategySession()
        s.close(plan_id="p-001")
        assert s.succeeded

    def test_duration_ms_positive(self):
        s = StrategySession()
        s.close()
        assert s.duration_ms >= 0

    def test_to_dict_keys(self):
        s = StrategySession(strategy_id="x")
        s.close()
        d = s.to_dict()
        assert all(k in d for k in [
            "session_id", "strategy_id", "started_at", "completed_at",
            "state", "duration_ms", "plan_id", "error", "metrics",
        ])


# ── ExecutionHistory ──────────────────────────────────────────────────────────

class TestExecutionHistory:
    def _session(self, sid: str, succeed: bool = True) -> StrategySession:
        s = StrategySession(strategy_id=sid)
        s.close(plan_id=("plan-x" if succeed else None), error=(None if succeed else "err"))
        return s

    def test_record_and_for_strategy(self):
        h = ExecutionHistory()
        h.record(self._session("A"))
        assert len(h.for_strategy("A")) == 1

    def test_for_strategy_empty(self):
        h = ExecutionHistory()
        assert h.for_strategy("unknown") == []

    def test_latest(self):
        h = ExecutionHistory()
        h.record(self._session("A"))
        s2 = self._session("A")
        h.record(s2)
        assert h.latest("A") is s2

    def test_total_sessions(self):
        h = ExecutionHistory()
        for _ in range(4):
            h.record(self._session("A"))
        assert h.total_sessions("A") == 4

    def test_success_rate_all_succeed(self):
        h = ExecutionHistory()
        for _ in range(5):
            h.record(self._session("A", succeed=True))
        assert h.success_rate("A") == pytest.approx(1.0)

    def test_success_rate_none_succeed(self):
        h = ExecutionHistory()
        for _ in range(3):
            h.record(self._session("A", succeed=False))
        assert h.success_rate("A") == pytest.approx(0.0)

    def test_success_rate_mixed(self):
        h = ExecutionHistory()
        h.record(self._session("A", succeed=True))
        h.record(self._session("A", succeed=False))
        assert h.success_rate("A") == pytest.approx(0.5)

    def test_average_latency_positive(self):
        h = ExecutionHistory()
        h.record(self._session("A"))
        assert h.average_latency_ms("A") >= 0.0

    def test_known_strategies(self):
        h = ExecutionHistory()
        h.record(self._session("A"))
        h.record(self._session("B"))
        assert set(h.known_strategies()) == {"A", "B"}

    def test_for_strategy_n_limit(self):
        h = ExecutionHistory()
        for _ in range(10):
            h.record(self._session("A"))
        assert len(h.for_strategy("A", n=3)) == 3
