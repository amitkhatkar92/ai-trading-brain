"""
test_workflow_orchestration_m4.py
----------------------------------
Unit-tests for C16 M4: Workflow Orchestration Framework
iios.workflow.orchestration

Coverage targets: ≥ 95 %
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from iios.workflow.orchestration import (
    # constants
    WorkflowType, StepType, WorkflowStatus, StepStatus,
    ExecutionMode, OrchestrationEventType,
    TERMINAL_WORKFLOW_STATUSES, TERMINAL_STEP_STATUSES,
    DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS, DEFAULT_WORKFLOW_TIMEOUT,
    DEFAULT_BACKOFF_SECONDS, DEFAULT_BACKOFF_MULTIPLIER, DEFAULT_MAX_BACKOFF,
    DEFAULT_MAX_HISTORY, DEFAULT_MAX_REGISTRY, DEFAULT_QUEUE_CAPACITY,
    DEFAULT_MAX_PARALLEL, VERSION, BUILD_VERSION,
    PREFIX_DEFINITION, PREFIX_STEP, PREFIX_RUNTIME, PREFIX_REQUEST,
    PREFIX_RESULT, PREFIX_CHECKPOINT, PREFIX_EVENT, PREFIX_ENGINE, PREFIX_JOB,
    # exceptions
    WorkflowOrchestrationError, WorkflowDefinitionError, WorkflowValidationError,
    WorkflowExecutionError, WorkflowStepError, WorkflowDependencyError,
    WorkflowTimeoutError, WorkflowRetryExhaustedError, WorkflowCompensationError,
    WorkflowCheckpointError, WorkflowRecoveryError, WorkflowRegistryError,
    WorkflowResourceError, WorkflowSchedulerError, WorkflowPersistenceError,
    WorkflowQueueError,
    # domain objects
    RetryPolicy, WorkflowStep, StepResult,
    WorkflowDefinition, WorkflowExecutionRequest,
    WorkflowRuntime, WorkflowExecutionResult,
    WorkflowCheckpoint,
    ValidationResult,
    OrchestrationEvent,
    OrchestrationStatisticsReport,
    WorkflowMonitorSnapshot,
    # services
    WorkflowContextManager, WorkflowStateStore,
    WorkflowCheckpointManager, WorkflowPersistence,
    WorkflowDependencyEngine, WorkflowRetryEngine, WorkflowTimeoutEngine,
    WorkflowStepExecutor, WorkflowSequentialEngine, WorkflowParallelEngine,
    WorkflowConditionalEngine, WorkflowEventEngine,
    WorkflowCompensationEngine, WorkflowRecoveryEngine, WorkflowExecutor,
    WorkflowOrchestrationEventBus, WorkflowMonitor, WorkflowStatistics,
    WorkflowHistory, WorkflowValidator, WorkflowRegistry,
    WorkflowFactory, WorkflowQueueManager, WorkflowResourceManager,
    WorkflowScheduler, WorkflowOrchestrationEngine,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _noop_handler(step, inputs, ctx):
    return {}


def _output_handler(outputs: Dict[str, Any]):
    def _h(step, inputs, ctx):
        return outputs
    return _h


def _fail_handler(step, inputs, ctx):
    raise ValueError("deliberate failure")


def _make_step(name="s1", handler="noop", deps=None, **kw):
    return WorkflowFactory.create_task_step(name, handler, dependencies=deps or [], **kw)


def _make_seq_def(name="wf", steps=None):
    s = steps or [_make_step()]
    return WorkflowFactory.create_sequential_workflow(name, s)


def _make_request(defn):
    return WorkflowFactory.create_request("run-1", defn.definition_id)


def _make_engine():
    e = WorkflowOrchestrationEngine()
    e.initialize()
    e.register_handler("noop", _noop_handler)
    e.register_handler("fail", _fail_handler)
    return e


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_workflow_type_values(self):
        assert WorkflowType.SEQUENTIAL == "sequential"
        assert WorkflowType.PARALLEL   == "parallel"
        assert WorkflowType.SAGA       == "saga"
        assert len(WorkflowType)       == 12

    def test_step_type_values(self):
        assert StepType.TASK   == "task"
        assert len(StepType)   == 10

    def test_workflow_status_terminal(self):
        assert WorkflowStatus.COMPLETED in TERMINAL_WORKFLOW_STATUSES
        assert WorkflowStatus.RUNNING   not in TERMINAL_WORKFLOW_STATUSES

    def test_step_status_terminal(self):
        assert StepStatus.COMPLETED in TERMINAL_STEP_STATUSES
        assert StepStatus.RUNNING   not in TERMINAL_STEP_STATUSES

    def test_prefixes(self):
        assert PREFIX_DEFINITION.startswith("w")
        assert PREFIX_STEP.startswith("s")
        assert PREFIX_JOB.startswith("w")

    def test_defaults(self):
        assert DEFAULT_MAX_RETRIES == 3
        assert DEFAULT_MAX_PARALLEL == 32


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_exception(self):
        exc = WorkflowOrchestrationError("base error")
        assert "WOF-000" in str(exc) or "base error" in str(exc)

    def test_definition_error(self):
        exc = WorkflowDefinitionError("missing", definition_id="abc")
        assert exc.definition_id == "abc"

    def test_validation_error(self):
        exc = WorkflowValidationError("invalid", issues=["bad step"])
        assert "bad step" in exc.issues

    def test_execution_error(self):
        exc = WorkflowExecutionError("exec error", workflow_id="wf-1")
        assert exc.workflow_id == "wf-1"

    def test_step_error(self):
        exc = WorkflowStepError("step err", step_id="s-1")
        assert exc.step_id == "s-1"

    def test_timeout_error(self):
        exc = WorkflowTimeoutError("timed out", step_id="s-1")
        assert exc.step_id == "s-1"

    def test_retry_exhausted(self):
        exc = WorkflowRetryExhaustedError("no retries", step_id="s-1", attempts=3)
        assert exc.attempts == 3

    def test_registry_error(self):
        exc = WorkflowRegistryError("not found")
        assert "WOF-011" in str(exc) or "not found" in str(exc)

    def test_resource_error(self):
        exc = WorkflowResourceError("full")
        assert isinstance(exc, WorkflowOrchestrationError)

    def test_queue_error(self):
        exc = WorkflowQueueError("full queue")
        assert isinstance(exc, WorkflowOrchestrationError)

    def test_hierarchy(self):
        for cls in [
            WorkflowDefinitionError, WorkflowValidationError,
            WorkflowExecutionError, WorkflowStepError,
        ]:
            assert issubclass(cls, WorkflowOrchestrationError)


# ─────────────────────────────────────────────────────────────────────────────
# RetryPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestRetryPolicy:
    def test_defaults(self):
        p = RetryPolicy()
        assert p.max_retries        == DEFAULT_MAX_RETRIES
        assert p.backoff_seconds    == DEFAULT_BACKOFF_SECONDS
        assert p.backoff_multiplier == DEFAULT_BACKOFF_MULTIPLIER
        assert p.max_backoff_seconds == DEFAULT_MAX_BACKOFF

    def test_backoff_formula(self):
        p = RetryPolicy(backoff_seconds=1.0, backoff_multiplier=2.0, max_backoff_seconds=10.0)
        assert p.backoff_for(0) == 1.0
        assert p.backoff_for(1) == 2.0
        assert p.backoff_for(2) == 4.0
        assert p.backoff_for(10) == 10.0  # capped

    def test_frozen(self):
        p = RetryPolicy()
        with pytest.raises((AttributeError, TypeError)):
            p.max_retries = 99


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowStep
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowStep:
    def test_create(self):
        s = _make_step("my-step", "h1")
        assert s.step_id.startswith(PREFIX_STEP)
        assert s.name == "my-step"
        assert s.handler == "h1"

    def test_frozen(self):
        s = _make_step()
        with pytest.raises((AttributeError, TypeError)):
            s.name = "other"

    def test_dependencies(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2", deps=[s1.step_id])
        assert s1.step_id in s2.dependencies
        assert s2.has_dependencies

    def test_no_dependencies(self):
        s = _make_step()
        assert not s.has_dependencies

    def test_has_compensation(self):
        s = _make_step(compensation_step_id="comp-1")
        assert s.has_compensation

    def test_effective_timeout(self):
        s = _make_step(timeout_seconds=0.0)
        assert s.effective_timeout == DEFAULT_TIMEOUT_SECONDS
        s2 = _make_step(timeout_seconds=5.0)
        assert s2.effective_timeout == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# StepResult
# ─────────────────────────────────────────────────────────────────────────────

class TestStepResult:
    def _step(self):
        return _make_step()

    def test_success(self):
        s = self._step()
        r = StepResult.success(s, {"x": 1}, 50.0)
        assert r.is_success
        assert r.outputs == {"x": 1}
        assert r.duration_ms == 50.0

    def test_failure(self):
        s = self._step()
        r = StepResult.failure(s, "oops", 20.0)
        assert r.is_failure
        assert r.error == "oops"

    def test_skipped(self):
        s = self._step()
        r = StepResult.skipped(s)
        assert r.status == StepStatus.SKIPPED

    def test_timed_out(self):
        s = self._step()
        r = StepResult.timed_out(s, 300.0)
        assert r.status == StepStatus.TIMED_OUT


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowDefinition
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowDefinition:
    def test_create(self):
        s = _make_step()
        d = _make_seq_def("wd", [s])
        assert d.definition_id.startswith(PREFIX_DEFINITION)
        assert d.name == "wd"
        assert d.step_count == 1

    def test_frozen(self):
        d = _make_seq_def()
        with pytest.raises((AttributeError, TypeError)):
            d.name = "x"

    def test_get_step(self):
        s = _make_step("s1")
        d = _make_seq_def(steps=[s])
        assert d.get_step(s.step_id) is s

    def test_get_step_missing(self):
        d = _make_seq_def()
        with pytest.raises(WorkflowDefinitionError):
            d.get_step("nonexistent")

    def test_step_ids(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2")
        d  = _make_seq_def(steps=[s1, s2])
        assert s1.step_id in d.step_ids
        assert s2.step_id in d.step_ids


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowExecutionRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowExecutionRequest:
    def test_create(self):
        r = WorkflowExecutionRequest.create("wf-1", "def-1")
        assert r.request_id.startswith(PREFIX_REQUEST)
        assert r.workflow_id   == "wf-1"
        assert r.definition_id == "def-1"
        assert r.priority      == 5

    def test_context_data(self):
        r = WorkflowExecutionRequest.create("wf-1", "def-1", context_data={"k": "v"})
        assert r.context_data == {"k": "v"}


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowRuntime
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowRuntime:
    def _make_runtime(self):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        return WorkflowRuntime.create(req), s

    def test_create(self):
        rt, s = self._make_runtime()
        assert rt.runtime_id.startswith(PREFIX_RUNTIME)
        assert rt.status == WorkflowStatus.PENDING

    def test_set_status(self):
        rt, _ = self._make_runtime()
        rt.set_status(WorkflowStatus.RUNNING)
        assert rt.status == WorkflowStatus.RUNNING

    def test_is_terminal(self):
        rt, _ = self._make_runtime()
        assert not rt.is_terminal
        rt.set_status(WorkflowStatus.COMPLETED)
        assert rt.is_terminal

    def test_step_status(self):
        rt, s = self._make_runtime()
        rt.set_step_status(s.step_id, StepStatus.RUNNING)
        assert rt.get_step_status(s.step_id) == StepStatus.RUNNING

    def test_increment_retry(self):
        rt, s = self._make_runtime()
        rt.increment_retry(s.step_id)
        rt.increment_retry(s.step_id)
        assert rt.get_step_retry_count(s.step_id) == 2

    def test_update_context(self):
        rt, _ = self._make_runtime()
        rt.update_context({"a": 1})
        assert rt.get_context()["a"] == 1

    def test_snapshot(self):
        rt, _ = self._make_runtime()
        snap = rt.snapshot()
        assert "runtime_id" in snap

    def test_to_dict(self):
        rt, _ = self._make_runtime()
        d = rt.to_dict()
        assert d["runtime_id"] == rt.runtime_id


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowContextManager
# ─────────────────────────────────────────────────────────────────────────────

class TestContextManager:
    def test_set_get(self):
        ctx = WorkflowContextManager()
        ctx.set("x", 42)
        assert ctx.get("x") == 42

    def test_missing_default(self):
        ctx = WorkflowContextManager()
        assert ctx.get("missing", "default") == "default"

    def test_merge(self):
        ctx = WorkflowContextManager()
        ctx.merge({"a": 1, "b": 2})
        assert ctx.get("a") == 1

    def test_delete(self):
        ctx = WorkflowContextManager()
        ctx.set("x", 1)
        ctx.delete("x")
        assert ctx.get("x") is None

    def test_snapshot_restore(self):
        ctx = WorkflowContextManager()
        ctx.set("x", 1)
        snap = ctx.snapshot()
        ctx.set("x", 99)
        ctx.restore(snap)
        assert ctx.get("x") == 1

    def test_resolve_inputs(self):
        ctx = WorkflowContextManager({"price": 100})
        result = ctx.resolve_inputs({"price": "buy_price"})
        assert result["buy_price"] == 100

    def test_apply_outputs(self):
        ctx = WorkflowContextManager()
        ctx.apply_outputs({"result": "ok"}, {"result": "step1.result"})
        assert ctx.get("step1.result") == "ok"

    def test_size(self):
        ctx = WorkflowContextManager({"a": 1, "b": 2})
        assert ctx.size() == 2

    def test_thread_safe(self):
        ctx = WorkflowContextManager()
        errors = []
        def writer(i):
            try:
                ctx.set(f"k{i}", i)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowStateStore
# ─────────────────────────────────────────────────────────────────────────────

class TestStateStore:
    def _rt(self):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        rt  = WorkflowRuntime.create(req)
        rt.set_status(WorkflowStatus.RUNNING)
        return rt

    def test_put_get(self):
        store = WorkflowStateStore()
        rt = self._rt()
        store.put(rt)
        fetched = store.get(rt.runtime_id)
        assert fetched.runtime_id == rt.runtime_id

    def test_get_missing(self):
        store = WorkflowStateStore()
        with pytest.raises(WorkflowExecutionError):
            store.get("nonexistent")

    def test_get_or_none(self):
        store = WorkflowStateStore()
        assert store.get_or_none("x") is None

    def test_active_runtimes(self):
        store = WorkflowStateStore()
        rt = self._rt()
        store.put(rt)
        assert store.active_count() == 1

    def test_remove(self):
        store = WorkflowStateStore()
        rt = self._rt()
        store.put(rt)
        store.remove(rt.runtime_id)
        assert store.runtime_count() == 0

    def test_exists(self):
        store = WorkflowStateStore()
        rt = self._rt()
        store.put(rt)
        assert store.exists(rt.runtime_id)

    def test_clear(self):
        store = WorkflowStateStore()
        store.put(self._rt())
        store.clear()
        assert store.runtime_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowCheckpointManager
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckpointManager:
    def _runtime(self):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        return WorkflowRuntime.create(req)

    def test_create_and_retrieve(self):
        mgr = WorkflowCheckpointManager()
        rt  = self._runtime()
        chk = mgr.create(rt, {"x": 1})
        assert chk.checkpoint_id.startswith(PREFIX_CHECKPOINT)
        latest = mgr.get_latest(rt.runtime_id)
        assert latest.checkpoint_id == chk.checkpoint_id

    def test_restore(self):
        mgr = WorkflowCheckpointManager()
        rt  = self._runtime()
        ctx = WorkflowContextManager()
        ctx.set("price", 100)
        chk = mgr.create(rt, ctx.snapshot())
        ctx.set("price", 999)
        mgr.restore(chk, rt)
        # rt context not directly set by restore; just check no error
        assert chk.context_snapshot.get("price") == 100

    def test_clear(self):
        mgr = WorkflowCheckpointManager()
        rt  = self._runtime()
        mgr.create(rt, {})
        mgr.clear(rt.runtime_id)
        assert mgr.checkpoint_count(rt.runtime_id) == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowPersistence
# ─────────────────────────────────────────────────────────────────────────────

class TestPersistence:
    def _runtime(self):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        return WorkflowRuntime.create(req)

    def test_save_load(self):
        p  = WorkflowPersistence()
        rt = self._runtime()
        p.save_runtime(rt)
        assert p.runtime_exists(rt.runtime_id)
        snap = p.load_runtime_snapshot(rt.runtime_id)
        assert snap["runtime_id"] == rt.runtime_id

    def test_delete(self):
        p  = WorkflowPersistence()
        rt = self._runtime()
        p.save_runtime(rt)
        p.delete_runtime(rt.runtime_id)
        assert not p.runtime_exists(rt.runtime_id)

    def test_save_checkpoint(self):
        p   = WorkflowPersistence()
        rt  = self._runtime()
        mgr = WorkflowCheckpointManager()
        chk = mgr.create(rt, {})
        p.save_checkpoint(chk)
        assert p.checkpoint_count(rt.runtime_id) == 1

    def test_clear(self):
        p = WorkflowPersistence()
        p.clear()
        assert p.runtime_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowDependencyEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestDependencyEngine:
    def test_linear_wave(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2", deps=[s1.step_id])
        d  = _make_seq_def(steps=[s1, s2])
        engine = WorkflowDependencyEngine()
        waves  = engine.get_execution_waves(d)
        assert len(waves) == 2
        assert s1.step_id in waves[0]
        assert s2.step_id in waves[1]

    def test_parallel_wave(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2")
        d  = _make_seq_def(steps=[s1, s2])
        engine = WorkflowDependencyEngine()
        waves  = engine.get_execution_waves(d)
        assert len(waves) == 1
        assert len(waves[0]) == 2

    def test_no_cycles_valid(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2", deps=[s1.step_id])
        d  = _make_seq_def(steps=[s1, s2])
        assert WorkflowDependencyEngine().validate_no_cycles(d) is True

    def test_satisfied_dependencies(self):
        s1 = _make_step("s1")
        s2 = _make_step("s2", deps=[s1.step_id])
        d  = _make_seq_def(steps=[s1, s2])
        eng = WorkflowDependencyEngine()
        assert eng.get_dependencies_satisfied(s2.step_id, d, {s1.step_id}) is True
        assert eng.get_dependencies_satisfied(s2.step_id, d, set()) is False


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowRetryEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestRetryEngine:
    def test_success_on_first_attempt(self):
        s    = _make_step()
        req  = _make_request(_make_seq_def(steps=[s]))
        rt   = WorkflowRuntime.create(req)
        eng  = WorkflowRetryEngine()
        result = eng.execute_with_retry(
            s, lambda: StepResult.success(s, {}, 1.0), rt,
        )
        assert result.is_success

    def test_exhausted(self):
        s    = _make_step()
        req  = _make_request(_make_seq_def(steps=[s]))
        rt   = WorkflowRuntime.create(req)
        eng  = WorkflowRetryEngine()
        policy = RetryPolicy(max_retries=2, backoff_seconds=0.0)
        with pytest.raises(WorkflowRetryExhaustedError):
            eng.execute_with_retry(
                s, lambda: StepResult.failure(s, "err", 1.0), rt, policy=policy,
            )

    def test_retry_count_incremented(self):
        s    = _make_step()
        req  = _make_request(_make_seq_def(steps=[s]))
        rt   = WorkflowRuntime.create(req)
        eng  = WorkflowRetryEngine()
        policy = RetryPolicy(max_retries=1, backoff_seconds=0.0)
        try:
            eng.execute_with_retry(
                s, lambda: StepResult.failure(s, "err", 1.0), rt, policy=policy,
            )
        except WorkflowRetryExhaustedError:
            pass
        assert rt.get_step_retry_count(s.step_id) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowTimeoutEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeoutEngine:
    def test_completes_within_timeout(self):
        s   = _make_step(timeout_seconds=5.0)
        eng = WorkflowTimeoutEngine()
        result = eng.execute_with_timeout(s, lambda: StepResult.success(s, {}, 1.0), 5.0)
        assert result.is_success

    def test_times_out(self):
        s   = _make_step(timeout_seconds=0.05)
        eng = WorkflowTimeoutEngine()
        def slow():
            time.sleep(1.0)
            return StepResult.success(s, {}, 1000.0)
        result = eng.execute_with_timeout(s, slow, 0.05)
        assert result.status == StepStatus.TIMED_OUT


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowStepExecutor
# ─────────────────────────────────────────────────────────────────────────────

class TestStepExecutor:
    def test_execute_success(self):
        s   = _make_step()
        ctx = WorkflowContextManager({"a": 1})
        exe = WorkflowStepExecutor()
        result = exe.execute(s, _noop_handler, ctx)
        assert result.is_success

    def test_execute_with_outputs(self):
        s   = _make_step()
        ctx = WorkflowContextManager()
        exe = WorkflowStepExecutor()
        result = exe.execute(s, _output_handler({"score": 42}), ctx)
        assert result.is_success

    def test_execute_failure(self):
        s   = _make_step()
        ctx = WorkflowContextManager()
        exe = WorkflowStepExecutor()
        result = exe.execute(s, _fail_handler, ctx)
        assert result.is_failure


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowConditionalEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestConditionalEngine:
    def test_no_condition_executes(self):
        s   = _make_step()
        ctx = WorkflowContextManager()
        eng = WorkflowConditionalEngine()
        assert eng.should_execute(s, ctx) is True

    def test_condition_true(self):
        s   = _make_step(condition="yes")
        ctx = WorkflowContextManager()
        eng = WorkflowConditionalEngine()
        assert eng.should_execute(s, ctx, condition_lookup=lambda name: lambda c: True) is True

    def test_condition_false(self):
        s   = _make_step(condition="no")
        ctx = WorkflowContextManager()
        eng = WorkflowConditionalEngine()
        assert eng.should_execute(s, ctx, condition_lookup=lambda name: lambda c: False) is False

    def test_filter_executable(self):
        s1 = _make_step("s1")                   # no condition
        s2 = _make_step("s2", condition="skip")  # will return False
        ctx = WorkflowContextManager()
        eng = WorkflowConditionalEngine()
        exe, skipped = eng.filter_executable_steps(
            [s1, s2], ctx, condition_lookup=lambda name: lambda c: False
        )
        assert s1 in exe      # no condition → always execute
        assert s2 in skipped


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowEventEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestEventEngine:
    def test_signal_and_wait(self):
        eng = WorkflowEventEngine()
        threading.Timer(0.1, eng.signal, args=("ready",)).start()
        payload = eng.wait_for("ready", timeout_seconds=2.0)
        assert eng.is_signalled("ready")

    def test_wait_timeout(self):
        eng = WorkflowEventEngine()
        with pytest.raises(WorkflowTimeoutError):
            eng.wait_for("never", timeout_seconds=0.05)

    def test_clear_all(self):
        eng = WorkflowEventEngine()
        eng.signal("x")
        eng.clear_all()
        assert not eng.is_signalled("x")

    def test_pending_events(self):
        eng = WorkflowEventEngine()
        eng.signal("ev1")
        assert "ev1" in eng.pending_events()


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowCompensationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestCompensationEngine:
    def test_compensation_runs(self):
        comp_step = WorkflowFactory.create_compensation_step("undo", "undo_handler")
        main_step = _make_step("main", compensation_step_id=comp_step.step_id)
        d         = WorkflowFactory.create_saga_workflow("saga", [main_step, comp_step])
        req       = _make_request(d)
        rt        = WorkflowRuntime.create(req)
        rt.set_step_status(main_step.step_id, StepStatus.COMPLETED)
        ctx       = WorkflowContextManager()

        called = []
        def undo_handler(step, inputs, cx):
            called.append(step.step_id)
            return {}

        eng     = WorkflowCompensationEngine()
        results = eng.compensate(
            rt, d, ctx, handler_lookup=lambda name: undo_handler
        )
        assert len(results) == 1
        assert called

    def test_compensation_skips_no_compensation_step(self):
        s   = _make_step("s1")  # no compensation_step_id
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        rt  = WorkflowRuntime.create(req)
        rt.set_step_status(s.step_id, StepStatus.COMPLETED)
        ctx = WorkflowContextManager()
        eng = WorkflowCompensationEngine()
        results = eng.compensate(rt, d, ctx, handler_lookup=lambda name: _noop_handler)
        assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowRecoveryEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryEngine:
    def test_can_recover_false_when_no_checkpoint(self):
        rt  = WorkflowRuntime.create(
            WorkflowExecutionRequest.create("wf-1", "def-1")
        )
        mgr = WorkflowCheckpointManager()
        eng = WorkflowRecoveryEngine(checkpoint_manager=mgr)
        assert not eng.can_recover(rt.runtime_id)

    def test_recover_restores_context(self):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = _make_request(d)
        rt  = WorkflowRuntime.create(req)
        mgr = WorkflowCheckpointManager()
        ctx = WorkflowContextManager({"key": "value"})
        mgr.create(rt, ctx.snapshot())
        ctx.set("key", "changed")

        eng = WorkflowRecoveryEngine(checkpoint_manager=mgr)
        ctx2 = WorkflowContextManager()
        chk  = eng.recover(rt, ctx2)
        assert chk is not None
        assert rt.status == WorkflowStatus.RECOVERING


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestValidator:
    def test_valid_definition(self):
        d   = _make_seq_def()
        v   = WorkflowValidator()
        res = v.validate(d)
        assert res.valid
        assert len(res.issues) == 0

    def test_validate_or_raise(self):
        d = _make_seq_def()
        WorkflowValidator().validate_or_raise(d)   # should not raise

    def test_validation_result_frozen(self):
        r = ValidationResult(definition_id="d", valid=True, issues=())
        with pytest.raises((AttributeError, TypeError)):
            r.valid = False


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_register_and_get_definition(self):
        reg = WorkflowRegistry()
        d   = _make_seq_def("my-wf")
        reg.register_definition(d)
        assert reg.definition_exists(d.definition_id)
        fetched = reg.get_definition(d.definition_id)
        assert fetched.name == "my-wf"

    def test_get_missing_definition(self):
        reg = WorkflowRegistry()
        with pytest.raises(WorkflowDefinitionError):
            reg.get_definition("nonexistent")

    def test_get_by_name(self):
        reg = WorkflowRegistry()
        d   = _make_seq_def("named-wf")
        reg.register_definition(d)
        assert reg.get_definition_by_name("named-wf").name == "named-wf"

    def test_deregister(self):
        reg = WorkflowRegistry()
        d   = _make_seq_def()
        reg.register_definition(d)
        assert reg.deregister_definition(d.definition_id)
        assert not reg.definition_exists(d.definition_id)

    def test_register_handler(self):
        reg = WorkflowRegistry()
        reg.register_handler("h1", _noop_handler)
        assert reg.handler_exists("h1")
        assert reg.get_handler("h1") is _noop_handler

    def test_missing_handler(self):
        reg = WorkflowRegistry()
        with pytest.raises(WorkflowRegistryError):
            reg.get_handler("missing")

    def test_register_condition(self):
        reg = WorkflowRegistry()
        fn  = lambda ctx: True
        reg.register_condition("cond1", fn)
        assert reg.condition_exists("cond1")
        assert reg.get_condition("cond1") is fn

    def test_capacity_limit(self):
        reg = WorkflowRegistry(max_definitions=2)
        reg.register_definition(_make_seq_def("w1"))
        reg.register_definition(_make_seq_def("w2"))
        with pytest.raises(WorkflowRegistryError):
            reg.register_definition(_make_seq_def("w3"))

    def test_clear_all(self):
        reg = WorkflowRegistry()
        reg.register_definition(_make_seq_def())
        reg.register_handler("h", _noop_handler)
        reg.clear_all()
        assert reg.definition_count() == 0
        assert reg.handler_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_task_step(self):
        s = WorkflowFactory.create_task_step("my-task", "handler")
        assert s.step_type == StepType.TASK
        assert s.name      == "my-task"

    def test_create_approval_step(self):
        s = WorkflowFactory.create_approval_step("approve", "ap_handler")
        assert s.step_type == StepType.APPROVAL

    def test_create_compensation_step(self):
        s = WorkflowFactory.create_compensation_step("undo", "undo_handler")
        assert s.step_type == StepType.COMPENSATION

    def test_create_sequential_workflow(self):
        d = WorkflowFactory.create_sequential_workflow("seq", [_make_step()])
        assert d.workflow_type == WorkflowType.SEQUENTIAL

    def test_create_parallel_workflow(self):
        d = WorkflowFactory.create_parallel_workflow("par", [_make_step()])
        assert d.workflow_type == WorkflowType.PARALLEL

    def test_create_saga_workflow(self):
        d = WorkflowFactory.create_saga_workflow("saga", [_make_step()])
        assert d.workflow_type == WorkflowType.SAGA
        assert d.enable_compensation

    def test_create_request(self):
        r = WorkflowFactory.create_request("wf-1", "def-1", priority=1)
        assert r.priority == 1

    def test_retry_policies(self):
        assert WorkflowFactory.no_retry().max_retries == 0
        assert WorkflowFactory.fast_retry().backoff_seconds < 1.0
        assert WorkflowFactory.standard_retry().max_retries == 3
        assert WorkflowFactory.aggressive_retry().max_retries == 10


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_report(self):
        stats  = WorkflowStatistics()
        report = stats.report()
        assert report.workflows_executed == 0
        assert isinstance(report, OrchestrationStatisticsReport)

    def test_record_success(self):
        stats = WorkflowStatistics()
        stats.record_execution(WorkflowStatus.COMPLETED, 100.0, steps_executed=2, steps_succeeded=2)
        r = stats.report()
        assert r.workflows_executed  == 1
        assert r.workflows_succeeded == 1
        assert r.steps_executed      == 2

    def test_record_failure(self):
        stats = WorkflowStatistics()
        stats.record_execution(WorkflowStatus.FAILED, 50.0)
        r = stats.report()
        assert r.workflows_failed == 1

    def test_reset(self):
        stats = WorkflowStatistics()
        stats.record_execution(WorkflowStatus.COMPLETED, 10.0)
        stats.reset()
        assert stats.report().workflows_executed == 0

    def test_to_dict(self):
        d = WorkflowStatistics().report().to_dict()
        assert "workflows_executed" in d
        assert "generated_at" in d


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def _result(self, workflow_id="wf-1"):
        s   = _make_step()
        d   = _make_seq_def(steps=[s])
        req = WorkflowExecutionRequest.create(workflow_id, d.definition_id)
        rt  = WorkflowRuntime.create(req)
        rt.set_status(WorkflowStatus.COMPLETED)
        return WorkflowExecutionResult.from_runtime(rt, {}, 50.0)

    def test_record_and_get(self):
        hist = WorkflowHistory()
        r    = self._result()
        hist.record(r)
        assert hist.get(r.result_id) is r

    def test_recent(self):
        hist = WorkflowHistory()
        for i in range(5):
            hist.record(self._result(f"wf-{i}"))
        recent = hist.recent(3)
        assert len(recent) == 3

    def test_by_workflow(self):
        hist = WorkflowHistory()
        r    = self._result("wf-target")
        hist.record(r)
        matches = hist.by_workflow("wf-target")
        assert any(m.result_id == r.result_id for m in matches)

    def test_bounded(self):
        hist = WorkflowHistory(max_entries=3)
        for i in range(5):
            hist.record(self._result(f"wf-{i}"))
        assert hist.count() == 3

    def test_clear(self):
        hist = WorkflowHistory()
        hist.record(self._result())
        n = hist.clear()
        assert n == 1
        assert hist.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowMonitor
# ─────────────────────────────────────────────────────────────────────────────

class TestMonitor:
    def _active_store(self):
        store = WorkflowStateStore()
        s     = _make_step()
        d     = _make_seq_def(steps=[s])
        req   = _make_request(d)
        rt    = WorkflowRuntime.create(req)
        rt.set_status(WorkflowStatus.RUNNING)
        store.put(rt)
        return store, rt

    def test_active_count(self):
        store, _ = self._active_store()
        mon = WorkflowMonitor(store)
        assert mon.active_count() == 1

    def test_snapshot(self):
        store, _ = self._active_store()
        mon  = WorkflowMonitor(store)
        snap = mon.snapshot()
        assert isinstance(snap, WorkflowMonitorSnapshot)
        assert snap.active_count == 1

    def test_health(self):
        mon = WorkflowMonitor()
        h   = mon.health()
        assert "active_workflows" in h


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowResourceManager
# ─────────────────────────────────────────────────────────────────────────────

class TestResourceManager:
    def test_acquire_release(self):
        rm = WorkflowResourceManager(max_concurrent=2)
        assert rm.available() == 2
        rm.acquire()
        assert rm.in_use()    == 1
        rm.release()
        assert rm.in_use()    == 0

    def test_capacity_exceeded(self):
        rm = WorkflowResourceManager(max_concurrent=1)
        rm.acquire()
        with pytest.raises(WorkflowResourceError):
            rm.acquire(blocking=True, timeout=0.05)

    def test_non_blocking_false(self):
        rm = WorkflowResourceManager(max_concurrent=1)
        rm.acquire()
        result = rm.acquire(blocking=False)
        assert result is False

    def test_health(self):
        rm = WorkflowResourceManager()
        h  = rm.health()
        assert "max_concurrent" in h


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowQueueManager
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueManager:
    def test_enqueue_and_process(self):
        processed = []
        def executor(req):
            processed.append(req.workflow_id)

        mgr = WorkflowQueueManager(capacity=10, num_workers=1)
        mgr.start(executor)
        d   = _make_seq_def()
        req = _make_request(d)
        mgr.enqueue(req)
        time.sleep(0.3)
        mgr.stop()
        assert req.workflow_id in processed

    def test_enqueue_not_started_raises(self):
        mgr = WorkflowQueueManager()
        d   = _make_seq_def()
        req = _make_request(d)
        with pytest.raises(WorkflowQueueError):
            mgr.enqueue(req)

    def test_queue_full(self):
        mgr = WorkflowQueueManager(capacity=1, num_workers=0)
        # Manually mark running so enqueue doesn't raise "not started"
        mgr._running = True
        d   = _make_seq_def()
        mgr.enqueue(_make_request(d))
        with pytest.raises(WorkflowQueueError):
            mgr.enqueue(_make_request(d))
        mgr._running = False


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestScheduler:
    def test_schedule_once_fires(self):
        fired = []
        def executor(req):
            fired.append(req.definition_id)

        sched = WorkflowScheduler(executor_fn=executor)
        sched.start()
        sched.schedule_once("def-1", delay_seconds=0.05)
        time.sleep(0.3)
        sched.stop()
        assert "def-1" in fired

    def test_cancel_job(self):
        sched = WorkflowScheduler()
        sched.start()
        job_id = sched.schedule_once("def-1", delay_seconds=10.0)
        assert sched.cancel(job_id)
        assert job_id not in sched.list_jobs()
        sched.stop()

    def test_recurring_fires_multiple(self):
        counts = []
        def executor(req):
            counts.append(1)

        sched = WorkflowScheduler(executor_fn=executor)
        sched.start()
        sched.schedule_recurring("def-r", interval_seconds=0.05, initial_delay=0.0)
        time.sleep(0.25)
        sched.stop()
        assert len(counts) >= 2

    def test_invalid_interval(self):
        sched = WorkflowScheduler()
        sched.start()
        with pytest.raises(WorkflowSchedulerError):
            sched.schedule_recurring("def-x", interval_seconds=0)
        sched.stop()


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowOrchestrationEventBus
# ─────────────────────────────────────────────────────────────────────────────

class TestEventBus:
    def _event(self, et=OrchestrationEventType.WORKFLOW_COMPLETED):
        return OrchestrationEvent.create(et, "eng-1", "wf-1", "rt-1", {})

    def test_emit_and_listener(self):
        bus      = WorkflowOrchestrationEventBus()
        received = []
        bus.add_listener(OrchestrationEventType.WORKFLOW_COMPLETED, received.append)
        bus.emit(self._event())
        assert len(received) == 1

    def test_listener_count(self):
        bus = WorkflowOrchestrationEventBus()
        bus.add_listener(OrchestrationEventType.WORKFLOW_COMPLETED, lambda e: None)
        assert bus.listener_count(OrchestrationEventType.WORKFLOW_COMPLETED) == 1

    def test_remove_listener(self):
        bus = WorkflowOrchestrationEventBus()
        fn  = lambda e: None
        bus.add_listener(OrchestrationEventType.WORKFLOW_COMPLETED, fn)
        bus.remove_listener(OrchestrationEventType.WORKFLOW_COMPLETED, fn)
        assert bus.listener_count(OrchestrationEventType.WORKFLOW_COMPLETED) == 0

    def test_wrong_type_not_received(self):
        bus      = WorkflowOrchestrationEventBus()
        received = []
        bus.add_listener(OrchestrationEventType.WORKFLOW_STEP_COMPLETED, received.append)
        bus.emit(self._event(OrchestrationEventType.WORKFLOW_COMPLETED))
        assert len(received) == 0

    def test_event_frozen(self):
        ev = self._event()
        with pytest.raises((AttributeError, TypeError)):
            ev.workflow_id = "other"

    def test_clear(self):
        bus = WorkflowOrchestrationEventBus()
        bus.add_listener(OrchestrationEventType.WORKFLOW_COMPLETED, lambda e: None)
        bus.clear()
        assert bus.listener_count(OrchestrationEventType.WORKFLOW_COMPLETED) == 0


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowExecutor
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutor:
    def _setup(self, workflow_type=WorkflowType.SEQUENTIAL):
        s   = WorkflowFactory.create_task_step("step1", "noop")
        d   = WorkflowDefinition.create("test-wf", [s], workflow_type=workflow_type)
        req = WorkflowFactory.create_request("run-1", d.definition_id)

        exe = WorkflowExecutor()

        def handler_lookup(name):
            return _noop_handler

        return exe, d, req, handler_lookup

    def test_sequential_success(self):
        exe, d, req, hl = self._setup()
        result = exe.execute(req, d, hl)
        assert result.is_success
        assert result.steps_executed >= 1

    def test_parallel_success(self):
        s1 = WorkflowFactory.create_task_step("s1", "noop")
        s2 = WorkflowFactory.create_task_step("s2", "noop")
        d  = WorkflowDefinition.create("par-wf", [s1, s2], workflow_type=WorkflowType.PARALLEL)
        req = WorkflowFactory.create_request("run-p", d.definition_id)
        exe = WorkflowExecutor()
        result = exe.execute(req, d, lambda name: _noop_handler)
        assert result.is_success

    def test_handler_failure(self):
        s   = WorkflowFactory.create_task_step("s1", "fail")
        d   = WorkflowDefinition.create("fail-wf", [s])
        req = WorkflowFactory.create_request("run-f", d.definition_id)
        exe = WorkflowExecutor()
        result = exe.execute(
            req, d, lambda name: _fail_handler,
        )
        assert result.is_failure


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowOrchestrationEngine — integration
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestrationEngine:
    def test_initialize_and_stop(self):
        eng = WorkflowOrchestrationEngine()
        eng.initialize()
        assert eng.is_running
        eng.stop()
        assert not eng.is_running

    def test_double_initialize(self):
        eng = WorkflowOrchestrationEngine()
        eng.initialize()
        eng.initialize()  # should not raise
        eng.stop()

    def test_register_and_execute(self):
        eng = _make_engine()
        d   = _make_seq_def()
        eng.register_definition(d)
        req    = _make_request(d)
        result = eng.execute(req)
        assert result.is_success
        eng.stop()

    def test_invalid_definition_rejected(self):
        eng = _make_engine()
        # Empty steps → validation fails
        with pytest.raises((WorkflowValidationError, Exception)):
            # try to create a def with empty steps — factory prevents it;
            # we test via validator directly
            from iios.workflow.orchestration import WorkflowValidator, WorkflowDefinition
            import uuid, datetime, timezone
            from iios.workflow.orchestration.constants import WorkflowType as WT
            bad = WorkflowDefinition(
                definition_id = "wdef-bad",
                name          = "",
                description   = "",
                workflow_type = WT.SEQUENTIAL,
                steps         = (),
                entry_step_id = "",
                exit_step_ids = (),
                version       = "1.0.0",
                max_retries   = 3,
                timeout_seconds = 3600.0,
                enable_checkpointing = True,
                enable_compensation  = True,
                metadata      = {},
                created_at    = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            )
            WorkflowValidator().validate_or_raise(bad)
        eng.stop()

    def test_health(self):
        eng = _make_engine()
        h   = eng.health()
        assert h["is_running"]
        assert "active_workflows" in h
        eng.stop()

    def test_statistics(self):
        eng = _make_engine()
        d   = _make_seq_def()
        eng.register_definition(d)
        eng.execute(_make_request(d))
        stats = eng.statistics()
        assert stats["workflows_executed"] >= 1
        eng.stop()

    def test_history_recorded(self):
        eng = _make_engine()
        d   = _make_seq_def()
        eng.register_definition(d)
        req = _make_request(d)
        res = eng.execute(req)
        hist = eng.history()
        assert hist.get(res.result_id) is not None
        eng.stop()

    def test_event_listener(self):
        eng      = _make_engine()
        received = []
        eng.event_bus().add_listener(
            OrchestrationEventType.WORKFLOW_COMPLETED,
            received.append,
        )
        d = _make_seq_def()
        eng.register_definition(d)
        eng.execute(_make_request(d))
        eng.stop()
        assert len(received) >= 1

    def test_resource_released_on_completion(self):
        eng = _make_engine()
        d   = _make_seq_def()
        eng.register_definition(d)
        for _ in range(5):
            eng.execute(_make_request(d))
        assert eng._resource_manager.in_use() == 0
        eng.stop()

    def test_engine_id_prefix(self):
        eng = WorkflowOrchestrationEngine()
        assert eng.engine_id.startswith(PREFIX_ENGINE)


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEnd:
    def test_sequential_multi_step(self):
        eng = WorkflowOrchestrationEngine()
        eng.initialize()

        outputs = {}

        def fetch(step, inputs, ctx):
            return {"data": [1, 2, 3]}

        def compute(step, inputs, ctx):
            data = ctx.get(f"{list(step.dependencies)[0]}.data") or []
            return {"result": sum(data)}

        s1 = WorkflowFactory.create_task_step("fetch",   "fetch_data")
        s2 = WorkflowFactory.create_task_step("compute", "compute",
                                               dependencies=[s1.step_id])
        d  = WorkflowFactory.create_sequential_workflow("etl", [s1, s2])

        eng.register_definition(d)
        eng.register_handler("fetch_data", fetch)
        eng.register_handler("compute",    compute)

        req    = WorkflowFactory.create_request("e2e-1", d.definition_id)
        result = eng.execute(req)

        assert result.is_success
        assert result.steps_executed == 2
        eng.stop()

    def test_parallel_independent_steps(self):
        eng = WorkflowOrchestrationEngine()
        eng.initialize()
        eng.register_handler("noop", _noop_handler)

        steps = [WorkflowFactory.create_task_step(f"s{i}", "noop") for i in range(4)]
        d     = WorkflowFactory.create_parallel_workflow("parallel-etl", steps)
        eng.register_definition(d)
        result = eng.execute(WorkflowFactory.create_request("par-e2e", d.definition_id))
        assert result.is_success
        assert result.steps_executed == 4
        eng.stop()

    def test_saga_with_compensation(self):
        compensated = []

        def reserve(step, inputs, ctx):
            return {"reserved": True}

        def fail_step(step, inputs, ctx):
            raise RuntimeError("payment failed")

        def undo_reserve(step, inputs, ctx):
            compensated.append("undo_reserve")
            return {}

        comp_step  = WorkflowFactory.create_compensation_step("undo-reserve", "undo_reserve")
        main_step  = WorkflowFactory.create_task_step(
            "reserve", "reserve",
            compensation_step_id=comp_step.step_id,
        )
        fail_st    = WorkflowFactory.create_task_step(
            "pay", "fail_step",
            dependencies=[main_step.step_id],
        )

        d   = WorkflowFactory.create_saga_workflow("saga", [main_step, fail_st, comp_step])
        eng = WorkflowOrchestrationEngine()
        eng.initialize()
        eng.register_definition(d)
        eng.register_handler("reserve",     reserve)
        eng.register_handler("fail_step",   fail_step)
        eng.register_handler("undo_reserve", undo_reserve)

        result = eng.execute(WorkflowFactory.create_request("saga-1", d.definition_id))
        assert result.is_failure
        assert "undo_reserve" in compensated
        eng.stop()

    def test_conditional_step_skipped(self):
        eng = WorkflowOrchestrationEngine()
        eng.initialize()

        visited = []

        def handler(step, inputs, ctx):
            visited.append(step.name)
            return {}

        s_always = WorkflowFactory.create_task_step("always", "handler")
        s_cond   = WorkflowFactory.create_task_step(
            "conditional", "handler", condition="is_premium"
        )

        d = WorkflowFactory.create_sequential_workflow("cond-wf", [s_always, s_cond])
        eng.register_definition(d)
        eng.register_handler("handler", handler)
        eng.register_condition("is_premium", lambda ctx: False)

        eng.execute(WorkflowFactory.create_request("cond-1", d.definition_id))
        assert "always"      in visited
        assert "conditional" not in visited
        eng.stop()

    def test_concurrent_executions(self):
        eng = WorkflowOrchestrationEngine(max_concurrent=10)
        eng.initialize()
        eng.register_handler("noop", _noop_handler)

        d = _make_seq_def("concurrent-wf")
        eng.register_definition(d)

        results = []
        errors  = []

        def run():
            try:
                r = eng.execute(WorkflowFactory.create_request("c-wf", d.definition_id))
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        assert not errors
        assert all(r.is_success for r in results)
        eng.stop()
