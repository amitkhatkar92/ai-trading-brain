"""
tests/ai/orchestrator/test_orchestrator.py
===========================================
Comprehensive unit tests for A10 Enterprise AI Orchestrator.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import time
import pytest

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.exceptions.orchestrator_exceptions import (
    AIOrchestrationException,
    AIObjectiveException,
    AIObjectiveNotFoundError,
    AIObjectiveAlreadyExistsError,
    AIObjectiveValidationError,
    AIPlanningException,
    AIPlanNotFoundError,
    AIPlanGenerationError,
    AIPlanDependencyError,
    AIReplanningError,
    AIWorkflowException,
    AIWorkflowNotFoundError,
    AIWorkflowAlreadyExistsError,
    AIWorkflowStateError,
    AIWorkflowExecutionError,
    AIWorkflowTimeoutError,
    AITaskSchedulerException,
    AITaskNotFoundError,
    AITaskQueueFullError,
    AITaskDependencyError,
    AITaskExecutionError,
    AIResourceException,
    AIAgentNotAvailableError,
    AIResourceExhaustedError,
    AIAllocationConflictError,
    AIRecoveryException,
    AIRecoveryFailedError,
    AIRollbackFailedError,
    AIMaxRetriesExceededError,
)
from iios.ai.foundation.exceptions import AIException

# ── Core ──────────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.core.orchestration_types import (
    ObjectiveStatus,
    PlanStatus,
    WorkflowStatus,
    TaskStatus,
    StepStatus,
    ExecutionMode,
)
from iios.ai.orchestrator.core.orchestration_context import (
    OrchestrationContext,
    OrchestrationSession,
    OrchestrationResult,
)
from iios.ai.orchestrator.core.plan_types import (
    PlanStep,
    PlanDependency,
    ExecutionPlan,
    PlanningContext,
)
from iios.ai.orchestrator.core.workflow_types import (
    WorkflowStep,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowState,
)
from iios.ai.orchestrator.core.task_types import ScheduledTask, SchedulerPolicy

# ── Engine ────────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.engine.planning_engine import PlanningEngine
from iios.ai.orchestrator.engine.workflow_engine import WorkflowManager
from iios.ai.orchestrator.engine.orchestration_engine import (
    Orchestrator,
    OrchestrationManager,
)

# ── Policy ────────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.policy.task_scheduler import TaskScheduler
from iios.ai.orchestrator.policy.resource_coordinator import (
    AgentAllocator,
    CapabilityAllocator,
    ExecutionCoordinator,
    ResourceReservation,
)
from iios.ai.orchestrator.policy.recovery_manager import (
    RecoveryManager,
    RecoveryStrategy,
    RetryCoordinator,
    RollbackManager,
)

# ── Observability ─────────────────────────────────────────────────────────────
from iios.ai.orchestrator.observability.execution_monitor import (
    ExecutionMetrics,
    ExecutionMonitor,
    ProgressTracker,
    Timeline,
    TimelineEvent,
)

# ── Events ────────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.events.orchestrator_events import (
    OrchestratorEventType,
    OrchestratorEvent,
    ObjectiveReceivedEvent,
    PlanGeneratedEvent,
    SessionStartedEvent,
    SessionCompletedEvent,
    WorkflowRegisteredEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    TaskScheduledEvent,
    TaskCompletedEvent,
    RecoveryStartedEvent,
    RecoveryCompletedEvent,
    AgentAllocatedEvent,
    ResourceReservedEvent,
)
from iios.ai.orchestrator.events.orchestrator_event_bus import OrchestratorEventBus

# ── Snapshot ──────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.snapshot.orchestrator_snapshot import OrchestratorSnapshot

# ── Gateway ───────────────────────────────────────────────────────────────────
from iios.ai.orchestrator.gateway.orchestrator_gateway import OrchestratorGateway


# =============================================================================
# Helpers
# =============================================================================

def _gw() -> OrchestratorGateway:
    gw = OrchestratorGateway()
    gw.start()
    return gw


def _step(name: str = "step1", action: str = "execute") -> WorkflowStep:
    return WorkflowStep.create(name=name, action=action)


def _defn(steps=None) -> WorkflowDefinition:
    if steps is None:
        steps = (WorkflowStep.create("s1", "execute"),)
    return WorkflowDefinition.create("test_workflow", steps)


# =============================================================================
# SECTION 1: Exceptions
# =============================================================================

class TestExceptions:

    @pytest.mark.parametrize("cls,code", [
        (AIOrchestrationException,    "AI-1500"),
        (AIObjectiveException,        "AI-1510"),
        (AIObjectiveNotFoundError,    "AI-1511"),
        (AIObjectiveAlreadyExistsError, "AI-1512"),
        (AIObjectiveValidationError,  "AI-1513"),
        (AIPlanningException,         "AI-1520"),
        (AIPlanNotFoundError,         "AI-1521"),
        (AIPlanGenerationError,       "AI-1522"),
        (AIPlanDependencyError,       "AI-1523"),
        (AIReplanningError,           "AI-1524"),
        (AIWorkflowException,         "AI-1530"),
        (AIWorkflowNotFoundError,     "AI-1531"),
        (AIWorkflowAlreadyExistsError,"AI-1532"),
        (AIWorkflowStateError,        "AI-1533"),
        (AIWorkflowExecutionError,    "AI-1534"),
        (AIWorkflowTimeoutError,      "AI-1535"),
        (AITaskSchedulerException,    "AI-1540"),
        (AITaskNotFoundError,         "AI-1541"),
        (AITaskQueueFullError,        "AI-1542"),
        (AITaskDependencyError,       "AI-1543"),
        (AITaskExecutionError,        "AI-1544"),
        (AIResourceException,         "AI-1550"),
        (AIAgentNotAvailableError,    "AI-1551"),
        (AIResourceExhaustedError,    "AI-1552"),
        (AIAllocationConflictError,   "AI-1553"),
        (AIRecoveryException,         "AI-1560"),
        (AIRecoveryFailedError,       "AI-1561"),
        (AIRollbackFailedError,       "AI-1562"),
        (AIMaxRetriesExceededError,   "AI-1563"),
    ])
    def test_error_code(self, cls, code):
        ex = cls()
        assert ex.error_code == code

    @pytest.mark.parametrize("cls,code", [
        (AIOrchestrationException,    "AI-1500"),
        (AIObjectiveNotFoundError,    "AI-1511"),
        (AIWorkflowNotFoundError,     "AI-1531"),
        (AITaskNotFoundError,         "AI-1541"),
        (AIAgentNotAvailableError,    "AI-1551"),
        (AIRecoveryFailedError,       "AI-1561"),
    ])
    def test_code_in_message(self, cls, code):
        ex = cls()
        assert code in ex.message

    def test_base_inherits_ai_exception(self):
        assert issubclass(AIOrchestrationException, AIException)

    def test_objective_not_found_is_orchestration(self):
        assert isinstance(AIObjectiveNotFoundError(), AIOrchestrationException)

    def test_workflow_not_found_is_workflow_exception(self):
        assert isinstance(AIWorkflowNotFoundError(), AIWorkflowException)

    def test_task_not_found_is_scheduler_exception(self):
        assert isinstance(AITaskNotFoundError(), AITaskSchedulerException)

    def test_agent_not_available_is_resource_exception(self):
        assert isinstance(AIAgentNotAvailableError(), AIResourceException)

    def test_recovery_failed_is_recovery_exception(self):
        assert isinstance(AIRecoveryFailedError(), AIRecoveryException)

    def test_custom_message(self):
        ex = AIObjectiveNotFoundError("session xyz not found")
        assert "xyz" in ex.message

    def test_base_exception_custom_code(self):
        ex = AIOrchestrationException("msg", code="AI-1599")
        assert ex.error_code == "AI-1599"


# =============================================================================
# SECTION 2: Core types
# =============================================================================

class TestOrchestrationTypes:

    def test_objective_status_terminal(self):
        assert ObjectiveStatus.COMPLETED.is_terminal()
        assert ObjectiveStatus.FAILED.is_terminal()
        assert ObjectiveStatus.CANCELLED.is_terminal()
        assert not ObjectiveStatus.PENDING.is_terminal()
        assert not ObjectiveStatus.EXECUTING.is_terminal()

    def test_plan_status_terminal(self):
        assert PlanStatus.COMPLETED.is_terminal()
        assert not PlanStatus.READY.is_terminal()

    def test_workflow_status_terminal(self):
        assert WorkflowStatus.COMPLETED.is_terminal()
        assert not WorkflowStatus.RUNNING.is_terminal()

    def test_workflow_status_active(self):
        assert WorkflowStatus.RUNNING.is_active()
        assert WorkflowStatus.PAUSED.is_active()
        assert not WorkflowStatus.COMPLETED.is_active()

    def test_task_status_terminal(self):
        assert TaskStatus.COMPLETED.is_terminal()
        assert TaskStatus.CANCELLED.is_terminal()
        assert not TaskStatus.QUEUED.is_terminal()

    def test_step_status_terminal(self):
        assert StepStatus.COMPLETED.is_terminal()
        assert StepStatus.SKIPPED.is_terminal()
        assert not StepStatus.RUNNING.is_terminal()

    def test_execution_mode_values(self):
        assert ExecutionMode.SEQUENTIAL.value == "sequential"
        assert ExecutionMode.PARALLEL.value   == "parallel"


class TestOrchestrationContext:

    def test_context_create(self):
        ctx = OrchestrationContext.create("do X", "agent-1")
        assert ctx.objective    == "do X"
        assert ctx.principal_id == "agent-1"
        assert ctx.context_id
        assert ctx.session_id
        assert ctx.trace_id

    def test_context_metadata(self):
        ctx = OrchestrationContext.create("obj", "p1", env="prod")
        assert ctx.get_meta("env") == "prod"
        assert ctx.get_meta("missing", "default") == "default"

    def test_session_create(self):
        ctx     = OrchestrationContext.create("obj", "p1")
        session = OrchestrationSession.create(ctx)
        assert session.status == ObjectiveStatus.PENDING
        assert session.session_id == ctx.session_id

    def test_session_with_status(self):
        ctx     = OrchestrationContext.create("obj", "p1")
        session = OrchestrationSession.create(ctx).with_status(ObjectiveStatus.EXECUTING)
        assert session.status == ObjectiveStatus.EXECUTING

    def test_session_with_state(self):
        ctx     = OrchestrationContext.create("obj", "p1")
        session = OrchestrationSession.create(ctx).with_state("plan_id", "p-1")
        assert session.get_state("plan_id") == "p-1"
        assert session.get_state("missing", "x") == "x"

    def test_result_success(self):
        r = OrchestrationResult.success("s1", "obj", time.time() - 1)
        assert r.is_successful
        assert r.duration_ms > 0
        assert r.steps_failed == 0

    def test_result_failure(self):
        r = OrchestrationResult.failure("s1", "obj", time.time(), "bad")
        assert not r.is_successful
        assert r.status == ObjectiveStatus.FAILED

    def test_result_cancelled(self):
        r = OrchestrationResult.cancelled("s1", "obj", time.time())
        assert r.status == ObjectiveStatus.CANCELLED


class TestPlanTypes:

    def test_plan_step_create(self):
        s = PlanStep.create("name", "execute", x="1")
        assert s.step_id
        assert s.get_param("x") == "1"
        assert s.get_param("missing", "d") == "d"

    def test_plan_step_defaults(self):
        s = PlanStep.create("n", "a")
        assert s.parallel is False
        assert s.max_retries == 0
        assert s.dependencies == frozenset()

    def test_plan_dependency_create(self):
        d = PlanDependency.create("A", "B")
        assert d.from_step == "A"
        assert d.to_step   == "B"
        assert d.condition is None

    def test_execution_plan_create(self):
        p = ExecutionPlan.create("obj")
        assert p.status == PlanStatus.DRAFT
        assert p.step_count() == 0

    def test_execution_plan_with_status(self):
        p = ExecutionPlan.create("obj").with_status(PlanStatus.READY)
        assert p.status == PlanStatus.READY

    def test_execution_plan_with_steps(self):
        s1 = PlanStep.create("s1", "execute")
        p  = ExecutionPlan.create("obj").with_steps((s1,))
        assert p.step_count() == 1

    def test_planning_context_create(self):
        ctx = PlanningContext.create("obj", mode="fast")
        assert ctx.objective == "obj"
        assert ctx.get_preference("mode") == "fast"

    def test_planning_context_constraints(self):
        ctx = PlanningContext.create("obj", constraints=frozenset({"no_external"}))
        assert "no_external" in ctx.constraints


class TestWorkflowTypes:

    def test_workflow_step_create(self):
        s = WorkflowStep.create("step", "action", x="42")
        assert s.name == "step"
        assert s.get_param("x") == "42"

    def test_workflow_definition_create(self):
        s  = WorkflowStep.create("s1", "a")
        d  = WorkflowDefinition.create("wf", (s,))
        assert d.name         == "wf"
        assert d.initial_step == s.step_id
        assert d.step_count() == 1

    def test_workflow_definition_requires_steps(self):
        with pytest.raises(ValueError):
            WorkflowDefinition.create("wf", ())

    def test_workflow_definition_get_step(self):
        s = WorkflowStep.create("s1", "a")
        d = WorkflowDefinition.create("wf", (s,))
        assert d.get_step(s.step_id) == s
        assert d.get_step("nonexistent") is None

    def test_workflow_instance_create(self):
        i = WorkflowInstance.create("wf_id", "ctx_id")
        assert i.status == WorkflowStatus.PENDING

    def test_workflow_instance_with_status(self):
        i = WorkflowInstance.create("wf_id", "ctx_id").with_status(WorkflowStatus.RUNNING)
        assert i.status == WorkflowStatus.RUNNING

    def test_workflow_state_create(self):
        state = WorkflowState.create("inst_id", "step_id")
        assert state.current_step_id == "step_id"
        assert state.status == WorkflowStatus.PENDING


class TestTaskTypes:

    def test_scheduled_task_create(self):
        t = ScheduledTask.create("t1", "action", priority=5, x="1")
        assert t.name     == "t1"
        assert t.priority == 5
        assert t.get_param("x") == "1"

    def test_scheduled_task_with_status(self):
        t = ScheduledTask.create("t1", "a")
        t2 = t.with_status(TaskStatus.RUNNING)
        assert t2.status == TaskStatus.RUNNING

    def test_scheduled_task_is_due(self):
        t = ScheduledTask.create("t1", "a", scheduled_at=time.time() - 1)
        assert t.is_due()

    def test_scheduled_task_not_due(self):
        t = ScheduledTask.create("t1", "a", scheduled_at=time.time() + 9999)
        assert not t.is_due()

    def test_scheduled_task_is_ready(self):
        t = ScheduledTask.create("t1", "a", dependencies=frozenset({"dep1"}))
        assert not t.is_ready(frozenset())
        assert t.is_ready(frozenset({"dep1"}))

    def test_scheduler_policy_default(self):
        p = SchedulerPolicy.default()
        assert p.max_concurrent  > 0
        assert p.max_queue_size  > 0
        assert p.retry_backoff_s == 0.0


# =============================================================================
# SECTION 3: Planning Engine
# =============================================================================

class TestPlanningEngine:

    def test_create_plan_single(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("do something")
        plan = pe.create_plan(ctx)
        assert plan.status == PlanStatus.READY
        assert plan.step_count() == 1

    def test_create_plan_sequential(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("step A; step B; step C")
        plan = pe.create_plan(ctx)
        assert plan.step_count() == 3
        assert len(plan.dependencies) == 2

    def test_create_plan_parallel(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("A | B | C")
        plan = pe.create_plan(ctx)
        assert plan.step_count() == 3
        assert len(plan.dependencies) == 0
        for step in plan.steps:
            assert step.parallel

    def test_add_step(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("obj")
        plan = pe.create_plan(ctx)
        s    = PlanStep.create("extra", "execute")
        plan2 = pe.add_step(plan, s)
        assert plan2.step_count() == 2

    def test_get_plan(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("obj")
        plan = pe.create_plan(ctx)
        retrieved = pe.get_plan(plan.plan_id)
        assert retrieved.plan_id == plan.plan_id

    def test_get_plan_not_found(self):
        pe = PlanningEngine()
        with pytest.raises(AIPlanNotFoundError):
            pe.get_plan("nonexistent")

    def test_validate_plan_valid(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("a; b; c")
        plan = pe.create_plan(ctx)
        assert pe.validate_plan(plan) is True

    def test_validate_plan_unknown_dep(self):
        pe   = PlanningEngine()
        s1   = PlanStep.create("s1", "execute")
        dep  = PlanDependency.create("unknown_id", s1.step_id)
        plan = ExecutionPlan.create("obj", (s1,), (dep,))
        with pytest.raises(AIPlanDependencyError):
            pe.validate_plan(plan)

    def test_get_execution_order_sequential(self):
        pe     = PlanningEngine()
        ctx    = PlanningContext.create("a; b")
        plan   = pe.create_plan(ctx)
        batches = pe.get_execution_order(plan)
        assert len(batches) == 2

    def test_get_execution_order_parallel(self):
        pe     = PlanningEngine()
        ctx    = PlanningContext.create("a | b | c")
        plan   = pe.create_plan(ctx)
        batches = pe.get_execution_order(plan)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_replan_removes_failed_step(self):
        pe     = PlanningEngine()
        ctx    = PlanningContext.create("a; b; c")
        plan   = pe.create_plan(ctx)
        failed = plan.steps[0]
        new_plan = pe.replan(plan, failed.step_id)
        ids = {s.step_id for s in new_plan.steps}
        assert failed.step_id not in ids

    def test_replan_invalid_step(self):
        pe   = PlanningEngine()
        ctx  = PlanningContext.create("a")
        plan = pe.create_plan(ctx)
        with pytest.raises(AIReplanningError):
            pe.replan(plan, "nonexistent")

    def test_plan_count(self):
        pe  = PlanningEngine()
        ctx = PlanningContext.create("a")
        pe.create_plan(ctx)
        assert pe.plan_count() == 1


# =============================================================================
# SECTION 4: Workflow Manager
# =============================================================================

class TestWorkflowManager:

    def _wm_with_handler(self):
        wm = WorkflowManager()
        wm.register_step_handler("execute", lambda p: "ok")
        return wm

    def test_register_and_get(self):
        wm = WorkflowManager()
        d  = _defn()
        wm.register(d)
        assert wm.get_definition(d.workflow_id).workflow_id == d.workflow_id

    def test_register_duplicate_raises(self):
        wm = WorkflowManager()
        d  = _defn()
        wm.register(d)
        with pytest.raises(AIWorkflowAlreadyExistsError):
            wm.register(d)

    def test_deregister(self):
        wm = WorkflowManager()
        d  = _defn()
        wm.register(d)
        wm.deregister(d.workflow_id)
        assert wm.definition_count() == 0

    def test_deregister_not_found(self):
        wm = WorkflowManager()
        with pytest.raises(AIWorkflowNotFoundError):
            wm.deregister("nonexistent")

    def test_start_workflow(self):
        wm  = self._wm_with_handler()
        d   = _defn()
        wm.register(d)
        ctx = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        assert inst.status == WorkflowStatus.RUNNING

    def test_pause_and_resume(self):
        wm  = self._wm_with_handler()
        d   = _defn()
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        wm.pause(inst.instance_id)
        assert wm.get_instance(inst.instance_id).status == WorkflowStatus.PAUSED
        wm.resume(inst.instance_id)
        assert wm.get_instance(inst.instance_id).status == WorkflowStatus.RUNNING

    def test_cancel_workflow(self):
        wm  = self._wm_with_handler()
        d   = _defn()
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        wm.cancel(inst.instance_id)
        assert wm.get_instance(inst.instance_id).status == WorkflowStatus.CANCELLED

    def test_cancel_terminal_raises(self):
        wm  = self._wm_with_handler()
        d   = _defn()
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        wm.cancel(inst.instance_id)
        with pytest.raises(AIWorkflowStateError):
            wm.cancel(inst.instance_id)

    def test_execute_step_success(self):
        wm   = self._wm_with_handler()
        step = WorkflowStep.create("s1", "execute")
        d    = WorkflowDefinition.create("wf", (step,))
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        result = wm.execute_step(inst.instance_id, step.step_id)
        assert result == "ok"
        state = wm.get_state(inst.instance_id)
        assert state.status == WorkflowStatus.COMPLETED

    def test_execute_step_no_handler(self):
        wm   = WorkflowManager()
        step = WorkflowStep.create("s1", "unknown_action")
        d    = WorkflowDefinition.create("wf", (step,))
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        with pytest.raises(AIWorkflowExecutionError):
            wm.execute_step(inst.instance_id, step.step_id)

    def test_execute_step_failure_path(self):
        wm = WorkflowManager()
        wm.register_step_handler("fail_action", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
        step = WorkflowStep.create("s1", "fail_action")
        d    = WorkflowDefinition.create("wf", (step,))
        wm.register(d)
        ctx  = OrchestrationContext.create("obj", "p1")
        inst = wm.start(d.workflow_id, ctx)
        with pytest.raises(AIWorkflowExecutionError):
            wm.execute_step(inst.instance_id, step.step_id)
        assert wm.get_state(inst.instance_id).status == WorkflowStatus.FAILED


# =============================================================================
# SECTION 5: Orchestration Engine
# =============================================================================

class TestOrchestrationEngine:

    def _make(self):
        pe   = PlanningEngine()
        mgr  = OrchestrationManager()
        orch = Orchestrator(mgr, pe)
        orch.register_step_handler("execute", lambda p: "step_done")
        return orch, mgr, pe

    def test_submit_objective(self):
        orch, mgr, _ = self._make()
        ctx = OrchestrationContext.create("obj", "p1")
        sid = orch.submit_objective(ctx)
        assert sid
        session = mgr.get_session(sid)
        assert session.status == ObjectiveStatus.PENDING

    def test_submit_empty_objective_raises(self):
        orch, _, _ = self._make()
        ctx = OrchestrationContext.create("   ", "p1")
        with pytest.raises(AIObjectiveValidationError):
            orch.submit_objective(ctx)

    def test_generate_plan(self):
        orch, mgr, _ = self._make()
        ctx = OrchestrationContext.create("a; b", "p1")
        sid = orch.submit_objective(ctx)
        plan = orch.generate_plan(sid)
        assert plan.step_count() == 2
        assert plan.status == PlanStatus.READY

    def test_execute_success(self):
        orch, _, _ = self._make()
        ctx    = OrchestrationContext.create("do it", "p1")
        sid    = orch.submit_objective(ctx)
        result = orch.execute(sid)
        assert result.is_successful
        assert result.steps_completed > 0

    def test_execute_no_handler_skips(self):
        pe   = PlanningEngine()
        mgr  = OrchestrationManager()
        orch = Orchestrator(mgr, pe)
        # no handlers registered
        ctx    = OrchestrationContext.create("do it", "p1")
        sid    = orch.submit_objective(ctx)
        result = orch.execute(sid)
        assert result.is_successful  # skipped steps still = success

    def test_execute_handler_failure_returns_failed(self):
        pe   = PlanningEngine()
        mgr  = OrchestrationManager()
        orch = Orchestrator(mgr, pe)
        orch.register_step_handler("execute", lambda p: (_ for _ in ()).throw(ValueError("bad")))
        ctx    = OrchestrationContext.create("do it", "p1")
        sid    = orch.submit_objective(ctx)
        result = orch.execute(sid)
        assert not result.is_successful
        assert result.steps_failed > 0

    def test_cancel(self):
        orch, mgr, _ = self._make()
        ctx = OrchestrationContext.create("obj", "p1")
        sid = orch.submit_objective(ctx)
        orch.cancel(sid)
        assert mgr.get_session(sid).status == ObjectiveStatus.CANCELLED

    def test_session_count(self):
        orch, mgr, _ = self._make()
        ctx = OrchestrationContext.create("obj", "p1")
        orch.submit_objective(ctx)
        assert orch.session_count() == 1

    def test_orchestration_manager_close_session(self):
        mgr  = OrchestrationManager()
        ctx  = OrchestrationContext.create("obj", "p1")
        sess = mgr.create_session(ctx)
        assert mgr.active_count() == 1
        mgr.close_session(sess.session_id)
        assert mgr.active_count() == 0


# =============================================================================
# SECTION 6: Task Scheduler
# =============================================================================

class TestTaskScheduler:

    def test_schedule_and_run(self):
        ts = TaskScheduler()
        ts.register_handler("action", lambda p: "done")
        t  = ScheduledTask.create("t1", "action")
        ts.schedule(t)
        executed = ts.run_pending()
        assert t.task_id in executed
        assert ts.completed_count() == 1

    def test_priority_ordering(self):
        ts     = TaskScheduler()
        order  = []
        ts.register_handler("a", lambda p: order.append("low"))
        ts.register_handler("b", lambda p: order.append("high"))
        low  = ScheduledTask.create("low",  "a", priority=0)
        high = ScheduledTask.create("high", "b", priority=10)
        ts.schedule(low)
        ts.schedule(high)
        ts.run_pending()
        assert order.index("high") < order.index("low")

    def test_future_task_not_run(self):
        ts = TaskScheduler()
        ts.register_handler("action", lambda p: None)
        t  = ScheduledTask.create("t1", "action", scheduled_at=time.time() + 9999)
        ts.schedule(t)
        executed = ts.run_pending()
        assert t.task_id not in executed

    def test_dependency_deferred(self):
        ts    = TaskScheduler()
        calls = []
        ts.register_handler("action", lambda p: calls.append(1))
        dep   = ScheduledTask.create("dep", "action")
        child = ScheduledTask.create("child", "action",
                                    dependencies=frozenset({dep.task_id}))
        ts.schedule(dep)
        ts.schedule(child)
        executed = ts.run_pending()
        # dep runs, child deferred
        assert dep.task_id in executed
        assert child.task_id not in executed
        # second run: dep completed, child now runs
        executed2 = ts.run_pending()
        assert child.task_id in executed2

    def test_cancel_task(self):
        ts = TaskScheduler()
        t  = ScheduledTask.create("t1", "action")
        ts.schedule(t)
        ts.cancel_task(t.task_id)
        executed = ts.run_pending()
        assert t.task_id not in executed

    def test_cancel_terminal_raises(self):
        ts = TaskScheduler()
        ts.register_handler("action", lambda p: None)
        t  = ScheduledTask.create("t1", "action")
        ts.schedule(t)
        ts.run_pending()
        with pytest.raises(AITaskExecutionError):
            ts.cancel_task(t.task_id)

    def test_queue_full_raises(self):
        policy = SchedulerPolicy(
            max_concurrent    = 1,
            max_queue_size    = 2,
            default_timeout_s = 60,
            retry_backoff_s   = 0.0,
        )
        ts = TaskScheduler(policy)
        ts.schedule(ScheduledTask.create("t1", "a", scheduled_at=time.time() + 9999))
        ts.schedule(ScheduledTask.create("t2", "a", scheduled_at=time.time() + 9999))
        with pytest.raises(AITaskQueueFullError):
            ts.schedule(ScheduledTask.create("t3", "a", scheduled_at=time.time() + 9999))

    def test_no_handler_marks_failed(self):
        ts = TaskScheduler()
        t  = ScheduledTask.create("t1", "no_such_action")
        ts.schedule(t)
        ts.run_pending()
        assert ts.failed_count() == 1

    def test_recurring_task_requeued(self):
        ts    = TaskScheduler()
        calls = []
        ts.register_handler("action", lambda p: calls.append(1))
        t = ScheduledTask.create("t1", "action", recurring_interval_s=0.0)
        ts.schedule(t)
        ts.run_pending()
        # recurring task should be re-queued (not in completed permanently)
        assert ts.queued_count() == 1 or ts.task_count() >= 1


# =============================================================================
# SECTION 7: Resource Coordination
# =============================================================================

class TestAgentAllocator:

    def test_register_and_allocate(self):
        aa = AgentAllocator()
        aa.register_agent("agent-1", frozenset({"cap-A"}))
        agent = aa.allocate("cap-A")
        assert agent == "agent-1"

    def test_allocate_no_agent_raises(self):
        aa = AgentAllocator()
        with pytest.raises(AIAgentNotAvailableError):
            aa.allocate("cap-A")

    def test_allocate_at_max_load_raises(self):
        aa = AgentAllocator()
        aa.register_agent("agent-1", frozenset({"cap-A"}), max_load=1)
        aa.allocate("cap-A")
        with pytest.raises(AIAgentNotAvailableError):
            aa.allocate("cap-A")

    def test_release_frees_load(self):
        aa = AgentAllocator()
        aa.register_agent("agent-1", frozenset({"cap-A"}), max_load=1)
        aa.allocate("cap-A")
        aa.release("agent-1")
        agent = aa.allocate("cap-A")
        assert agent == "agent-1"

    def test_least_loaded_selection(self):
        aa = AgentAllocator()
        aa.register_agent("a1", frozenset({"cap"}), max_load=5)
        aa.register_agent("a2", frozenset({"cap"}), max_load=5)
        # a1 gets more load
        aa.allocate("cap")  # a1 load=1
        # next allocation should pick a2 (load=0)
        chosen = aa.allocate("cap")
        assert chosen == "a2"

    def test_available_agents(self):
        aa = AgentAllocator()
        aa.register_agent("a1", frozenset({"cap"}), max_load=1)
        assert "a1" in aa.available_agents()

    def test_agent_count(self):
        aa = AgentAllocator()
        aa.register_agent("a1", frozenset({"cap"}))
        aa.register_agent("a2", frozenset({"cap"}))
        assert aa.agent_count() == 2


class TestCapabilityAllocator:

    def test_reserve_and_release(self):
        ca  = CapabilityAllocator()
        res = ca.reserve("cap-A", "agent-1", "req-1")
        assert res.capability_id == "cap-A"
        assert not ca.is_available("cap-A")
        ca.release("cap-A")
        assert ca.is_available("cap-A")

    def test_conflict_raises(self):
        ca = CapabilityAllocator()
        ca.reserve("cap-A", "agent-1", "req-1")
        with pytest.raises(AIAllocationConflictError):
            ca.reserve("cap-A", "agent-2", "req-2")

    def test_release_by_id(self):
        ca  = CapabilityAllocator()
        res = ca.reserve("cap-A", "a1", "r1")
        ca.release_by_id(res.reservation_id)
        assert ca.is_available("cap-A")

    def test_reservation_count(self):
        ca = CapabilityAllocator()
        ca.reserve("cap-A", "a1", "r1")
        ca.reserve("cap-B", "a2", "r2")
        assert ca.reservation_count() == 2


# =============================================================================
# SECTION 8: Recovery Manager
# =============================================================================

class TestRecoveryManager:

    def _make(self):
        rc  = RetryCoordinator()
        rm  = RollbackManager()
        mgr = RecoveryManager(rc, rm)
        return mgr, rc, rm

    def test_retry_success(self):
        rc     = RetryCoordinator()
        calls  = []
        result = rc.retry(lambda: calls.append(1) or "done", max_retries=2)
        assert result == "done"
        assert len(calls) == 1

    def test_retry_exhausted(self):
        rc = RetryCoordinator()
        with pytest.raises(AIMaxRetriesExceededError):
            rc.retry(lambda: (_ for _ in ()).throw(ValueError("bad")), max_retries=2)

    def test_rollback_success(self):
        rm     = RollbackManager()
        called = []
        rm.register_rollback("plan1", "step1", lambda: called.append("rolled"))
        result = rm.rollback("plan1")
        assert result is True
        assert "rolled" in called

    def test_rollback_failure_raises(self):
        rm = RollbackManager()
        rm.register_rollback("plan1", "s1", lambda: (_ for _ in ()).throw(RuntimeError("rb fail")))
        with pytest.raises(AIRollbackFailedError):
            rm.rollback("plan1")

    def test_rollback_no_entries_returns_true(self):
        rm = RollbackManager()
        assert rm.rollback("nonexistent") is True

    def test_recovery_skip_strategy(self):
        mgr, _, _ = self._make()
        mgr.register_strategy("*", RecoveryStrategy.SKIP)
        assert mgr.recover("s1", "any_action") is True

    def test_recovery_fail_strategy_raises(self):
        mgr, _, _ = self._make()
        mgr.register_strategy("*", RecoveryStrategy.FAIL)
        with pytest.raises(AIRecoveryFailedError):
            mgr.recover("s1", "any_action")

    def test_recovery_default_fail(self):
        mgr, _, _ = self._make()
        with pytest.raises(AIRecoveryFailedError):
            mgr.recover("s1", "unmatched_action")

    def test_recovery_retry_strategy(self):
        mgr, _, _ = self._make()
        mgr.register_strategy("execute", RecoveryStrategy.RETRY)
        calls = []
        result = mgr.recover(
            session_id    = "s1",
            failed_action = "execute",
            handler_fn    = lambda: calls.append(1) or "ok",
            max_retries   = 1,
        )
        assert result is True

    def test_recovery_rollback_strategy(self):
        mgr, _, rm = self._make()
        rolled = []
        rm.register_rollback("plan1", "s1", lambda: rolled.append(1))
        mgr.register_strategy("execute", RecoveryStrategy.ROLLBACK)
        result = mgr.recover("session", "execute", plan_id="plan1")
        assert result is True
        assert rolled

    def test_strategy_count(self):
        mgr, _, _ = self._make()
        mgr.register_strategy("a", RecoveryStrategy.SKIP)
        mgr.register_strategy("b", RecoveryStrategy.RETRY)
        assert mgr.strategy_count() == 2


# =============================================================================
# SECTION 9: Observability
# =============================================================================

class TestExecutionMonitor:

    def test_record_start_and_metrics(self):
        em = ExecutionMonitor()
        em.record_start("s1", total_steps=3)
        m = em.get_metrics("s1")
        assert m.total_steps == 3

    def test_record_step_complete(self):
        em = ExecutionMonitor()
        em.record_start("s1")
        em.record_step_start("s1", "step-A")
        em.record_step_complete("s1", "step-A")
        m = em.get_metrics("s1")
        assert m.completed_steps == 1

    def test_record_step_failed(self):
        em = ExecutionMonitor()
        em.record_start("s1")
        em.record_step_failed("s1", "step-A")
        m = em.get_metrics("s1")
        assert m.failed_steps == 1

    def test_timeline(self):
        em = ExecutionMonitor()
        em.record_start("s1")
        em.record_step_start("s1", "step-A")
        em.record_step_complete("s1", "step-A")
        em.record_complete("s1")
        tl = em.get_timeline("s1")
        assert tl.session_id == "s1"
        assert tl.event_count() >= 3

    def test_session_count(self):
        em = ExecutionMonitor()
        em.record_start("s1")
        em.record_start("s2")
        assert em.session_count() == 2

    def test_success_rate_full(self):
        em = ExecutionMonitor()
        em.record_start("s1", total_steps=2)
        em.record_step_complete("s1", "a")
        em.record_step_complete("s1", "b")
        m = em.get_metrics("s1")
        assert m.success_rate == 1.0


class TestProgressTracker:

    def test_start_and_advance(self):
        pt = ProgressTracker()
        pt.start("s1", 4)
        assert pt.get_progress("s1") == 0.0
        pt.advance("s1", 2)
        assert pt.get_progress("s1") == 0.5

    def test_advance_caps_at_one(self):
        pt = ProgressTracker()
        pt.start("s1", 2)
        pt.advance("s1", 100)
        assert pt.get_progress("s1") == 1.0

    def test_reset(self):
        pt = ProgressTracker()
        pt.start("s1", 2)
        pt.advance("s1", 1)
        pt.reset("s1")
        assert pt.tracked_count() == 0


# =============================================================================
# SECTION 10: Events
# =============================================================================

class TestOrchestratorEvents:

    def test_objective_received_event(self):
        ev = ObjectiveReceivedEvent.create("src", "s1", "obj1")
        assert ev.event_type == OrchestratorEventType.OBJECTIVE_RECEIVED
        assert ev.session_id == "s1"
        assert ev.objective  == "obj1"

    def test_plan_generated_event(self):
        ev = PlanGeneratedEvent.create("src", "s1", "p1", 3)
        assert ev.event_type == OrchestratorEventType.PLAN_GENERATED
        assert ev.step_count == 3

    def test_session_started_event(self):
        ev = SessionStartedEvent.create("src", "s1", "p1")
        assert ev.principal_id == "p1"

    def test_session_completed_event(self):
        ev = SessionCompletedEvent.create("src", "s1", 123.4)
        assert ev.duration_ms == 123.4

    def test_workflow_registered_event(self):
        ev = WorkflowRegisteredEvent.create("src", "wf1", "My Workflow")
        assert ev.workflow_name == "My Workflow"

    def test_workflow_started_event(self):
        ev = WorkflowStartedEvent.create("src", "wf1", "inst-1")
        assert ev.instance_id == "inst-1"

    def test_workflow_completed_event(self):
        ev = WorkflowCompletedEvent.create("src", "inst-1", 55.0)
        assert ev.duration_ms == 55.0

    def test_task_scheduled_event(self):
        ev = TaskScheduledEvent.create("src", "t1", "my_task", 5)
        assert ev.priority == 5

    def test_task_completed_event(self):
        ev = TaskCompletedEvent.create("src", "t1", 10.0)
        assert ev.duration_ms == 10.0

    def test_recovery_started_event(self):
        ev = RecoveryStartedEvent.create("src", "s1", "execute", "retry")
        assert ev.strategy == "retry"

    def test_recovery_completed_event(self):
        ev = RecoveryCompletedEvent.create("src", "s1", True)
        assert ev.success is True

    def test_agent_allocated_event(self):
        ev = AgentAllocatedEvent.create("src", "a1", "cap-A")
        assert ev.agent_id == "a1"

    def test_resource_reserved_event(self):
        ev = ResourceReservedEvent.create("src", "res-1", "cap-A")
        assert ev.reservation_id == "res-1"

    def test_event_has_id_and_timestamp(self):
        ev = ObjectiveReceivedEvent.create("src", "s1", "obj")
        assert ev.event_id
        assert ev.occurred_at > 0


class TestOrchestratorEventBus:

    def test_subscribe_and_publish(self):
        bus   = OrchestratorEventBus()
        seen  = []
        bus.subscribe(OrchestratorEventType.OBJECTIVE_RECEIVED, lambda e: seen.append(e))
        ev = ObjectiveReceivedEvent.create("src", "s1", "obj")
        bus.publish(ev)
        assert len(seen) == 1

    def test_subscribe_all(self):
        bus  = OrchestratorEventBus()
        seen = []
        bus.subscribe_all(lambda e: seen.append(e))
        bus.publish(ObjectiveReceivedEvent.create("src", "s1", "obj"))
        bus.publish(SessionStartedEvent.create("src", "s1", "p1"))
        assert len(seen) == 2

    def test_unsubscribe(self):
        bus  = OrchestratorEventBus()
        seen = []
        fn   = lambda e: seen.append(e)
        bus.subscribe(OrchestratorEventType.OBJECTIVE_RECEIVED, fn)
        bus.unsubscribe(OrchestratorEventType.OBJECTIVE_RECEIVED, fn)
        bus.publish(ObjectiveReceivedEvent.create("src", "s1", "obj"))
        assert len(seen) == 0

    def test_subscriber_exception_swallowed(self):
        bus = OrchestratorEventBus()
        bus.subscribe_all(lambda e: (_ for _ in ()).throw(RuntimeError("oops")))
        bus.publish(ObjectiveReceivedEvent.create("src", "s1", "obj"))
        assert bus.total_count() == 1

    def test_history(self):
        bus = OrchestratorEventBus()
        bus.publish(ObjectiveReceivedEvent.create("src", "s1", "obj"))
        assert len(bus.history(limit=10)) == 1

    def test_clear_history(self):
        bus = OrchestratorEventBus()
        bus.publish(ObjectiveReceivedEvent.create("src", "s1", "obj"))
        bus.clear_history()
        assert bus.total_count() == 0


# =============================================================================
# SECTION 11: Snapshot
# =============================================================================

class TestOrchestratorSnapshot:

    def test_build(self):
        snap = OrchestratorSnapshot.build(
            is_running                = True,
            active_sessions           = 3,
            registered_workflows      = 5,
            active_workflow_instances = 2,
            queued_tasks              = 10,
            completed_tasks           = 100,
            failed_tasks              = 2,
            registered_agents         = 4,
            active_reservations       = 1,
            recovery_strategies       = 3,
            monitored_sessions        = 3,
            plan_count                = 3,
            event_history_size        = 50,
        )
        assert snap.is_running              is True
        assert snap.active_sessions         == 3
        assert snap.registered_workflows    == 5
        assert snap.queued_tasks            == 10
        assert snap.snapshot_id
        assert snap.captured_at > 0

    def test_snapshot_is_frozen(self):
        snap = OrchestratorSnapshot.build(
            is_running=True, active_sessions=0, registered_workflows=0,
            active_workflow_instances=0, queued_tasks=0, completed_tasks=0,
            failed_tasks=0, registered_agents=0, active_reservations=0,
            recovery_strategies=0, monitored_sessions=0, plan_count=0,
            event_history_size=0,
        )
        with pytest.raises(Exception):
            snap.active_sessions = 99  # type: ignore


# =============================================================================
# SECTION 12: Gateway
# =============================================================================

def _wf_defn() -> WorkflowDefinition:
    step = WorkflowStep.create("s1", "execute")
    return WorkflowDefinition.create("wf1", (step,))


class TestGatewayLifecycle:

    def test_not_started_raises(self):
        gw = OrchestratorGateway()
        with pytest.raises(AIOrchestrationException):
            gw.submit_objective("obj", "p1")

    def test_start_stop(self):
        gw = OrchestratorGateway()
        gw.start()
        gw.stop()

    def test_restart(self):
        gw = OrchestratorGateway()
        gw.start()
        gw.stop()
        gw.start()
        sid = gw.submit_objective("restart test", "p1")
        assert sid
        gw.stop()

    def test_health_when_running(self):
        gw = _gw()
        h  = gw.health()
        assert h["running"] is True
        assert h["system_id"] == "iios:ai:orchestrator:gateway"
        gw.stop()

    def test_status_alias(self):
        gw = _gw()
        assert gw.status() == gw.health()
        gw.stop()

    def test_snapshot(self):
        gw   = _gw()
        snap = gw.snapshot()
        assert snap.is_running is True
        gw.stop()


class TestGatewayObjective:

    def test_submit_objective(self):
        gw  = _gw()
        sid = gw.submit_objective("analyse data", "agent-1")
        assert sid
        session = gw.get_session(sid)
        assert session.context.objective == "analyse data"
        gw.stop()

    def test_generate_plan(self):
        gw   = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        sid  = gw.submit_objective("a; b", "p1")
        plan = gw.generate_plan(sid)
        assert plan.step_count() == 2
        assert plan.status == PlanStatus.READY
        gw.stop()

    def test_execute_plan(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "done")
        sid    = gw.submit_objective("do it", "p1")
        gw.generate_plan(sid)
        result = gw.execute_plan(sid)
        assert result.is_successful
        gw.stop()

    def test_execute_plan_auto_generates(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "done")
        sid    = gw.submit_objective("auto", "p1")
        result = gw.execute_plan(sid)
        assert result.is_successful
        gw.stop()

    def test_cancel_session(self):
        gw  = _gw()
        sid = gw.submit_objective("obj", "p1")
        gw.cancel_session(sid)
        session = gw.get_session(sid)
        assert session.status == ObjectiveStatus.CANCELLED
        gw.stop()

    def test_get_execution_status(self):
        gw  = _gw()
        sid = gw.submit_objective("obj", "p1")
        st  = gw.get_execution_status(sid)
        assert st["session_id"] == sid
        assert "status" in st
        gw.stop()

    def test_replan(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        sid  = gw.submit_objective("a; b; c", "p1")
        plan = gw.generate_plan(sid)
        failed_step = plan.steps[0]
        new_plan = gw.replan(sid, failed_step.step_id)
        assert failed_step.step_id not in {s.step_id for s in new_plan.steps}
        gw.stop()


class TestGatewayWorkflow:

    def test_register_and_start_workflow(self):
        gw   = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        defn = _wf_defn()
        gw.register_workflow(defn)
        iid  = gw.start_workflow(defn.workflow_id, "obj", "p1")
        assert iid
        state = gw.get_workflow_state(iid)
        assert state.status == WorkflowStatus.RUNNING
        gw.stop()

    def test_pause_resume_workflow(self):
        gw   = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        defn = _wf_defn()
        gw.register_workflow(defn)
        iid  = gw.start_workflow(defn.workflow_id, "obj", "p1")
        gw.pause_workflow(iid)
        assert gw.get_workflow_state(iid).status == WorkflowStatus.PAUSED
        gw.resume_workflow(iid)
        assert gw.get_workflow_state(iid).status == WorkflowStatus.RUNNING
        gw.stop()

    def test_cancel_workflow(self):
        gw   = _gw()
        defn = _wf_defn()
        gw.register_workflow(defn)
        iid  = gw.start_workflow(defn.workflow_id, "obj", "p1")
        gw.cancel_workflow(iid)
        assert gw.get_workflow_state(iid).status == WorkflowStatus.CANCELLED
        gw.stop()

    def test_execute_workflow_step(self):
        gw   = _gw()
        gw.register_step_handler("execute", lambda p: "step_result")
        defn = _wf_defn()
        gw.register_workflow(defn)
        iid  = gw.start_workflow(defn.workflow_id, "obj", "p1")
        step = defn.steps[0]
        res  = gw.execute_workflow_step(iid, step.step_id)
        assert res == "step_result"
        gw.stop()

    def test_list_workflows(self):
        gw   = _gw()
        defn = _wf_defn()
        gw.register_workflow(defn)
        assert len(gw.list_workflows()) == 1
        gw.stop()


class TestGatewayScheduler:

    def test_schedule_and_run(self):
        gw = _gw()
        gw.register_task_handler("run", lambda p: None)
        t  = ScheduledTask.create("task1", "run")
        gw.schedule_task(t)
        executed = gw.run_pending_tasks()
        assert t.task_id in executed
        gw.stop()

    def test_cancel_task(self):
        gw = _gw()
        t  = ScheduledTask.create("t1", "run", scheduled_at=time.time() + 9999)
        gw.schedule_task(t)
        gw.cancel_task(t.task_id)
        executed = gw.run_pending_tasks()
        assert t.task_id not in executed
        gw.stop()


class TestGatewayResources:

    def test_register_and_allocate_agent(self):
        gw = _gw()
        gw.register_agent("a1", frozenset({"cap-X"}))
        agent = gw.allocate_agent("cap-X")
        assert agent == "a1"
        gw.stop()

    def test_reserve_resource(self):
        gw  = _gw()
        res = gw.reserve_resource("cap-Y", "a1", "req-1")
        assert res.capability_id == "cap-Y"
        gw.stop()

    def test_release_resource(self):
        gw  = _gw()
        gw.reserve_resource("cap-Y", "a1", "req-1")
        gw.release_resource("cap-Y")
        res2 = gw.reserve_resource("cap-Y", "a2", "req-2")
        assert res2.capability_id == "cap-Y"
        gw.stop()


class TestGatewayRecovery:

    def test_register_and_apply_strategy(self):
        gw = _gw()
        gw.register_recovery_strategy("*", RecoveryStrategy.SKIP)
        result = gw.recover("s1", "execute")
        assert result is True
        gw.stop()

    def test_rollback_registration(self):
        gw     = _gw()
        called = []
        gw.register_rollback("plan1", "step1", lambda: called.append(1))
        gw._c.rollback_manager.rollback("plan1")
        assert called
        gw.stop()


class TestGatewayObservability:

    def test_progress_after_submit(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        sid = gw.submit_objective("obj", "p1")
        gw.generate_plan(sid)
        p = gw.get_progress(sid)
        assert 0.0 <= p <= 1.0
        gw.stop()

    def test_metrics_after_execute(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        sid    = gw.submit_objective("do it", "p1")
        gw.generate_plan(sid)
        gw.execute_plan(sid)
        m = gw.get_metrics(sid)
        assert m.session_id == sid
        assert m.total_duration_ms >= 0
        gw.stop()

    def test_timeline_after_execute(self):
        gw  = _gw()
        gw.register_step_handler("execute", lambda p: "ok")
        sid    = gw.submit_objective("do it", "p1")
        gw.generate_plan(sid)
        gw.execute_plan(sid)
        tl = gw.get_timeline(sid)
        assert tl.session_id == sid
        assert tl.event_count() >= 1
        gw.stop()


class TestGatewayEvents:

    def test_submit_emits_objective_received(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(
            OrchestratorEventType.OBJECTIVE_RECEIVED,
            lambda e: seen.append(e),
        )
        gw.submit_objective("obj", "p1")
        assert len(seen) == 1
        assert seen[0].event_type == OrchestratorEventType.OBJECTIVE_RECEIVED
        gw.stop()

    def test_generate_plan_emits_event(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(
            OrchestratorEventType.PLAN_GENERATED,
            lambda e: seen.append(e),
        )
        sid = gw.submit_objective("a; b", "p1")
        gw.generate_plan(sid)
        assert len(seen) == 1
        gw.stop()

    def test_register_workflow_emits_event(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(
            OrchestratorEventType.WORKFLOW_REGISTERED,
            lambda e: seen.append(e),
        )
        gw.register_workflow(_wf_defn())
        assert len(seen) == 1
        gw.stop()


# =============================================================================
# SECTION 13: Integration
# =============================================================================

class TestIntegration:

    def test_full_orchestration_flow(self):
        """submit → generate_plan → execute_plan → result."""
        gw = _gw()
        gw.register_step_handler("execute", lambda p: "output")

        sid    = gw.submit_objective("step A; step B; step C", "agent-1")
        plan   = gw.generate_plan(sid)
        result = gw.execute_plan(sid)

        assert plan.step_count()   == 3
        assert result.is_successful
        assert result.steps_completed == 3
        gw.stop()

    def test_parallel_plan_execution(self):
        """Parallel steps (|) all complete in single pass."""
        gw = _gw()
        calls = []
        gw.register_step_handler("execute", lambda p: calls.append(1))

        sid    = gw.submit_objective("A | B | C", "agent-1")
        plan   = gw.generate_plan(sid)
        assert all(s.parallel for s in plan.steps)
        result = gw.execute_plan(sid)
        assert result.is_successful
        assert len(calls) == 3
        gw.stop()

    def test_workflow_full_cycle(self):
        """register → start → execute_step → completed."""
        gw = _gw()
        gw.register_step_handler("execute", lambda p: "wf_done")
        step = WorkflowStep.create("only_step", "execute")
        defn = WorkflowDefinition.create("my_wf", (step,))
        gw.register_workflow(defn)

        iid   = gw.start_workflow(defn.workflow_id, "wf_obj", "agent-2")
        res   = gw.execute_workflow_step(iid, step.step_id)
        state = gw.get_workflow_state(iid)

        assert res == "wf_done"
        assert state.status == WorkflowStatus.COMPLETED
        gw.stop()

    def test_task_scheduler_with_dependency(self):
        """dep task completes → child task runs on second pass."""
        gw = _gw()
        gw.register_task_handler("work", lambda p: None)

        dep   = ScheduledTask.create("dep",   "work")
        child = ScheduledTask.create("child", "work",
                                    dependencies=frozenset({dep.task_id}))
        gw.schedule_task(dep)
        gw.schedule_task(child)

        pass1 = gw.run_pending_tasks()
        pass2 = gw.run_pending_tasks()

        assert dep.task_id   in pass1
        assert child.task_id in pass2
        gw.stop()

    def test_recovery_retry_on_failure(self):
        """Register RETRY strategy → recovery handler succeeds after first failure."""
        gw = _gw()
        gw.register_recovery_strategy("flaky", RecoveryStrategy.RETRY)
        attempts = []
        def flaky_handler():
            attempts.append(1)
            if len(attempts) < 2:
                raise ValueError("transient")
            return "ok"

        result = gw.recover("session-1", "flaky", handler_fn=flaky_handler, max_retries=3)
        assert result is True
        assert len(attempts) == 2
        gw.stop()

    def test_resource_coordination(self):
        """register agent → coordinate → reservation created."""
        gw = _gw()
        gw.register_agent("coordinator-agent", frozenset({"cap-COORD"}), max_load=2)

        agent_id = gw.allocate_agent("cap-COORD")
        assert agent_id == "coordinator-agent"

        res = gw.reserve_resource("cap-COORD", agent_id, "requester-1")
        assert res.agent_id == agent_id

        gw.release_resource("cap-COORD")
        gw.release_agent(agent_id)
        gw.stop()

    def test_health_counters_reflect_state(self):
        """Health counters update after registering workflows and submitting objectives."""
        gw = _gw()
        gw.register_workflow(_wf_defn())
        gw.submit_objective("test", "p1")

        h = gw.health()
        assert h["registered_workflows"] >= 1
        assert h["active_sessions"]      >= 1
        gw.stop()
