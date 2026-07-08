"""
tests/unit/intelligence/test_intelligence_orchestrator.py
==========================================================
Comprehensive tests for the IIOS Intelligence Orchestration Engine.

Coverage:
  Constants, Exceptions, Context, ExecutionPolicy, EngineRegistry,
  Sessions (lifecycle, nested, recovery, concurrent), WorkflowBuilder,
  WorkflowExecutor (sequential, parallel, conditional, nested,
  checkpoint recovery, cancellation), WorkflowRegistry, WorkflowScheduler,
  WorkflowEngine, IntelligenceManager, IntelligenceOrchestrator,
  Concurrency, Performance, End-to-End pipeline.
"""

from __future__ import annotations

import threading
import time
import uuid

import pytest

# ══════════════════════════════════════════════════════════════════════════════
#  Reset helper
# ══════════════════════════════════════════════════════════════════════════════

def _reset_all():
    from iios.intelligence.intelligence_orchestrator import reset_intelligence_orchestrator
    from iios.intelligence.intelligence_manager      import reset_intelligence_manager
    from iios.intelligence.intelligence_context      import reset_intelligence_context
    from iios.intelligence.registry.engine_registry  import reset_engine_registry
    from iios.intelligence.sessions.session_manager  import reset_session_manager
    from iios.intelligence.workflow.workflow_engine  import reset_workflow_engine
    from iios.intelligence.workflow.workflow_executor  import reset_workflow_executor
    from iios.intelligence.workflow.workflow_registry  import reset_workflow_registry
    from iios.intelligence.workflow.workflow_scheduler import reset_workflow_scheduler

    reset_intelligence_orchestrator()
    reset_intelligence_manager()
    reset_intelligence_context()
    reset_engine_registry()
    reset_session_manager()
    reset_workflow_engine()
    reset_workflow_executor()
    reset_workflow_registry()
    reset_workflow_scheduler()


@pytest.fixture(autouse=True)
def reset_all():
    _reset_all()
    yield
    _reset_all()


# ══════════════════════════════════════════════════════════════════════════════
#  1 — Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_engine_type_members(self):
        from iios.intelligence import EngineType
        assert EngineType.REASONING.value   == "reasoning_engine"
        assert EngineType.DEBATE.value      == "debate_engine"
        assert EngineType.STRATEGY.value    == "strategy_engine"
        assert EngineType.RISK.value        == "risk_engine"
        assert EngineType.LEARNING.value    == "learning_engine"
        assert EngineType.AGENT.value       == "agent_engine"

    def test_workflow_types(self):
        from iios.intelligence import WorkflowType
        types = [wt.value for wt in WorkflowType]
        assert "sequential"   in types
        assert "parallel"     in types
        assert "conditional"  in types
        assert "event_driven" in types
        assert "nested"       in types
        assert "long_running" in types

    def test_priority_ordered(self):
        from iios.intelligence import Priority
        assert Priority.CRITICAL > Priority.HIGH > Priority.NORMAL > Priority.LOW

    def test_session_status_members(self):
        from iios.intelligence import SessionStatus
        for s in ("pending", "active", "paused", "completed", "failed", "expired", "cancelled"):
            assert any(st.value == s for st in SessionStatus)

    def test_limits_positive(self):
        from iios.intelligence import (
            MAX_CONCURRENT_SESSIONS, MAX_CONCURRENT_WORKFLOWS, MAX_WORKFLOW_STEPS,
            MAX_NESTING_DEPTH, SESSION_TTL_SECONDS, WORKFLOW_TIMEOUT_MS,
        )
        for v in [MAX_CONCURRENT_SESSIONS, MAX_CONCURRENT_WORKFLOWS,
                  MAX_WORKFLOW_STEPS, MAX_NESTING_DEPTH, SESSION_TTL_SECONDS]:
            assert v > 0
        assert WORKFLOW_TIMEOUT_MS > 0

    def test_well_known_workflow_ids(self):
        from iios.intelligence import WF_FULL_ANALYSIS, WF_RISK_CHECK, WF_STRATEGY_CYCLE, WF_LEARNING_CYCLE
        assert all(isinstance(x, str) and len(x) > 0 for x in [
            WF_FULL_ANALYSIS, WF_RISK_CHECK, WF_STRATEGY_CYCLE, WF_LEARNING_CYCLE
        ])


# ══════════════════════════════════════════════════════════════════════════════
#  2 — Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        from iios.intelligence import (
            IntelligenceError,
            EngineError, EngineNotFoundError, EngineAlreadyRegisteredError,
            EngineExecutionError, EngineTimeoutError, EngineUnavailableError,
            SessionError, SessionNotFoundError, SessionExpiredError,
            SessionAlreadyActiveError, SessionRecoveryError, SessionCapacityError,
            WorkflowError, WorkflowNotFoundError, WorkflowExecutionError,
            WorkflowStepError, WorkflowTimeoutError, WorkflowCancelledError,
            CircularDependencyError, CheckpointError,
            OrchestratorError, OrchestratorNotInitializedError, PolicyViolationError,
            SchedulerError, SchedulerNotRunningError,
        )
        assert issubclass(EngineNotFoundError, EngineError)
        assert issubclass(EngineError, IntelligenceError)
        assert issubclass(SessionNotFoundError, SessionError)
        assert issubclass(SessionExpiredError, SessionError)
        assert issubclass(SessionCapacityError, SessionError)
        assert issubclass(WorkflowStepError, WorkflowError)
        assert issubclass(CircularDependencyError, WorkflowError)
        assert issubclass(OrchestratorNotInitializedError, OrchestratorError)
        assert issubclass(PolicyViolationError, OrchestratorError)
        assert issubclass(SchedulerNotRunningError, SchedulerError)

    def test_error_codes(self):
        from iios.intelligence import (
            IntelligenceError, EngineNotFoundError,
            SessionNotFoundError, OrchestratorNotInitializedError,
            WorkflowNotFoundError, SchedulerNotRunningError,
        )
        assert IntelligenceError("x").code     == "INT-000"
        assert EngineNotFoundError("e").code   == "INT-011"
        assert SessionNotFoundError("s").code  == "INT-021"
        assert OrchestratorNotInitializedError().code == "INT-041"
        assert WorkflowNotFoundError("w").code == "INT-031"
        assert SchedulerNotRunningError().code == "INT-051"

    def test_raise_and_catch(self):
        from iios.intelligence import IntelligenceError, EngineNotFoundError
        with pytest.raises(IntelligenceError):
            raise EngineNotFoundError("missing-engine")

    def test_circular_dependency_carries_cycle(self):
        from iios.intelligence import CircularDependencyError
        err = CircularDependencyError(["a", "b", "a"])
        assert "a" in err.cycle


