"""tests/unit/investment/decision/core/test_framework.py
End-to-end tests for DecisionFramework facade.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from iios.investment.decision.core.configuration_engine import ConfigurationEngine
from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_constants import (
    DecisionEventType,
    DecisionFrameworkStatus,
    DecisionStatus,
    DecisionType,
    EnvironmentProfile,
)
from iios.investment.decision.core.decision_context import make_context
from iios.investment.decision.core.decision_framework import DecisionFramework
from iios.investment.decision.core.decision_registry import DecisionRegistry
from tests.unit.investment.decision.core.conftest import (
    FailingDecision,
    RejectedDecision,
    SimpleBuyDecision,
)


def _make_framework(env: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT) -> DecisionFramework:
    fw = DecisionFramework(environment=env)
    fw.register_decision_type("simple_buy", SimpleBuyDecision)
    fw.register_decision_type("rejected",   RejectedDecision)
    fw.register_decision_type("failing",    FailingDecision)
    fw.start()
    return fw


def _ctx(subject_id: str = "RELIANCE", decision_type: DecisionType = DecisionType.INVESTMENT):
    return make_context(
        decision_type=decision_type,
        subject_id=subject_id,
        subject_type="equity",
        source="test_framework",
        environment=EnvironmentProfile.DEVELOPMENT,
    )


# ===========================================================================
# Framework start/stop
# ===========================================================================

class TestDecisionFrameworkStartStop:
    def test_starts_in_ready_state(self):
        fw = _make_framework()
        assert fw.status == DecisionFrameworkStatus.READY

    def test_stop_changes_status(self):
        fw = _make_framework()
        fw.stop()
        assert fw.status == DecisionFrameworkStatus.STOPPED

    def test_environment_accessible(self):
        fw = _make_framework()
        assert fw.environment == EnvironmentProfile.DEVELOPMENT

    def test_status_is_operational(self):
        fw = _make_framework()
        assert fw.status.is_operational

    def test_framework_started_event_emitted(self):
        events = []
        fw = DecisionFramework()
        fw.event_bus.subscribe(lambda e: events.append(e))
        fw.start()
        types = [e.event_type for e in events]
        assert DecisionEventType.FRAMEWORK_STARTED in types


# ===========================================================================
# Decision type registration
# ===========================================================================

class TestFrameworkRegistration:
    def test_register_type(self):
        fw = DecisionFramework()
        fw.register_decision_type("my_decision", SimpleBuyDecision)
        assert "my_decision" in fw.known_decision_types()

    def test_registry_info(self):
        fw = _make_framework()
        info = fw.get_registry_info()
        assert "registered_types" in info
        assert "simple_buy" in info["registered_types"]

    def test_known_decision_types(self):
        fw = _make_framework()
        types = fw.known_decision_types()
        assert "simple_buy" in types
        assert "rejected" in types


# ===========================================================================
# Decision execution — async
# ===========================================================================

class TestFrameworkExecutionAsync:
    @pytest.mark.asyncio
    async def test_execute_simple_buy(self):
        fw    = _make_framework()
        ctx   = _ctx("INFY")
        state = await fw.execute("simple_buy", ctx)
        assert state.status == DecisionStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_execute_rejected(self):
        fw    = _make_framework()
        ctx   = _ctx("WIPRO")
        state = await fw.execute("rejected", ctx)
        assert state.status == DecisionStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_failing_decision_raises(self):
        fw  = _make_framework()
        ctx = _ctx("TCS")
        with pytest.raises(RuntimeError):
            await fw.execute("failing", ctx)

    @pytest.mark.asyncio
    async def test_decision_recorded_in_history(self):
        fw    = _make_framework()
        ctx   = _ctx("HDFC")
        await fw.execute("simple_buy", ctx)
        history = fw.get_decision_history("HDFC")
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_execute_batch(self):
        fw   = _make_framework()
        tasks = [
            ("simple_buy", _ctx("A")),
            ("simple_buy", _ctx("B")),
            ("rejected",   _ctx("C")),
        ]
        results = await fw.execute_batch(tasks)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_batch_failing_does_not_crash_others(self):
        fw    = _make_framework()
        tasks = [
            ("simple_buy", _ctx("GOOD")),
            ("failing",    _ctx("BAD")),
        ]
        results = await fw.execute_batch(tasks)
        # "GOOD" should succeed; "BAD" should be omitted from results
        good_ctx  = tasks[0][1]
        assert good_ctx.decision_id in results

    @pytest.mark.asyncio
    async def test_events_captured_in_history(self):
        fw  = _make_framework()
        ctx = _ctx("ONGC")
        await fw.execute("simple_buy", ctx)
        events = fw.get_events(ctx.decision_id)
        assert len(events) > 0


# ===========================================================================
# Decision execution — sync wrapper
# ===========================================================================

class TestFrameworkExecutionSync:
    def test_execute_sync(self):
        fw    = _make_framework()
        ctx   = _ctx("TATASTEEL")
        state = fw.execute_sync("simple_buy", ctx)
        assert state.status == DecisionStatus.ARCHIVED


# ===========================================================================
# Session management
# ===========================================================================

class TestFrameworkSessionManagement:
    def test_create_session(self):
        fw      = _make_framework()
        session = fw.create_session("test_session")
        assert session.is_open
        assert fw.get_session(session.session_id) is session

    def test_close_session(self):
        fw      = _make_framework()
        session = fw.create_session()
        fw.close_session(session.session_id)
        assert not session.is_open

    def test_get_missing_session_returns_none(self):
        fw = _make_framework()
        assert fw.get_session("nonexistent") is None

    def test_stats_open_sessions(self):
        fw = _make_framework()
        fw.create_session("s1")
        fw.create_session("s2")
        s = fw.stats()
        assert s["open_sessions"] >= 2


# ===========================================================================
# Query APIs
# ===========================================================================

class TestFrameworkQueryAPIs:
    @pytest.mark.asyncio
    async def test_get_decision_history_subject(self):
        fw  = _make_framework()
        ctx = _ctx("BAJAJ")
        await fw.execute("simple_buy", ctx)
        history = fw.get_decision_history("BAJAJ")
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_get_decision_history_recent(self):
        fw = _make_framework()
        for sid in ["X1", "X2", "X3"]:
            await fw.execute("simple_buy", _ctx(sid))
        history = fw.get_decision_history(limit=2)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_decision_state_archived(self):
        fw  = _make_framework()
        ctx = _ctx("MARUTI")
        await fw.execute("simple_buy", ctx)
        state = fw.get_decision_state(ctx.decision_id)
        assert state is not None

    def test_get_decision_state_missing(self):
        fw = _make_framework()
        assert fw.get_decision_state("nonexistent") is None

    def test_get_configuration_default(self):
        fw  = _make_framework()
        cfg = fw.get_configuration()
        assert cfg is not None

    def test_get_configuration_named(self):
        fw  = _make_framework()
        fw.config_engine.register("momentum", DecisionConfiguration(approval_threshold=80.0))
        cfg = fw.get_configuration("momentum")
        assert cfg.approval_threshold == 80.0

    def test_get_event_count(self):
        fw = _make_framework()
        assert fw.get_event_count() >= 1  # FRAMEWORK_STARTED event

    def test_stats_structure(self):
        fw = _make_framework()
        s  = fw.stats()
        assert "status"           in s
        assert "environment"      in s
        assert "registered_types" in s
        assert "total_decisions"  in s
        assert "event_count"      in s

    def test_current_decisions_empty_when_idle(self):
        fw = _make_framework()
        assert fw.get_current_decisions() == []

    def test_properties_accessible(self):
        fw = _make_framework()
        assert fw.event_bus is not None
        assert fw.registry is not None
        assert fw.catalog is not None
        assert fw.config_engine is not None
        assert fw.param_registry is not None
