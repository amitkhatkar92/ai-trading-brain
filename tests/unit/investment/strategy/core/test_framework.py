"""tests/unit/investment/strategy/core/test_framework.py
Integration tests for StrategyFramework.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.strategy.core import (
    ExecutionPlan, LifecycleError, StrategyConfiguration,
    StrategyContext, StrategyEventType, StrategyFramework,
    StrategySession, StrategyState,
)
from .conftest import (
    ConcreteStrategy, FailingStrategy, RejectAllStrategy,
    make_config, make_context, make_descriptor,
)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

class TestFrameworkLifecycle:
    def test_register_adds_to_registered(self, framework):
        desc = make_descriptor()
        framework.register(ConcreteStrategy, desc)
        assert "test_strategy" in framework.list_registered()

    def test_load_returns_ready_instance(self, framework):
        framework.register(ConcreteStrategy, make_descriptor())
        inst = framework.load("test_strategy")
        assert inst.state == StrategyState.READY

    def test_load_adds_to_loaded(self, framework):
        framework.register(ConcreteStrategy, make_descriptor())
        framework.load("test_strategy")
        assert "test_strategy" in framework.list_loaded()

    def test_unload_removes_from_loaded(self, loaded_framework):
        loaded_framework.unload("test_strategy")
        assert "test_strategy" not in loaded_framework.list_loaded()

    def test_unload_not_loaded_is_noop(self, framework):
        framework.unload("nonexistent")  # Should not raise

    def test_enable_disable(self, framework):
        framework.register(ConcreteStrategy, make_descriptor())
        framework.disable("test_strategy")
        assert "test_strategy" not in framework.list_enabled()
        framework.enable("test_strategy")
        assert "test_strategy" in framework.list_enabled()

    def test_pause_and_resume(self, loaded_framework):
        loaded_framework.pause("test_strategy")
        assert loaded_framework.get_state("test_strategy") == StrategyState.PAUSED
        loaded_framework.resume("test_strategy")
        assert loaded_framework.get_state("test_strategy") == StrategyState.RUNNING

    def test_get_state_unknown_returns_none(self, framework):
        assert framework.get_state("unknown") is None

    def test_unregister_removes(self, framework):
        framework.register(ConcreteStrategy, make_descriptor())
        framework.unregister("test_strategy")
        assert "test_strategy" not in framework.list_registered()


# ── Execution ─────────────────────────────────────────────────────────────────

class TestFrameworkExecution:
    def test_execute_returns_plan(self, loaded_framework):
        ctx = make_context()
        plan = loaded_framework.execute("test_strategy", ctx)
        assert isinstance(plan, ExecutionPlan)

    def test_execute_skipped_returns_none(self, framework):
        framework.register(ConcreteStrategy, make_descriptor())
        framework.load("test_strategy")
        ctx = make_context(symbols=[])
        plan = framework.execute("test_strategy", ctx)
        # Empty symbols → validate_inputs returns False → None
        assert plan is None

    def test_execute_unloaded_raises(self, framework):
        with pytest.raises(KeyError):
            framework.execute("nonexistent", make_context())

    def test_execute_all_sequential(self, framework):
        for i in range(3):
            framework.register(ConcreteStrategy, make_descriptor(f"s{i}"), replace=True)
            framework.load(f"s{i}")
        ctx_map = {f"s{i}": make_context(f"s{i}") for i in range(3)}
        results = framework.execute_all(ctx_map, parallel=False)
        assert len(results) == 3
        assert all(isinstance(v, ExecutionPlan) for v in results.values())

    def test_execute_all_parallel(self, framework):
        for i in range(5):
            framework.register(ConcreteStrategy, make_descriptor(f"p{i}"), replace=True)
            framework.load(f"p{i}")
        ctx_map = {f"p{i}": make_context(f"p{i}") for i in range(5)}
        results = framework.execute_all(ctx_map, parallel=True)
        assert len(results) == 5

    def test_session_history_recorded(self, loaded_framework):
        ctx = make_context()
        loaded_framework.execute("test_strategy", ctx)
        hist = loaded_framework.get_session_history("test_strategy")
        assert len(hist) == 1
        assert isinstance(hist[0], StrategySession)

    def test_success_rate_after_success(self, loaded_framework):
        loaded_framework.execute("test_strategy", make_context())
        assert loaded_framework.get_success_rate("test_strategy") == pytest.approx(1.0)

    def test_average_latency_positive(self, loaded_framework):
        loaded_framework.execute("test_strategy", make_context())
        assert loaded_framework.get_average_latency_ms("test_strategy") >= 0.0


# ── Query APIs ────────────────────────────────────────────────────────────────

class TestQueryAPIs:
    def test_get_instance(self, loaded_framework):
        inst = loaded_framework.get_instance("test_strategy")
        assert isinstance(inst, ConcreteStrategy)

    def test_get_instance_unknown_returns_none(self, framework):
        assert framework.get_instance("unknown") is None

    def test_get_descriptor(self, loaded_framework):
        desc = loaded_framework.get_descriptor("test_strategy")
        assert desc is not None
        assert desc.strategy_id == "test_strategy"

    def test_get_configuration(self, loaded_framework):
        config = loaded_framework.get_configuration("test_strategy")
        assert config is not None

    def test_get_lifecycle(self, loaded_framework):
        lc = loaded_framework.get_lifecycle("test_strategy")
        assert lc is not None
        assert lc.state == StrategyState.READY

    def test_catalog_accessible(self, loaded_framework):
        cat = loaded_framework.catalog()
        assert cat.count() >= 1

    def test_config_engine_accessible(self, loaded_framework):
        engine = loaded_framework.config_engine()
        assert engine is not None

    def test_list_registered_and_loaded(self, loaded_framework):
        assert "test_strategy" in loaded_framework.list_registered()
        assert "test_strategy" in loaded_framework.list_loaded()
        assert "test_strategy" in loaded_framework.list_enabled()


# ── Event API ─────────────────────────────────────────────────────────────────

class TestEventAPI:
    def test_subscribe_receives_events(self, framework):
        received = []
        framework.subscribe(received.append)
        framework.register(ConcreteStrategy, make_descriptor())
        assert any(e.event_type == StrategyEventType.STRATEGY_REGISTERED for e in received)

    def test_unsubscribe_stops_receiving(self, framework):
        received = []
        framework.subscribe(received.append)
        framework.unsubscribe(received.append)
        framework.register(ConcreteStrategy, make_descriptor())
        assert len(received) == 0

    def test_event_history_for_strategy(self, loaded_framework):
        loaded_framework.execute("test_strategy", make_context())
        events = loaded_framework.event_history("test_strategy")
        assert len(events) > 0

    def test_recent_events(self, loaded_framework):
        loaded_framework.execute("test_strategy", make_context())
        recent = loaded_framework.recent_events(50)
        assert len(recent) > 0


# ── Configuration API ─────────────────────────────────────────────────────────

class TestConfigurationAPI:
    def test_declare_parameter(self, loaded_framework):
        from iios.investment.strategy.core import ParameterSpec
        loaded_framework.declare_parameter(
            "test_strategy",
            ParameterSpec(name="lookback", type=int, default=20),
        )
        engine = loaded_framework.config_engine()
        spec = engine.parameter_registry.get("test_strategy", "lookback")
        assert spec is not None

    def test_update_configuration(self, loaded_framework):
        config = loaded_framework.update_configuration(
            "test_strategy", {"alpha": 0.9}, reason="test"
        )
        assert config.get("alpha") == pytest.approx(0.9)


# ── Health report ─────────────────────────────────────────────────────────────

class TestHealthReport:
    def test_health_report_structure(self, loaded_framework):
        report = loaded_framework.health_report()
        assert all(k in report for k in [
            "registered_count", "loaded_count",
            "enabled_count", "loaded_strategies", "total_events",
        ])

    def test_health_report_loaded_strategies(self, loaded_framework):
        report = loaded_framework.health_report()
        assert "test_strategy" in report["loaded_strategies"]
        strat = report["loaded_strategies"]["test_strategy"]
        assert "state" in strat
        assert "execution_count" in strat
        assert "success_rate" in strat

    def test_repr(self, loaded_framework):
        r = repr(loaded_framework)
        assert "StrategyFramework" in r


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_register_and_load(self, framework):
        errors = []

        def run(i):
            try:
                desc = make_descriptor(f"ts{i}")
                framework.register(ConcreteStrategy, desc)
                framework.load(f"ts{i}")
                framework.execute(f"ts{i}", make_context(f"ts{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert framework.health_report()["loaded_count"] == 15

    def test_concurrent_execute_same_strategy(self, loaded_framework):
        """Only one thread can execute at a time; others get StrategyError (busy).
        The framework must never corrupt state or raise unexpected exceptions."""
        from iios.investment.strategy.core import StrategyError
        unexpected = []

        def run():
            try:
                loaded_framework.execute("test_strategy", make_context())
            except StrategyError:
                pass  # expected: only one may hold RUNNING at a time
            except Exception as e:
                unexpected.append(e)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert unexpected == []
        # Framework must end in a stable state
        state = loaded_framework.get_state("test_strategy")
        assert state in (StrategyState.READY, StrategyState.PAUSED)


# ── Hot reload ────────────────────────────────────────────────────────────────

class TestHotReload:
    def test_update_config_at_runtime(self, loaded_framework):
        loaded_framework.update_configuration(
            "test_strategy", {"param_a": 123}
        )
        config = loaded_framework.get_configuration("test_strategy")
        assert config.get("param_a") == 123
        # Strategy is still READY after hot reload
        assert loaded_framework.get_state("test_strategy") == StrategyState.READY


# ── Plugin loading ────────────────────────────────────────────────────────────

class TestPluginLoading:
    def test_load_from_module_not_found(self, framework):
        from iios.investment.strategy.core import LoaderError
        with pytest.raises(LoaderError):
            framework.load_from_module("totally.fake.module.path")