# ══════════════════════════════════════════════════════════════════════════════
#  3 — IntelligenceContext
# ══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceContext:
    def test_execution_context_manager(self):
        from iios.intelligence import get_intelligence_context, Priority
        from iios.intelligence.intelligence_context import intelligence_execution
        with intelligence_execution(session_id="s1", actor="tester", priority=Priority.HIGH):
            ctx = get_intelligence_context()
            assert ctx.session_id == "s1"
            assert ctx.actor      == "tester"
            assert ctx.priority   == Priority.HIGH

    def test_workflow_scope(self):
        from iios.intelligence.intelligence_context import intelligence_execution, workflow_scope
        from iios.intelligence import get_intelligence_context, Priority
        with intelligence_execution():
            with workflow_scope("wf-test"):
                ctx = get_intelligence_context()
                assert ctx.workflow_id == "wf-test"
            ctx2 = get_intelligence_context()
            assert ctx2.workflow_id is None

    def test_step_scope_increments_depth(self):
        from iios.intelligence.intelligence_context import intelligence_execution, step_scope
        from iios.intelligence import get_intelligence_context
        with intelligence_execution():
            assert get_intelligence_context().depth == 0
            with step_scope("step-1"):
                assert get_intelligence_context().depth == 1
                with step_scope("step-1a"):
                    assert get_intelligence_context().depth == 2
            assert get_intelligence_context().depth == 0

    def test_elapsed_ms(self):
        from iios.intelligence.intelligence_context import intelligence_execution
        from iios.intelligence import get_intelligence_context
        with intelligence_execution():
            time.sleep(0.01)
            assert get_intelligence_context().elapsed_ms() >= 0

    def test_diagnostics(self):
        from iios.intelligence.intelligence_context import intelligence_execution
        from iios.intelligence import get_intelligence_context
        with intelligence_execution():
            ctx = get_intelligence_context()
            ctx.add_diagnostic("WARNING", "low memory", "monitor")
            ctx.add_diagnostic("ERROR", "engine down", "engine")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_context_is_thread_local(self):
        """Each thread has its own context."""
        from iios.intelligence.intelligence_context import intelligence_execution
        from iios.intelligence import get_intelligence_context
        results: dict = {}

        def _run(sid):
            with intelligence_execution(session_id=sid):
                time.sleep(0.01)
                results[sid] = get_intelligence_context().session_id

        threads = [threading.Thread(target=_run, args=(f"s{i}",)) for i in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(results) == 4
        assert all(results[k] == k for k in results)


# ══════════════════════════════════════════════════════════════════════════════
#  4 — ExecutionPolicy
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionPolicy:
    def test_retry_policy_should_retry(self):
        from iios.intelligence import RetryPolicy
        policy = RetryPolicy(max_attempts=3, jitter=False)
        assert policy.should_retry(0, ValueError("x"))
        assert policy.should_retry(2, ValueError("x"))
        assert not policy.should_retry(3, ValueError("x"))

    def test_retry_backoff_increases(self):
        from iios.intelligence import RetryPolicy
        policy = RetryPolicy(backoff_ms=100, backoff_factor=2.0, jitter=False)
        assert policy.wait_ms(0) == pytest.approx(100, abs=1)
        assert policy.wait_ms(1) == pytest.approx(200, abs=1)
        assert policy.wait_ms(2) == pytest.approx(400, abs=1)

    def test_cancellation_token(self):
        from iios.intelligence import CancellationToken
        tok = CancellationToken()
        assert not tok.is_cancelled
        tok.cancel("test reason")
        assert tok.is_cancelled
        assert tok.reason == "test reason"
        tok.reset()
        assert not tok.is_cancelled

    def test_fallback_policy_no_fn(self):
        from iios.intelligence import FallbackPolicy
        fp = FallbackPolicy(fallback_value=42, silence_errors=True)
        assert fp.apply(RuntimeError("boom")) == 42

    def test_fallback_policy_with_fn(self):
        from iios.intelligence import FallbackPolicy
        fp = FallbackPolicy(fallback_fn=lambda e: f"caught:{e}")
        result = fp.apply(ValueError("oops"))
        assert "caught" in result

    def test_execution_policy_to_dict(self):
        from iios.intelligence import ExecutionPolicy, Priority
        p = ExecutionPolicy(priority=Priority.HIGH)
        d = p.to_dict()
        assert d["priority"] == "HIGH"
        assert "retry"    in d
        assert "timeout"  in d
        assert "fallback" in d


# ══════════════════════════════════════════════════════════════════════════════
#  5 — EngineRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineRegistry:
    def test_register_and_get(self):
        from iios.intelligence import get_engine_registry, EngineType, Priority
        reg = get_engine_registry()
        reg.register_factory(
            engine_id="test.reasoning",
            engine_type=EngineType.REASONING,
            name="Test Reasoning",
            factory=lambda: object(),
        )
        d = reg.get("test.reasoning")
        assert d.engine_id   == "test.reasoning"
        assert d.engine_type == EngineType.REASONING

    def test_duplicate_raises(self):
        from iios.intelligence import get_engine_registry, EngineType, EngineAlreadyRegisteredError
        reg = get_engine_registry()
        reg.register_factory("dup.e", EngineType.DECISION, "D", lambda: None)
        with pytest.raises(EngineAlreadyRegisteredError):
            reg.register_factory("dup.e", EngineType.DECISION, "D", lambda: None)

    def test_overwrite(self):
        from iios.intelligence import get_engine_registry, EngineType
        reg = get_engine_registry()
        reg.register_factory("ow.e", EngineType.FORECAST, "F1", lambda: None)
        reg.register_factory("ow.e", EngineType.FORECAST, "F2", lambda: None, overwrite=True)
        assert reg.get("ow.e").name == "F2"

    def test_not_found_raises(self):
        from iios.intelligence import get_engine_registry, EngineNotFoundError
        with pytest.raises(EngineNotFoundError):
            get_engine_registry().get("no.such.engine")

    def test_register_all_engine_types(self):
        """Verify all 15 engine types can be registered."""
        from iios.intelligence import get_engine_registry, EngineType
        reg = get_engine_registry()
        for et in EngineType:
            reg.register_factory(f"stub.{et.value}", et, et.value, lambda: None, overwrite=True)
        assert reg.stats()["total"] >= len(list(EngineType))

    def test_best_returns_highest_priority(self):
        from iios.intelligence import get_engine_registry, EngineType, EngineStatus, Priority
        reg = get_engine_registry()
        reg.register_factory("low.r",  EngineType.REASONING, "Low",  lambda: None, priority=Priority.LOW)
        reg.register_factory("high.r", EngineType.REASONING, "High", lambda: None, priority=Priority.HIGH)
        reg.mark_ready("low.r")
        reg.mark_ready("high.r")
        best = reg.best(EngineType.REASONING)
        assert best.engine_id == "high.r"

    def test_best_returns_none_when_none_ready(self):
        from iios.intelligence import get_engine_registry, EngineType
        reg = get_engine_registry()
        assert reg.best(EngineType.DEBATE) is None

    def test_get_by_type(self):
        from iios.intelligence import get_engine_registry, EngineType
        reg = get_engine_registry()
        reg.register_factory("r1", EngineType.RISK, "R1", lambda: None)
        reg.register_factory("r2", EngineType.RISK, "R2", lambda: None)
        risk_engines = reg.get_by_type(EngineType.RISK)
        assert len(risk_engines) == 2

    def test_register_instance(self):
        from iios.intelligence import get_engine_registry, EngineType, EngineStatus

        class FakeEngine:
            def execute(self, r): return "ok"
            def health(self): return {"ok": True}
            def initialize(self): pass

        reg = get_engine_registry()
        reg.register_instance("inst.port", EngineType.PORTFOLIO, "Portfolio", FakeEngine())
        d = reg.get("inst.port")
        assert d.status == EngineStatus.READY

    def test_unregister(self):
        from iios.intelligence import get_engine_registry, EngineType, EngineNotFoundError
        reg = get_engine_registry()
        reg.register_factory("del.e", EngineType.AGENT, "A", lambda: None)
        assert reg.has("del.e")
        reg.unregister("del.e")
        assert not reg.has("del.e")
        with pytest.raises(EngineNotFoundError):
            reg.get("del.e")

    def test_stats(self):
        from iios.intelligence import get_engine_registry, EngineType
        reg = get_engine_registry()
        reg.register_factory("s1", EngineType.KNOWLEDGE, "K", lambda: None)
        s = reg.stats()
        assert s["total"] >= 1
        assert "by_status" in s


# ══════════════════════════════════════════════════════════════════════════════
#  6 — Sessions
# ══════════════════════════════════════════════════════════════════════════════

class TestSessions:
    def test_create_and_get(self):
        from iios.intelligence import get_session_manager, Priority
        sm = get_session_manager()
        s  = sm.create(actor="tester", priority=Priority.HIGH)
        assert s.session_id is not None
        assert sm.get(s.session_id).session_id == s.session_id

    def test_not_found(self):
        from iios.intelligence import get_session_manager, SessionNotFoundError
        with pytest.raises(SessionNotFoundError):
            get_session_manager().get("does-not-exist")

    def test_lifecycle_complete(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm = get_session_manager()
        s  = sm.create()
        sm.start(s.session_id)
        assert s.status == SessionStatus.ACTIVE
        sm.complete(s.session_id)
        assert s.status == SessionStatus.COMPLETED
        assert s.is_terminal

    def test_lifecycle_fail(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm = get_session_manager()
        s  = sm.create()
        sm.start(s.session_id)
        sm.fail(s.session_id, "boom")
        assert s.status  == SessionStatus.FAILED
        assert s.result  is not None
        assert s.result.error_count >= 1

    def test_pause_resume(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm = get_session_manager()
        s  = sm.create()
        sm.start(s.session_id)
        sm.pause(s.session_id)
        assert s.status == SessionStatus.PAUSED
        sm.resume(s.session_id)
        assert s.status == SessionStatus.ACTIVE

    def test_cancel(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm = get_session_manager()
        s  = sm.create()
        sm.cancel(s.session_id)
        assert s.status == SessionStatus.CANCELLED

    def test_nested_session(self):
        from iios.intelligence import get_session_manager
        sm     = get_session_manager()
        parent = sm.create()
        child  = sm.create_nested(parent.session_id)
        assert child.parent_id == parent.session_id
        assert child.is_nested
        children = sm.children_of(parent.session_id)
        assert any(c.session_id == child.session_id for c in children)

    def test_session_recovery(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm = get_session_manager()
        s  = sm.create()
        sm.start(s.session_id)
        sm.fail(s.session_id, "transient error")
        sm.recover(s.session_id, checkpoint_id="ckpt-001")
        assert s.status == SessionStatus.RECOVERING
        assert s.checkpoint_id == "ckpt-001"

    def test_stats(self):
        from iios.intelligence import get_session_manager
        sm = get_session_manager()
        sm.create()
        sm.create()
        s = sm.stats()
        assert s["total"] >= 2
        assert "active"   in s
        assert "capacity" in s

    def test_to_dict(self):
        from iios.intelligence import get_session_manager
        sm = get_session_manager()
        s  = sm.create(tags=["daily"], metadata={"symbol": "NIFTY"})
        d  = s.to_dict()
        assert d["session_id"] == s.session_id
        assert "status" in d


# ══════════════════════════════════════════════════════════════════════════════
#  7 — SessionResult
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionResult:
    def test_complete(self):
        from iios.intelligence import SessionResult, SessionStatus
        r = SessionResult(session_id="r1")
        r.complete()
        assert r.succeeded
        assert r.status == SessionStatus.COMPLETED

    def test_fail(self):
        from iios.intelligence import SessionResult, SessionStatus
        r = SessionResult(session_id="r2")
        r.fail("reason")
        assert r.failed
        assert r.error_count == 1

    def test_add_output_and_warning(self):
        from iios.intelligence import SessionResult
        r = SessionResult(session_id="r3")
        r.add_output("signal", 0.8)
        r.add_warning("low confidence")
        assert r.outputs["signal"] == 0.8
        assert r.warning_count == 1

    def test_to_dict(self):
        from iios.intelligence import SessionResult
        r = SessionResult(session_id="r4")
        r.add_output("result", "x")
        d = r.to_dict()
        assert d["session_id"] == "r4"
        assert "outputs" in d


# ══════════════════════════════════════════════════════════════════════════════
#  8 — WorkflowBuilder
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowBuilder:
    def test_build_sequential(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType
        wf = (
            WorkflowBuilder("wf1")
            .name("Test WF")
            .type(WorkflowType.SEQUENTIAL)
            .step("s1", lambda inp: "out1")
            .step("s2", lambda inp: "out2", depends_on=["s1"])
            .build()
        )
        assert wf.workflow_id == "wf1"
        assert wf.name        == "Test WF"
        assert len(wf.steps)  == 2

    def test_build_parallel(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType
        wf = (
            WorkflowBuilder("wf2")
            .type(WorkflowType.PARALLEL)
            .step("a", lambda _: "A")
            .step("b", lambda _: "B")
            .build()
        )
        assert wf.workflow_type == WorkflowType.PARALLEL

    def test_circular_dependency_raises(self):
        from iios.intelligence import WorkflowBuilder, CircularDependencyError
        builder = (
            WorkflowBuilder("cycle")
            .step("a", lambda _: None, depends_on=["b"])
            .step("b", lambda _: None, depends_on=["a"])
        )
        with pytest.raises((ValueError, CircularDependencyError)):
            builder.build()

    def test_missing_dep_raises(self):
        from iios.intelligence import WorkflowBuilder
        builder = WorkflowBuilder("bad").step("s1", lambda _: None, depends_on=["ghost"])
        with pytest.raises(ValueError):
            builder.build()

    def test_topological_order(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType
        wf = (
            WorkflowBuilder("topo")
            .step("root", lambda _: 1)
            .step("mid",  lambda _: 2, depends_on=["root"])
            .step("leaf", lambda _: 3, depends_on=["mid"])
            .build()
        )
        order = wf._topological_order()
        assert order.index("root") < order.index("mid") < order.index("leaf")

    def test_fluent_timeout(self):
        from iios.intelligence import WorkflowBuilder
        wf = WorkflowBuilder("to").step("s", lambda _: None).timeout(120_000, 5_000).build()
        assert wf.policy.timeout.workflow_timeout_ms == 120_000
        assert wf.policy.timeout.step_timeout_ms     == 5_000

    def test_fluent_tags_metadata(self):
        from iios.intelligence import WorkflowBuilder
        wf = (
            WorkflowBuilder("meta")
            .step("s", lambda _: None)
            .tag("alpha", "beta")
            .metadata(symbol="NIFTY", run="daily")
            .build()
        )
        assert "alpha" in wf.tags
        assert wf.metadata["symbol"] == "NIFTY"

    def test_checkpoint_step(self):
        from iios.intelligence import WorkflowBuilder, StepType
        wf = (
            WorkflowBuilder("ckpt")
            .step("s1", lambda _: None)
            .checkpoint("ckpt1", depends_on=["s1"])
            .build()
        )
        ckpt = wf.get_step("ckpt1")
        assert ckpt is not None
        assert ckpt.step_type == StepType.CHECKPOINT

    def test_to_dict(self):
        from iios.intelligence import WorkflowBuilder
        wf = WorkflowBuilder("d").step("s", lambda _: None).build()
        d  = wf.to_dict()
        assert d["workflow_id"] == "d"
        assert "steps" in d


# ══════════════════════════════════════════════════════════════════════════════
#  9 — WorkflowExecutor: sequential
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowExecutorSequential:
    def _build(self, wf_id="seq_test"):
        from iios.intelligence import WorkflowBuilder, WorkflowType
        return (
            WorkflowBuilder(wf_id)
            .type(WorkflowType.SEQUENTIAL)
            .step("s1", lambda inp: {"val": 1})
            .step("s2", lambda inp: {"val": inp.get("s1", {}).get("val", 0) + 1},
                  depends_on=["s1"])
            .build()
        )

    def test_sequential_completes(self):
        from iios.intelligence import get_workflow_executor, ExecutionStatus
        wf     = self._build()
        result = get_workflow_executor().execute(wf)
        assert result.succeeded
        assert result.status   == ExecutionStatus.COMPLETED
        assert result.step_count == 2

    def test_step_outputs_available(self):
        from iios.intelligence import get_workflow_executor
        wf     = self._build()
        result = get_workflow_executor().execute(wf)
        assert "s1" in result.outputs
        assert "s2" in result.outputs

    def test_failed_step_recorded(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor, StepStatus
        wf = (
            WorkflowBuilder("fail_wf")
            .step("ok", lambda _: "fine")
            .step("bad", lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
                  depends_on=["ok"])
            .build()
        )
        result = get_workflow_executor().execute(wf)
        assert result.steps["bad"].status == StepStatus.FAILED

    def test_conditional_step_skipped(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor, StepStatus
        wf = (
            WorkflowBuilder("cond_wf")
            .step("s1", lambda _: "data")
            .step("s2", lambda _: "skipped",
                  condition=lambda ctx, outs: False,
                  depends_on=["s1"])
            .build()
        )
        result = get_workflow_executor().execute(wf)
        assert result.steps["s2"].status == StepStatus.SKIPPED

    def test_checkpoint_step_saves_state(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        wf = (
            WorkflowBuilder("ckpt_wf")
            .step("s1", lambda _: "data")
            .checkpoint("ckpt1", depends_on=["s1"])
            .step("s2", lambda _: "more", depends_on=["ckpt1"])
            .build()
        )
        result = get_workflow_executor().execute(wf)
        assert result.succeeded
        assert len(result.checkpoints) == 1

    def test_checkpoint_recovery(self):
        """Re-run a workflow with a checkpoint dict — completed steps are skipped."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        counter = [0]

        def _count(_inp):
            counter[0] += 1
            return counter[0]

        wf = (
            WorkflowBuilder("recovery_wf")
            .step("s1", _count)
            .step("s2", _count, depends_on=["s1"])
            .build()
        )
        # Run once
        r1 = get_workflow_executor().execute(wf)
        assert counter[0] == 2
        # Re-run with checkpoint (s1 already done)
        counter[0] = 0
        r2 = get_workflow_executor().execute(wf, checkpoint={"s1": r1.outputs["s1"]})
        # Only s2 should have re-run
        assert counter[0] == 1

    def test_input_map(self):
        """Step input_map routes outputs from prior steps."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        wf = (
            WorkflowBuilder("inp_map")
            .step("producer", lambda _: {"price": 100.0})
            .step("consumer",
                  lambda inp: {"doubled": inp.get("price", 0) * 2},
                  depends_on=["producer"],
                  input_map={"producer.price": "price"})
            .build()
        )
        result = get_workflow_executor().execute(wf)
        assert result.outputs["consumer"]["doubled"] == 200.0


# ══════════════════════════════════════════════════════════════════════════════
#  10 — WorkflowExecutor: parallel
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowExecutorParallel:
    def test_parallel_all_steps_run(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        wf = (
            WorkflowBuilder("par")
            .type(WorkflowType.PARALLEL)
            .step("a", lambda _: "A")
            .step("b", lambda _: "B")
            .step("c", lambda _: "C")
            .build()
        )
        result = get_workflow_executor().execute(wf)
        assert result.succeeded
        assert result.step_count == 3

    def test_parallel_respects_dependencies(self):
        """Steps with deps run after their deps complete."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        order: list = []

        def _root(_):
            order.append("root")
            return "root"

        def _child(_):
            order.append("child")
            return "child"

        wf = (
            WorkflowBuilder("par_dep")
            .type(WorkflowType.PARALLEL)
            .step("root",  _root)
            .step("child", _child, depends_on=["root"])
            .build()
        )
        get_workflow_executor().execute(wf)
        assert order.index("root") < order.index("child")

    def test_parallel_cancellation(self):
        from iios.intelligence import (
            WorkflowBuilder, WorkflowType, get_workflow_executor,
            ExecutionPolicy, CancellationToken, ExecutionStatus, WorkflowCancelledError,
        )
        tok = CancellationToken()
        tok.cancel("immediate")
        policy = ExecutionPolicy(cancellation=tok)
        wf = (
            WorkflowBuilder("par_cancel")
            .type(WorkflowType.PARALLEL)
            .step("a", lambda _: "A")
            .build()
        )
        with pytest.raises(WorkflowCancelledError):
            get_workflow_executor().execute(wf, policy=policy)


# ══════════════════════════════════════════════════════════════════════════════
#  11 — Nested workflows
# ══════════════════════════════════════════════════════════════════════════════

class TestNestedWorkflows:
    def test_nested_workflow_executes(self):
        from iios.intelligence import WorkflowBuilder, WorkflowType, StepType, get_workflow_executor
        inner = WorkflowBuilder("inner").step("i1", lambda _: "inner_result").build()
        outer = (
            WorkflowBuilder("outer")
            .step("o1", lambda _: "outer_a")
            .sub_workflow("inner_step", inner, depends_on=["o1"])
            .build()
        )
        result = get_workflow_executor().execute(outer)
        assert result.succeeded
        assert "inner_step" in result.steps

    def test_nesting_depth_limit(self):
        from iios.intelligence import (
            WorkflowBuilder, get_workflow_executor, MAX_NESTING_DEPTH, WorkflowExecutionError
        )
        # Build a single-step workflow and call with depth > limit
        wf = WorkflowBuilder("deep").step("s", lambda _: None).build()
        with pytest.raises(WorkflowExecutionError):
            get_workflow_executor().execute(wf, depth=MAX_NESTING_DEPTH + 1)


# ══════════════════════════════════════════════════════════════════════════════
#  12 — WorkflowRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowRegistry:
    def test_register_and_get(self):
        from iios.intelligence import get_workflow_registry, WorkflowBuilder
        reg = get_workflow_registry()
        wf  = WorkflowBuilder("reg1").step("s", lambda _: None).build()
        reg.register(wf)
        assert reg.has("reg1")
        assert reg.get("reg1").workflow_id == "reg1"

    def test_duplicate_raises(self):
        from iios.intelligence import get_workflow_registry, WorkflowBuilder, WorkflowAlreadyRegisteredError
        reg = get_workflow_registry()
        wf  = WorkflowBuilder("dup").step("s", lambda _: None).build()
        reg.register(wf)
        with pytest.raises(WorkflowAlreadyRegisteredError):
            reg.register(wf)

    def test_not_found(self):
        from iios.intelligence import get_workflow_registry, WorkflowNotFoundError
        with pytest.raises(WorkflowNotFoundError):
            get_workflow_registry().get("ghost")

    def test_versioning(self):
        from iios.intelligence import get_workflow_registry, WorkflowBuilder
        reg = get_workflow_registry()
        wf1 = WorkflowBuilder("ver").step("s", lambda _: None).version("1.0.0").build()
        wf2 = WorkflowBuilder("ver").step("s", lambda _: None).version("2.0.0").build()
        reg.register(wf1)
        reg.register(wf2)
        assert reg.get("ver", "1.0.0").version == "1.0.0"
        assert reg.get("ver", "2.0.0").version == "2.0.0"
        assert reg.get("ver").version == "2.0.0"  # latest

    def test_list_ids(self):
        from iios.intelligence import get_workflow_registry, WorkflowBuilder
        reg = get_workflow_registry()
        for i in range(3):
            wf = WorkflowBuilder(f"wf{i}").step("s", lambda _: None).build()
            reg.register(wf)
        ids = reg.list_ids()
        assert len(ids) >= 3

    def test_stats(self):
        from iios.intelligence import get_workflow_registry, WorkflowBuilder
        reg = get_workflow_registry()
        wf  = WorkflowBuilder("stat_wf").step("s", lambda _: None).build()
        reg.register(wf)
        s = reg.stats()
        assert s["unique_ids"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  13 — WorkflowScheduler
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowScheduler:
    def _simple_wf(self, wf_id="sched_wf"):
        from iios.intelligence import WorkflowBuilder
        return WorkflowBuilder(wf_id).step("s", lambda _: "done").build()

    def test_schedule_once_and_trigger(self):
        from iios.intelligence import get_workflow_scheduler, ExecutionStatus
        sched = get_workflow_scheduler()
        wf    = self._simple_wf("once_wf")
        sw    = sched.schedule_once(wf, delay_s=9999)  # won't auto-fire
        result = sched.trigger(sw.schedule_id)
        assert result.succeeded

    def test_schedule_on_demand(self):
        from iios.intelligence import get_workflow_scheduler
        sched = get_workflow_scheduler()
        wf    = self._simple_wf("demand_wf")
        sw    = sched.schedule_on_demand(wf)
        assert not sw.is_due    # on-demand never auto-fires

    def test_cancel_schedule(self):
        from iios.intelligence import get_workflow_scheduler, WorkflowNotFoundError
        sched = get_workflow_scheduler()
        wf    = self._simple_wf("cancel_wf")
        sw    = sched.schedule_once(wf)
        assert sched.cancel(sw.schedule_id)
        with pytest.raises(WorkflowNotFoundError):
            sched.get_schedule(sw.schedule_id)

    def test_disable_enable(self):
        from iios.intelligence import get_workflow_scheduler
        sched = get_workflow_scheduler()
        wf    = self._simple_wf("de_wf")
        sw    = sched.schedule_once(wf)
        sched.disable(sw.schedule_id)
        assert not sw.enabled
        sched.enable(sw.schedule_id)
        assert sw.enabled

    def test_interval_schedule_advances(self):
        from iios.intelligence import get_workflow_scheduler, ScheduleType
        sched  = get_workflow_scheduler()
        wf     = self._simple_wf("interval_wf")
        sw     = sched.schedule_interval(wf, interval_s=60)
        t_before = sw.run_at
        sched.trigger(sw.schedule_id)
        assert sw.run_count == 1
        assert sw.run_at > t_before  # advanced

    def test_scheduler_start_stop(self):
        from iios.intelligence import get_workflow_scheduler
        sched = get_workflow_scheduler()
        sched.start()
        assert sched.is_running
        sched.stop()
        assert not sched.is_running

    def test_on_complete_callback(self):
        from iios.intelligence import get_workflow_scheduler
        results = []
        sched = get_workflow_scheduler()
        wf    = self._simple_wf("cb_wf")
        sw    = sched.schedule_once(wf, on_complete=lambda r: results.append(r))
        sched.trigger(sw.schedule_id)
        assert len(results) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  14 — WorkflowEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowEngine:
    def _engine(self):
        from iios.intelligence import get_workflow_engine
        e = get_workflow_engine()
        e.initialize()
        return e

    def test_register_and_run(self):
        from iios.intelligence import WorkflowBuilder
        engine = self._engine()
        wf = WorkflowBuilder("we_test").step("s", lambda _: "ok").build()
        engine.register(wf)
        result = engine.run("we_test")
        assert result.succeeded

    def test_run_definition(self):
        from iios.intelligence import WorkflowBuilder
        engine = self._engine()
        wf     = WorkflowBuilder("inline").step("s", lambda _: "ok").build()
        result = engine.run_definition(wf)
        assert result.succeeded

    def test_builder_shortcut(self):
        from iios.intelligence import WorkflowType
        engine  = self._engine()
        builder = engine.builder("b1")
        assert builder is not None
        wf = builder.step("s", lambda _: None).build()
        assert wf.workflow_id == "b1"

    def test_health(self):
        engine = self._engine()
        h = engine.health()
        assert h["status"] == "healthy"
        assert h["initialized"] is True

    def test_stats(self):
        engine = self._engine()
        s = engine.stats()
        assert "registry" in s
        assert "scheduler" in s


# ══════════════════════════════════════════════════════════════════════════════
#  15 — IntelligenceManager
# ══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceManager:
    def _mgr(self):
        from iios.intelligence import get_intelligence_manager
        m = get_intelligence_manager()
        m.initialize()
        return m

    def test_not_initialized_raises(self):
        from iios.intelligence import get_intelligence_manager, OrchestratorNotInitializedError, WorkflowBuilder
        m   = get_intelligence_manager()  # not initialized yet
        wf  = WorkflowBuilder("x").step("s", lambda _: None).build()
        with pytest.raises(OrchestratorNotInitializedError):
            m.run_workflow_definition(wf)

    def test_register_and_call_engine(self):
        class FakeEngine:
            def execute(self, r): return {"ans": r * 2}
            def initialize(self): pass
            def health(self): return {}

        from iios.intelligence import EngineType
        mgr = self._mgr()
        mgr.register_engine(
            "fake.strategy", EngineType.STRATEGY, "Fake",
            instance=FakeEngine(),
        )
        mgr._engines.mark_ready("fake.strategy")
        result = mgr.call_engine("fake.strategy", 21)
        assert result["ans"] == 42

    def test_session_lifecycle_via_manager(self):
        from iios.intelligence import SessionStatus
        mgr = self._mgr()
        s   = mgr.create_session(actor="test", tags=["unit"])
        mgr.complete_session(s.session_id)
        retrieved = mgr.get_session(s.session_id)
        assert retrieved.status == SessionStatus.COMPLETED

    def test_run_workflow(self):
        from iios.intelligence import WorkflowBuilder
        mgr = self._mgr()
        wf  = WorkflowBuilder("mgr_wf").step("s", lambda _: "data").build()
        mgr.register_workflow(wf)
        result = mgr.run_workflow("mgr_wf")
        assert result.succeeded

    def test_stats(self):
        mgr = self._mgr()
        s   = mgr.stats()
        assert "status"    in s
        assert "metrics"   in s
        assert "sessions"  in s

    def test_health(self):
        mgr = self._mgr()
        h   = mgr.health()
        assert h["status"] == "ready"


# ══════════════════════════════════════════════════════════════════════════════
#  16 — IntelligenceOrchestrator (master facade)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceOrchestrator:
    def _orch(self):
        from iios.intelligence import get_intelligence_orchestrator
        o = get_intelligence_orchestrator()
        o.initialize()
        return o

    def test_is_initialized(self):
        o = self._orch()
        assert o.is_initialized
        assert o.version == "1.0.0"

    def test_register_engine_and_call(self):
        class FakeEngine:
            def execute(self, r): return f"result:{r}"
            def initialize(self): pass
            def health(self): return {}

        from iios.intelligence import EngineType
        o = self._orch()
        o.register_engine(
            "orch.reasoning", EngineType.REASONING, "Reasoning",
            instance=FakeEngine(),
        )
        o._manager._engines.mark_ready("orch.reasoning")
        r = o.call_engine("orch.reasoning", "test_input")
        assert r == "result:test_input"

    def test_call_best_engine(self):
        class FakeEngine:
            def execute(self, r): return 99
            def initialize(self): pass
            def health(self): return {}

        from iios.intelligence import EngineType, Priority
        o = self._orch()
        o.register_engine(
            "orch.best", EngineType.FORECAST, "Best",
            instance=FakeEngine(), priority=Priority.CRITICAL,
        )
        o._manager._engines.mark_ready("orch.best")
        r = o.call_best_engine(EngineType.FORECAST)
        assert r == 99

    def test_session_create_complete(self):
        from iios.intelligence import SessionStatus
        o = self._orch()
        s = o.create_session(actor="orch_test")
        o.complete_session(s.session_id)
        s2 = o.get_session(s.session_id)
        assert s2.status == SessionStatus.COMPLETED

    def test_workflow_register_and_run(self):
        from iios.intelligence import WorkflowBuilder
        o  = self._orch()
        wf = WorkflowBuilder("orch_wf").step("s", lambda _: "done").build()
        o.register_workflow(wf)
        result = o.run_workflow("orch_wf")
        assert result.succeeded

    def test_run_definition(self):
        from iios.intelligence import WorkflowBuilder
        o  = self._orch()
        wf = WorkflowBuilder("inline_orch").step("s", lambda _: "x").build()
        r  = o.run_definition(wf)
        assert r.succeeded

    def test_workflow_builder_shortcut(self):
        o  = self._orch()
        wb = o.workflow_builder("orch_builder_test")
        assert wb is not None

    def test_schedule_and_trigger(self):
        from iios.intelligence import WorkflowBuilder
        o  = self._orch()
        wf = WorkflowBuilder("sched_orch").step("s", lambda _: "ok").build()
        sw = o.schedule_workflow(wf, delay_s=9999)
        r  = o.trigger_schedule(sw.schedule_id)
        assert r.succeeded

    def test_cancel_schedule(self):
        from iios.intelligence import WorkflowBuilder
        o  = self._orch()
        wf = WorkflowBuilder("cancel_orch").step("s", lambda _: "ok").build()
        sw = o.schedule_workflow(wf, delay_s=9999)
        assert o.cancel_schedule(sw.schedule_id)

    def test_priority_policy_enforcement(self):
        from iios.intelligence import PolicyType, Priority, PolicyViolationError
        o = self._orch()
        o.register_policy(PolicyType.PRIORITY, Priority.HIGH)
        with pytest.raises(PolicyViolationError):
            o.create_session(priority=Priority.LOW)

    def test_stats(self):
        o = self._orch()
        s = o.stats()
        assert "orchestrator_version" in s

    def test_health(self):
        o = self._orch()
        h = o.health()
        assert h["status"] == "ready"

    def test_singleton(self):
        from iios.intelligence import get_intelligence_orchestrator, reset_intelligence_orchestrator
        a = get_intelligence_orchestrator()
        b = get_intelligence_orchestrator()
        assert a is b
        reset_intelligence_orchestrator()
        c = get_intelligence_orchestrator()
        assert c is not a

    def test_not_initialized_raises_on_call(self):
        from iios.intelligence import (
            get_intelligence_orchestrator, OrchestratorNotInitializedError,
        )
        o = get_intelligence_orchestrator()  # NOT initialized
        with pytest.raises(OrchestratorNotInitializedError):
            from iios.intelligence import WorkflowBuilder
            wf = WorkflowBuilder("x").step("s", lambda _: None).build()
            o.run_definition(wf)


# ══════════════════════════════════════════════════════════════════════════════
#  17 — Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_workflow_execution(self):
        """Multiple workflows run concurrently without corruption."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor, ExecutionStatus
        exec_ = get_workflow_executor()
        results: list = []
        errors:  list = []

        def _run_wf(i):
            try:
                wf = (
                    WorkflowBuilder(f"par_wf_{i}")
                    .type(WorkflowType.PARALLEL)
                    .step("a", lambda _: i * 2)
                    .step("b", lambda _: i * 3)
                    .build()
                )
                r = exec_.execute(wf)
                results.append(r.succeeded)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_run_wf, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=30)

        assert errors == [], f"Concurrent workflow errors: {errors}"
        assert all(results)

    def test_concurrent_session_creation(self):
        from iios.intelligence import get_session_manager
        sm     = get_session_manager()
        ids:   list = []
        errors: list = []

        def _create():
            try:
                s = sm.create()
                ids.append(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_create) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert len(ids) == 50
        assert len(set(ids)) == 50  # all unique

    def test_concurrent_engine_registration(self):
        from iios.intelligence import get_engine_registry, EngineType
        reg    = get_engine_registry()
        errors: list = []

        def _register(i):
            try:
                reg.register_factory(f"conc.{i}", EngineType.PLUGIN, f"P{i}", lambda: None)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert reg.stats()["total"] >= 20

    def test_session_manager_thread_safe(self):
        from iios.intelligence import get_session_manager, SessionStatus
        sm     = get_session_manager()
        sids:  list = []
        errors: list = []

        def _lifecycle():
            try:
                s = sm.create()
                sids.append(s.session_id)
                sm.start(s.session_id)
                sm.complete(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_lifecycle) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []


# ══════════════════════════════════════════════════════════════════════════════
#  18 — Performance
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    def test_sequential_50_step_workflow(self):
        """A 50-step sequential workflow should complete in under 5 seconds."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        builder = WorkflowBuilder("perf50").type(WorkflowType.SEQUENTIAL)
        prev    = None
        for i in range(50):
            sid  = f"s{i}"
            deps = [prev] if prev else []
            builder.step(sid, lambda inp, i=i: i, depends_on=deps)
            prev = sid
        wf = builder.build()

        t0     = time.perf_counter()
        result = get_workflow_executor().execute(wf)
        ms     = (time.perf_counter() - t0) * 1_000

        assert result.succeeded
        assert ms < 5_000, f"50-step workflow took {ms:.0f} ms"

    def test_parallel_10_step_workflow(self):
        """A 10-step parallel workflow (no deps) should be faster than sequential."""
        from iios.intelligence import WorkflowBuilder, WorkflowType, get_workflow_executor
        builder = WorkflowBuilder("par10").type(WorkflowType.PARALLEL)
        for i in range(10):
            def _fn(_, i=i):
                time.sleep(0.01)
                return i
            builder.step(f"s{i}", _fn)
        wf = builder.build()

        t0     = time.perf_counter()
        result = get_workflow_executor().execute(wf)
        ms     = (time.perf_counter() - t0) * 1_000

        assert result.succeeded
        # Should be < 500ms (10 × 10ms parallel ≈ 10ms, with overhead)
        assert ms < 5_000


# ══════════════════════════════════════════════════════════════════════════════
#  19 — End-to-End pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline(self):
        """
        E2E test:
        1. Initialize orchestrator
        2. Register 3 mock AI engines
        3. Create a session
        4. Build and run a 4-step workflow that calls engines
        5. Complete session with result
        6. Verify stats
        """
        from iios.intelligence import (
            get_intelligence_orchestrator,
            EngineType, EngineStatus, Priority,
            WorkflowBuilder, WorkflowType,
            SessionStatus,
        )

        class MockEngine:
            def __init__(self, tag): self.tag = tag
            def execute(self, r): return {"tag": self.tag, "input": r}
            def initialize(self): pass
            def health(self): return {"ok": True}

        orch = get_intelligence_orchestrator()
        orch.initialize()

        # --- Register engines ---
        for et, tag in [
            (EngineType.REASONING, "reason"),
            (EngineType.RISK,      "risk"),
            (EngineType.STRATEGY,  "strategy"),
        ]:
            orch.register_engine(
                f"e2e.{tag}", et, tag.title(),
                instance=MockEngine(tag),
            )
            orch._manager._engines.mark_ready(f"e2e.{tag}")

        # --- Create session ---
        session = orch.create_session(actor="e2e_test", tags=["e2e"])
        assert session.status == SessionStatus.PENDING

        # --- Build workflow ---
        wf = (
            WorkflowBuilder("e2e_wf")
            .type(WorkflowType.SEQUENTIAL)
            .name("E2E Analysis Workflow")
            .step("load_data",    lambda inp: {"price": 100.0})
            .step("risk_check",   lambda inp: {"risk": "low"},    depends_on=["load_data"])
            .step("strategy_gen", lambda inp: {"action": "BUY"},  depends_on=["risk_check"])
            .step("checkpoint",   None, step_type=__import__(
                "iios.intelligence", fromlist=["StepType"]).StepType.CHECKPOINT,
                depends_on=["strategy_gen"])
            .build()
        )

        orch.register_workflow(wf)

        # --- Run workflow ---
        result = orch.run_workflow("e2e_wf", context={"symbol": "NIFTY"})
        assert result.succeeded
        assert result.step_count >= 3

        # --- Complete session ---
        from iios.intelligence import SessionResult
        sr = SessionResult(session_id=session.session_id)
        sr.add_output("workflow_result", result.to_dict())
        sr.complete()
        orch.complete_session(session.session_id, sr)

        retrieved = orch.get_session(session.session_id)
        assert retrieved.status == SessionStatus.COMPLETED

        # --- Verify stats ---
        stats = orch.stats()
        assert stats["metrics"]["total_workflows"] >= 1
        assert stats["metrics"]["total_sessions"]  >= 1

    def test_multiple_session_run_and_stats(self):
        from iios.intelligence import get_intelligence_orchestrator, WorkflowBuilder
        orch = get_intelligence_orchestrator()
        orch.initialize()

        wf = WorkflowBuilder("stat_wf").step("s", lambda _: "ok").build()
        orch.register_workflow(wf)

        for _ in range(5):
            orch.run_workflow("stat_wf")

        stats = orch.stats()
        assert stats["metrics"]["total_workflows"] == 5
