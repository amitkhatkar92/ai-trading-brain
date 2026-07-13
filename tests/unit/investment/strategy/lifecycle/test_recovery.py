"""tests/unit/investment/strategy/lifecycle/test_recovery.py
Tests for: CheckpointManager, FailureHandler, RestartManager, RecoveryEngine
"""
from __future__ import annotations

import time
import threading

import pytest

from iios.investment.strategy.lifecycle.checkpoint_manager import (
    Checkpoint,
    CheckpointManager,
)
from iios.investment.strategy.lifecycle.failure_handler import (
    CircuitState,
    FailureHandler,
    FailurePolicy,
    StrategyCircuit,
)
from iios.investment.strategy.lifecycle.restart_manager import (
    RestartManager,
    RestartPolicy,
)
from iios.investment.strategy.lifecycle.recovery_engine import (
    RecoveryDecision,
    RecoveryEngine,
)


# ── CheckpointManager ─────────────────────────────────────────────────────────

class TestCheckpointManager:
    def test_save_and_load_latest(self):
        cm = CheckpointManager()
        state = {"progress": 42, "data": [1, 2, 3]}
        ckpt = cm.save("s1", state, cycle_id="c1", label="after_phase_1")
        loaded = cm.load_latest("s1")
        assert loaded is ckpt
        assert loaded.state_snapshot["progress"] == 42

    def test_deep_copy_isolation(self):
        cm = CheckpointManager()
        state = {"x": 1}
        cm.save("s1", state)
        state["x"] = 99  # mutate original
        loaded = cm.load_latest("s1")
        assert loaded.state_snapshot["x"] == 1  # snapshot unaffected

    def test_load_latest_unknown_returns_none(self):
        cm = CheckpointManager()
        assert cm.load_latest("no-such") is None

    def test_load_by_id(self):
        cm = CheckpointManager()
        ckpt = cm.save("s1", {"v": 1})
        found = cm.load(ckpt.checkpoint_id)
        assert found is ckpt

    def test_load_by_unknown_id_returns_none(self):
        cm = CheckpointManager()
        assert cm.load("no-such-id") is None

    def test_per_strategy_limit(self):
        cm = CheckpointManager(max_per_strategy=3)
        for i in range(5):
            cm.save("s1", {"i": i})
        checkpoints = cm.list_checkpoints("s1")
        assert len(checkpoints) == 3

    def test_multiple_strategies(self):
        cm = CheckpointManager()
        cm.save("s1", {"a": 1})
        cm.save("s2", {"b": 2})
        assert cm.load_latest("s1").state_snapshot["a"] == 1
        assert cm.load_latest("s2").state_snapshot["b"] == 2

    def test_purge_strategy(self):
        cm = CheckpointManager()
        cm.save("s1", {"v": 1})
        cm.save("s1", {"v": 2})
        removed = cm.purge_strategy("s1")
        assert removed == 2
        assert cm.load_latest("s1") is None

    def test_checkpoint_count(self):
        cm = CheckpointManager()
        assert cm.checkpoint_count("s1") == 0
        cm.save("s1", {})
        assert cm.checkpoint_count("s1") == 1

    def test_known_strategy_ids(self):
        cm = CheckpointManager()
        cm.save("alpha", {})
        cm.save("beta", {})
        ids = cm.known_strategy_ids()
        assert "alpha" in ids
        assert "beta" in ids

    def test_to_dict_shape(self):
        cm = CheckpointManager()
        ckpt = cm.save("s1", {"x": 1}, label="test")
        d = ckpt.to_dict()
        assert "checkpoint_id" in d
        assert "strategy_id" in d
        assert "label" in d

    def test_thread_safe(self):
        cm = CheckpointManager(max_per_strategy=100, max_global=1000)
        errors = []

        def worker():
            try:
                for i in range(20):
                    cm.save(f"s{i % 5}", {"i": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ── StrategyCircuit ───────────────────────────────────────────────────────────

class TestStrategyCircuit:
    def test_initial_state_closed(self):
        policy = FailurePolicy(circuit_breaker_threshold=3)
        c = StrategyCircuit(policy)
        assert c.state == CircuitState.CLOSED
        assert c.is_open is False

    def test_opens_after_threshold(self):
        policy = FailurePolicy(circuit_breaker_threshold=3, circuit_reset_delay_s=9999)
        c = StrategyCircuit(policy)
        c.record_failure()
        c.record_failure()
        assert c.state == CircuitState.CLOSED
        c.record_failure()
        assert c.state == CircuitState.OPEN
        assert c.is_open is True

    def test_success_resets_to_closed(self):
        policy = FailurePolicy(circuit_breaker_threshold=2)
        c = StrategyCircuit(policy)
        c.record_failure()
        c.record_failure()
        assert c.state == CircuitState.OPEN
        c.record_success()
        assert c.state == CircuitState.CLOSED
        assert c.is_open is False


# ── FailureHandler ────────────────────────────────────────────────────────────

class TestFailureHandler:
    def test_should_retry_within_limit(self):
        fh = FailureHandler(FailurePolicy(max_retries=3))
        assert fh.should_retry("s1", "ValueError", attempt=0) is True
        assert fh.should_retry("s1", "ValueError", attempt=2) is True

    def test_should_not_retry_at_limit(self):
        fh = FailureHandler(FailurePolicy(max_retries=3))
        assert fh.should_retry("s1", "ValueError", attempt=3) is False

    def test_should_not_retry_non_retryable(self):
        policy = FailurePolicy(non_retryable_errors=["SystemExit"])
        fh = FailureHandler(policy)
        assert fh.should_retry("s1", "SystemExit", attempt=0) is False

    def test_retry_delay_exponential(self):
        policy = FailurePolicy(
            initial_retry_delay_s=1.0,
            backoff_factor=2.0,
            max_retry_delay_s=100.0,
        )
        fh = FailureHandler(policy)
        assert fh.retry_delay("s1", 0) == pytest.approx(1.0)
        assert fh.retry_delay("s1", 1) == pytest.approx(2.0)
        assert fh.retry_delay("s1", 2) == pytest.approx(4.0)

    def test_retry_delay_capped(self):
        policy = FailurePolicy(
            initial_retry_delay_s=1.0,
            backoff_factor=10.0,
            max_retry_delay_s=5.0,
        )
        fh = FailureHandler(policy)
        assert fh.retry_delay("s1", 5) == pytest.approx(5.0)

    def test_circuit_opens_and_blocks_retry(self):
        policy = FailurePolicy(circuit_breaker_threshold=2, max_retries=10)
        fh = FailureHandler(policy)
        fh.record_failure("s1", "Err", "msg", 0)
        fh.record_failure("s1", "Err", "msg", 1)
        assert fh.circuit_state("s1") == CircuitState.OPEN
        assert fh.should_retry("s1", "Err", attempt=2) is False

    def test_record_success_resets_circuit(self):
        policy = FailurePolicy(circuit_breaker_threshold=2)
        fh = FailureHandler(policy)
        fh.record_failure("s1", "Err", "msg", 0)
        fh.record_failure("s1", "Err", "msg", 1)
        fh.record_success("s1")
        assert fh.circuit_state("s1") == CircuitState.CLOSED

    def test_failure_history(self):
        fh = FailureHandler()
        fh.record_failure("s1", "TypeError", "type error", 0)
        fh.record_failure("s1", "ValueError", "value error", 1)
        history = fh.get_failure_history("s1")
        assert len(history) == 2

    def test_reset_strategy(self):
        fh = FailureHandler(FailurePolicy(circuit_breaker_threshold=2))
        fh.record_failure("s1", "Err", "msg", 0)
        fh.record_failure("s1", "Err", "msg", 1)
        fh.reset_strategy("s1")
        assert fh.circuit_state("s1") == CircuitState.CLOSED
        assert fh.get_failure_history("s1") == []

    def test_set_policy_per_strategy(self):
        fh = FailureHandler()
        custom_policy = FailurePolicy(max_retries=10)
        fh.set_policy("s1", custom_policy)
        assert fh.get_policy("s1").max_retries == 10

    def test_default_policy_fallback(self):
        fh = FailureHandler(FailurePolicy(max_retries=7))
        assert fh.get_policy("unknown").max_retries == 7


# ── RestartManager ────────────────────────────────────────────────────────────

class TestRestartManager:
    def test_never_policy(self):
        rm = RestartManager()
        rm.set_policy("s1", RestartPolicy.NEVER)
        assert rm.should_restart("s1", exit_was_failure=True) is False
        assert rm.should_restart("s1", exit_was_failure=False) is False

    def test_on_failure_policy(self):
        rm = RestartManager()
        rm.set_policy("s1", RestartPolicy.ON_FAILURE)
        assert rm.should_restart("s1", exit_was_failure=True) is True
        assert rm.should_restart("s1", exit_was_failure=False) is False

    def test_on_completion_policy(self):
        rm = RestartManager()
        rm.set_policy("s1", RestartPolicy.ON_COMPLETION)
        assert rm.should_restart("s1", exit_was_failure=False) is True
        assert rm.should_restart("s1", exit_was_failure=True) is False

    def test_always_policy(self):
        rm = RestartManager()
        rm.set_policy("s1", RestartPolicy.ALWAYS)
        assert rm.should_restart("s1", exit_was_failure=True) is True
        assert rm.should_restart("s1", exit_was_failure=False) is True

    def test_max_restarts_blocks(self):
        rm = RestartManager(max_restarts=2)
        rm.set_policy("s1", RestartPolicy.ALWAYS)
        rm.schedule_restart("s1", reason="test")
        rm.schedule_restart("s1", reason="test")
        assert rm.should_restart("s1", exit_was_failure=True) is False

    def test_restart_fn_called(self):
        restarted = []
        rm = RestartManager(restart_fn=lambda sid: restarted.append(sid))
        rm.set_policy("s1", RestartPolicy.ALWAYS)
        rm.schedule_restart("s1", reason="test")
        assert "s1" in restarted

    def test_restart_count(self):
        rm = RestartManager()
        assert rm.restart_count("s1") == 0
        rm.schedule_restart("s1", reason="test")
        assert rm.restart_count("s1") == 1

    def test_restart_history(self):
        rm = RestartManager()
        rm.schedule_restart("s1", reason="first", previous_status="failed")
        rm.schedule_restart("s1", reason="second")
        history = rm.restart_history("s1")
        assert len(history) == 2
        assert history[0].reason == "first"

    def test_reset_strategy(self):
        rm = RestartManager()
        rm.schedule_restart("s1", reason="test")
        rm.reset_strategy("s1")
        assert rm.restart_count("s1") == 0
        assert rm.restart_history("s1") == []

    def test_default_policy_never(self):
        rm = RestartManager()
        assert rm.get_policy("unknown") == RestartPolicy.NEVER


# ── RecoveryEngine ────────────────────────────────────────────────────────────

class TestRecoveryEngine:
    def test_save_and_load_checkpoint(self):
        eng = RecoveryEngine()
        ckpt = eng.save_checkpoint("s1", {"val": 42})
        loaded = eng.load_latest_checkpoint("s1")
        assert loaded is ckpt

    def test_handle_failure_retry(self):
        eng = RecoveryEngine(
            default_failure_policy=FailurePolicy(max_retries=3)
        )
        decision = eng.handle_failure("s1", "ValueError", "bad", attempt=0)
        assert decision.should_retry is True
        assert decision.retry_delay_s >= 0

    def test_handle_failure_max_retries_exceeded(self):
        eng = RecoveryEngine(
            default_failure_policy=FailurePolicy(max_retries=2)
        )
        decision = eng.handle_failure("s1", "ValueError", "bad", attempt=2)
        assert decision.should_retry is False

    def test_handle_failure_terminal(self):
        eng = RecoveryEngine()
        decision = eng.handle_failure(
            "s1", "Fatal", "crash", attempt=0, is_terminal_failure=True
        )
        assert decision.should_retry is False

    def test_handle_failure_includes_checkpoint(self):
        eng = RecoveryEngine()
        eng.save_checkpoint("s1", {"step": 3})
        decision = eng.handle_failure("s1", "Err", "msg", attempt=0)
        assert decision.checkpoint is not None

    def test_handle_success_resets_circuit(self):
        policy = FailurePolicy(circuit_breaker_threshold=2)
        eng = RecoveryEngine(default_failure_policy=policy)
        eng.handle_failure("s1", "Err", "msg", 0)
        eng.handle_failure("s1", "Err", "msg", 1)
        assert eng.circuit_state("s1") == CircuitState.OPEN
        eng.handle_success("s1")
        assert eng.circuit_state("s1") == CircuitState.CLOSED

    def test_handle_completion_no_restart(self):
        eng = RecoveryEngine()
        decision = eng.handle_completion("s1")
        assert decision is None

    def test_handle_completion_with_restart(self):
        restarted = []
        eng = RecoveryEngine(restart_fn=lambda sid: restarted.append(sid))
        eng.configure_strategy("s1", restart_policy=RestartPolicy.ON_COMPLETION)
        decision = eng.handle_completion("s1")
        assert decision is not None
        assert decision.should_restart is True
        assert "s1" in restarted

    def test_is_circuit_open(self):
        policy = FailurePolicy(circuit_breaker_threshold=1)
        eng = RecoveryEngine(default_failure_policy=policy)
        assert eng.is_circuit_open("s1") is False
        eng.handle_failure("s1", "Err", "msg", 0)
        assert eng.is_circuit_open("s1") is True

    def test_failure_history(self):
        eng = RecoveryEngine()
        eng.handle_failure("s1", "TypeError", "t", 0)
        history = eng.failure_history("s1")
        assert len(history) == 1

    def test_reset_strategy(self):
        eng = RecoveryEngine(
            default_failure_policy=FailurePolicy(circuit_breaker_threshold=1)
        )
        eng.save_checkpoint("s1", {"x": 1})
        eng.handle_failure("s1", "Err", "msg", 0)
        eng.reset_strategy("s1")
        assert eng.load_latest_checkpoint("s1") is None
        assert eng.is_circuit_open("s1") is False
        assert eng.failure_history("s1") == []

    def test_recovery_decision_to_dict(self):
        dec = RecoveryDecision("s1", should_retry=True, retry_delay_s=2.0)
        d = dec.to_dict()
        assert d["should_retry"] is True
        assert d["retry_delay_s"] == 2.0

    def test_configure_strategy_failure_policy(self):
        eng = RecoveryEngine()
        custom = FailurePolicy(max_retries=10)
        eng.configure_strategy("s1", failure_policy=custom)
        assert eng.failure_handler.get_policy("s1").max_retries == 10

    def test_configure_strategy_restart_policy(self):
        eng = RecoveryEngine()
        eng.configure_strategy("s1", restart_policy=RestartPolicy.ALWAYS)
        assert eng.restart_manager.get_policy("s1") == RestartPolicy.ALWAYS
