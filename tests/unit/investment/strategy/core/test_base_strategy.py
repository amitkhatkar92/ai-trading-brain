"""tests/unit/investment/strategy/core/test_base_strategy.py
Tests for InstitutionalBaseStrategy and its domain objects.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.core import (
    Candidate, ExecutionPlan, InstitutionalBaseStrategy, RiskValidationError,
    Signal, StrategyError, StrategyState,
)
from .conftest import (
    ConcreteStrategy, FailingStrategy, InvalidInputStrategy,
    RejectAllStrategy, EmptyUniverseStrategy,
    make_config, make_context, make_descriptor,
)


# ── Signal ────────────────────────────────────────────────────────────────────

class TestSignal:
    def test_signal_id_prefixed(self):
        s = Signal("strat", "INFY", "long", 0.8)
        assert s.signal_id.startswith("sig-")

    def test_confidence_clamped_high(self):
        s = Signal("strat", "INFY", "long", 1.5)
        assert s.confidence == 1.0

    def test_confidence_clamped_low(self):
        s = Signal("strat", "INFY", "short", -0.3)
        assert s.confidence == 0.0

    def test_to_dict_keys(self):
        d = Signal("strat", "INFY", "long", 0.7).to_dict()
        assert all(k in d for k in [
            "signal_id", "strategy_id", "ticker", "direction",
            "confidence", "score", "generated_at",
        ])

    def test_metadata_default_empty(self):
        s = Signal("strat", "TCS", "neutral", 0.5)
        assert s.metadata == {}


# ── Candidate ─────────────────────────────────────────────────────────────────

class TestCandidate:
    def test_total_score_empty(self):
        c = Candidate("INFY")
        assert c.total_score() == 0.0

    def test_add_score(self):
        c = Candidate("TCS")
        c.add_score("momentum", 60.0)
        c.add_score("quality", 40.0)
        assert c.total_score() == pytest.approx(100.0)

    def test_notes_list(self):
        c = Candidate("X")
        c.notes.append("strong breakout")
        assert len(c.notes) == 1


# ── ExecutionPlan ─────────────────────────────────────────────────────────────

class TestExecutionPlan:
    def test_plan_id_prefixed(self):
        p = ExecutionPlan("strat", [])
        assert p.plan_id.startswith("plan-")

    def test_add_position_size(self):
        s = Signal("strat", "INFY", "long", 0.8)
        p = ExecutionPlan("strat", [s])
        p.add_position_size("INFY", 0.25)
        assert p.position_sizes["INFY"] == pytest.approx(0.25)

    def test_to_dict_keys(self):
        p = ExecutionPlan("strat", [])
        d = p.to_dict()
        assert "plan_id" in d and "signal_count" in d


# ── BaseStrategy state machine ────────────────────────────────────────────────

class TestBaseStrategyStateMachine:
    def test_initial_state_registered(self, strategy):
        assert strategy.state == StrategyState.REGISTERED

    def test_load_transitions_to_loaded(self, strategy, config):
        strategy.load(config)
        assert strategy.state == StrategyState.LOADED

    def test_init_transitions_to_initialized(self, strategy, config):
        strategy.load(config)
        strategy.init()
        assert strategy.state == StrategyState.INITIALIZED

    def test_ready_transitions_to_ready(self, strategy, config):
        strategy.load(config)
        strategy.init()
        strategy.ready()
        assert strategy.state == StrategyState.READY

    def test_invalid_transition_raises(self, strategy):
        with pytest.raises(StrategyError):
            strategy.ready()    # REGISTERED → READY is invalid

    def test_pause_from_running(self, loaded_strategy, context):
        loaded_strategy.execute(context)   # → RUNNING → READY
        loaded_strategy.pause()
        assert loaded_strategy.state == StrategyState.PAUSED

    def test_resume_from_paused(self, loaded_strategy, context):
        loaded_strategy.pause()
        loaded_strategy.resume()
        assert loaded_strategy.state == StrategyState.RUNNING

    def test_fail_marks_failed(self, loaded_strategy):
        loaded_strategy.fail("test failure")
        assert loaded_strategy.state == StrategyState.FAILED

    def test_complete_from_ready(self, loaded_strategy):
        loaded_strategy.complete()
        assert loaded_strategy.state == StrategyState.COMPLETED


# ── Execute (pipeline) ────────────────────────────────────────────────────────

class TestBaseStrategyExecute:
    def test_execute_returns_plan(self, loaded_strategy, context):
        plan = loaded_strategy.execute(context)
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.signals) == len(context.symbols)

    def test_execute_increments_count(self, loaded_strategy, context):
        loaded_strategy.execute(context)
        assert loaded_strategy.execution_count == 1

    def test_execute_records_last_executed(self, loaded_strategy, context):
        assert loaded_strategy.last_executed is None
        loaded_strategy.execute(context)
        assert loaded_strategy.last_executed is not None

    def test_state_returns_to_ready_after_execute(self, loaded_strategy, context):
        loaded_strategy.execute(context)
        assert loaded_strategy.state == StrategyState.READY

    def test_execute_in_wrong_state_raises(self, strategy, context):
        with pytest.raises(StrategyError):
            strategy.execute(context)

    def test_empty_symbols_skips_cycle(self, loaded_strategy):
        ctx = make_context(symbols=[])
        plan = loaded_strategy.execute(ctx)
        assert plan is None

    def test_no_candidates_skips_cycle(self, descriptor, config, context):
        s = EmptyUniverseStrategy(descriptor)
        s.load(config); s.init(); s.ready()
        plan = s.execute(context)
        assert plan is None

    def test_reject_all_skips_cycle(self, descriptor, config, context):
        s = RejectAllStrategy(descriptor)
        s.load(config); s.init(); s.ready()
        plan = s.execute(context)
        assert plan is None

    def test_failing_strategy_goes_to_failed_state(
        self, descriptor, config, context
    ):
        s = FailingStrategy(descriptor)
        s.load(config); s.init(); s.ready()
        with pytest.raises(RuntimeError):
            s.execute(context)
        assert s.state == StrategyState.FAILED

    def test_invalid_inputs_skips_cycle(self, descriptor, config):
        s = InvalidInputStrategy(descriptor)
        s.load(config); s.init(); s.ready()
        ctx = make_context(symbols=["INFY"])
        plan = s.execute(ctx)
        assert plan is None

    def test_signal_count_accumulates(self, loaded_strategy, context):
        loaded_strategy.execute(context)
        loaded_strategy.execute(context)
        assert loaded_strategy.signal_count == len(context.symbols) * 2


# ── to_dict ───────────────────────────────────────────────────────────────────

class TestBaseStrategyToDict:
    def test_to_dict_keys(self, strategy):
        d = strategy.to_dict()
        assert all(k in d for k in [
            "strategy_id", "class", "state", "execution_count",
            "signal_count", "last_executed", "descriptor",
        ])

    def test_repr(self, strategy):
        r = repr(strategy)
        assert "test_strategy" in r
        assert "registered" in r
