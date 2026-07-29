"""
orchestrator_gateway.py -- iios.ai.orchestrator.gateway
=========================================================
:class:`OrchestratorGateway` — single lifecycle-aware public entry point
for the A10 Enterprise AI Orchestrator.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

from typing import Any, Callable, Dict, FrozenSet, List, Optional

from ..container.orchestrator_container import OrchestratorContainer
from ..core.orchestration_context import (
    OrchestrationContext,
    OrchestrationResult,
    OrchestrationSession,
)
from ..core.plan_types import ExecutionPlan
from ..core.task_types import ScheduledTask, SchedulerPolicy
from ..core.workflow_types import WorkflowDefinition, WorkflowInstance, WorkflowState
from ..events.orchestrator_events import (
    AgentAllocatedEvent,
    ObjectiveReceivedEvent,
    PlanGeneratedEvent,
    PlanReplannedEvent,
    RecoveryCompletedEvent,
    RecoveryStartedEvent,
    ResourceReservedEvent,
    SessionCancelledEvent,
    SessionCompletedEvent,
    SessionStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskScheduledEvent,
    WorkflowCancelledEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowRegisteredEvent,
    WorkflowStartedEvent,
)
from ..exceptions.orchestrator_exceptions import AIOrchestrationException
from ..lifecycle import AILifecycleAwareMixin
from ..observability.execution_monitor import ExecutionMetrics, Timeline
from ..policy.recovery_manager import RecoveryStrategy
from ..policy.resource_coordinator import ResourceReservation
from ..snapshot.orchestrator_snapshot import OrchestratorSnapshot

SYSTEM_ID = "iios:ai:orchestrator:gateway"
VERSION   = "1.0.0"
_SRC      = SYSTEM_ID


class OrchestratorGateway(AILifecycleAwareMixin):
    """
    Single lifecycle-aware public entry point for the A10 Enterprise AI Orchestrator.

    Usage::

        gw = OrchestratorGateway()
        gw.start()

        gw.register_step_handler("execute", lambda p: "result")

        session_id = gw.submit_objective("analyse market data", "agent-1")
        plan       = gw.generate_plan(session_id)
        result     = gw.execute_plan(session_id)

        gw.stop()
    """

    SYSTEM_ID  : str = SYSTEM_ID
    VERSION    : str = VERSION
    MODULE_ID  : str = "A10"
    MODULE_NAME: str = "Orchestration"
    API_VERSION: str = "v1"
    DESCRIPTION: str = "Workflow orchestration, task scheduling and execution coordination"
    STATUS     : str = "stable"

    def __init__(self) -> None:
        super().__init__()
        self._container: Optional[OrchestratorContainer] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._container = OrchestratorContainer()

    def _on_stop(self) -> None:
        self._container = None

    @property
    def _c(self) -> OrchestratorContainer:
        if self._container is None:
            raise AIOrchestrationException(
                f"[AI-1500] OrchestratorGateway is not running — call start() first"
            )
        return self._container

    # ── step handler registration ─────────────────────────────────────────────

    def register_step_handler(self, action: str, handler_fn: Callable[[Dict], Any]) -> None:
        """Register a step execution handler for *action* (used by both Orchestrator and WorkflowManager)."""
        self._c.orchestrator.register_step_handler(action, handler_fn)
        self._c.workflow_manager.register_step_handler(action, handler_fn)

    # ── TASK 1: Objective & session management ────────────────────────────────

    def submit_objective(
        self,
        objective:    str,
        principal_id: str,
        **metadata: str,
    ) -> str:
        """Submit a new objective.  Returns the session_id."""
        ctx = OrchestrationContext.create(
            objective    = objective,
            principal_id = principal_id,
            **metadata,
        )
        session_id = self._c.orchestrator.submit_objective(ctx)
        self._c.event_bus.publish(
            ObjectiveReceivedEvent.create(_SRC, session_id, objective)
        )
        self._c.event_bus.publish(
            SessionStartedEvent.create(_SRC, session_id, principal_id)
        )
        self._c.execution_monitor.record_start(session_id)
        return session_id

    def get_session(self, session_id: str) -> OrchestrationSession:
        return self._c.orch_manager.get_session(session_id)

    def get_execution_status(self, session_id: str) -> Dict:
        session = self._c.orch_manager.get_session(session_id)
        plan    = self._c.orchestrator.get_plan(session_id)
        return {
            "session_id": session_id,
            "status":     session.status.value,
            "objective":  session.context.objective,
            "plan_id":    plan.plan_id if plan else None,
            "step_count": plan.step_count() if plan else 0,
        }

    def cancel_session(self, session_id: str) -> None:
        self._c.orchestrator.cancel(session_id)
        self._c.event_bus.publish(SessionCancelledEvent.create(_SRC, session_id))

    # ── TASK 2: Planning ──────────────────────────────────────────────────────

    def generate_plan(self, session_id: str) -> ExecutionPlan:
        """Generate an execution plan for the session's objective."""
        plan = self._c.orchestrator.generate_plan(session_id)
        self._c.event_bus.publish(
            PlanGeneratedEvent.create(_SRC, session_id, plan.plan_id, plan.step_count())
        )
        self._c.progress_tracker.start(session_id, plan.step_count())
        return plan

    def execute_plan(self, session_id: str) -> OrchestrationResult:
        """Execute the plan for *session_id*."""
        import time as _time
        result = self._c.orchestrator.execute(session_id)
        dur_ms = result.duration_ms
        if result.is_successful:
            self._c.event_bus.publish(
                SessionCompletedEvent.create(_SRC, session_id, dur_ms)
            )
        self._c.execution_monitor.record_complete(session_id)
        return result

    def replan(self, session_id: str, failed_step_id: str) -> ExecutionPlan:
        """Dynamically replan by removing the failed step and its dependants."""
        current_plan = self._c.orchestrator.get_plan(session_id)
        if current_plan is None:
            raise AIOrchestrationException(
                f"[AI-1500] No plan found for session '{session_id}'"
            )
        new_plan = self._c.planning_engine.replan(current_plan, failed_step_id)
        self._c.event_bus.publish(
            PlanReplannedEvent.create(_SRC, session_id, new_plan.plan_id, failed_step_id)
        )
        return new_plan

    # ── TASK 3: Workflow ──────────────────────────────────────────────────────

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        self._c.workflow_manager.register(definition)
        self._c.event_bus.publish(
            WorkflowRegisteredEvent.create(_SRC, definition.workflow_id, definition.name)
        )

    def start_workflow(
        self,
        workflow_id:  str,
        objective:    str,
        principal_id: str,
    ) -> str:
        """Start a workflow instance.  Returns the instance_id."""
        ctx      = OrchestrationContext.create(objective=objective, principal_id=principal_id)
        instance = self._c.workflow_manager.start(workflow_id, ctx)
        self._c.event_bus.publish(
            WorkflowStartedEvent.create(_SRC, workflow_id, instance.instance_id)
        )
        return instance.instance_id

    def pause_workflow(self, instance_id: str) -> None:
        self._c.workflow_manager.pause(instance_id)

    def resume_workflow(self, instance_id: str) -> None:
        self._c.workflow_manager.resume(instance_id)

    def cancel_workflow(self, instance_id: str) -> None:
        self._c.workflow_manager.cancel(instance_id)
        self._c.event_bus.publish(WorkflowCancelledEvent.create(_SRC, instance_id))

    def execute_workflow_step(self, instance_id: str, step_id: str) -> Any:
        try:
            result = self._c.workflow_manager.execute_step(instance_id, step_id)
            inst   = self._c.workflow_manager.get_instance(instance_id)
            from ..core.orchestration_types import WorkflowStatus
            if inst.status == WorkflowStatus.COMPLETED:
                self._c.event_bus.publish(
                    WorkflowCompletedEvent.create(_SRC, instance_id, 0.0)
                )
            return result
        except Exception as exc:
            inst = self._c.workflow_manager.get_instance(instance_id)
            from ..core.orchestration_types import WorkflowStatus
            if inst.status == WorkflowStatus.FAILED:
                self._c.event_bus.publish(
                    WorkflowFailedEvent.create(_SRC, instance_id, str(exc))
                )
            raise

    def get_workflow_state(self, instance_id: str) -> WorkflowState:
        return self._c.workflow_manager.get_state(instance_id)

    def list_workflows(self) -> List[WorkflowDefinition]:
        return self._c.workflow_manager.list_definitions()

    # ── TASK 4: Task scheduling ───────────────────────────────────────────────

    def register_task_handler(self, action: str, handler_fn: Callable[[Dict], Any]) -> None:
        self._c.task_scheduler.register_handler(action, handler_fn)

    def schedule_task(self, task: ScheduledTask) -> str:
        task_id = self._c.task_scheduler.schedule(task)
        self._c.event_bus.publish(
            TaskScheduledEvent.create(_SRC, task_id, task.name, task.priority)
        )
        return task_id

    def cancel_task(self, task_id: str) -> None:
        self._c.task_scheduler.cancel_task(task_id)

    def run_pending_tasks(self) -> List[str]:
        """Execute all due tasks and return the executed task_id list."""
        executed = self._c.task_scheduler.run_pending()
        for task_id in executed:
            task = self._c.task_scheduler.get_task(task_id)
            from ..core.orchestration_types import TaskStatus
            if task.status == TaskStatus.COMPLETED:
                self._c.event_bus.publish(TaskCompletedEvent.create(_SRC, task_id, 0.0))
            elif task.status == TaskStatus.FAILED:
                self._c.event_bus.publish(TaskFailedEvent.create(_SRC, task_id, "failed"))
        return executed

    # ── TASK 5: Resource coordination ─────────────────────────────────────────

    def register_agent(
        self,
        agent_id:     str,
        capabilities: FrozenSet[str],
        max_load:     int = 1,
    ) -> None:
        self._c.agent_allocator.register_agent(agent_id, capabilities, max_load)

    def allocate_agent(self, capability_id: str) -> str:
        agent_id = self._c.agent_allocator.allocate(capability_id)
        self._c.event_bus.publish(
            AgentAllocatedEvent.create(_SRC, agent_id, capability_id)
        )
        return agent_id

    def release_agent(self, agent_id: str) -> None:
        self._c.agent_allocator.release(agent_id)

    def reserve_resource(
        self,
        capability_id: str,
        agent_id:      str,
        requester_id:  str,
        ttl_seconds:   Optional[float] = None,
    ) -> ResourceReservation:
        reservation = self._c.capability_allocator.reserve(
            capability_id = capability_id,
            agent_id      = agent_id,
            requester_id  = requester_id,
            ttl_seconds   = ttl_seconds,
        )
        self._c.event_bus.publish(
            ResourceReservedEvent.create(_SRC, reservation.reservation_id, capability_id)
        )
        return reservation

    def release_resource(self, capability_id: str) -> None:
        self._c.capability_allocator.release(capability_id)

    # ── TASK 6: Recovery ──────────────────────────────────────────────────────

    def register_recovery_strategy(
        self,
        action_pattern: str,
        strategy:       RecoveryStrategy,
    ) -> None:
        self._c.recovery_manager.register_strategy(action_pattern, strategy)

    def recover(
        self,
        session_id:    str,
        failed_action: str,
        handler_fn:    Optional[Callable[[], Any]] = None,
        plan_id:       Optional[str] = None,
        max_retries:   int   = 3,
    ) -> bool:
        strategy = self._c.recovery_manager.get_strategy(failed_action)
        self._c.event_bus.publish(
            RecoveryStartedEvent.create(_SRC, session_id, failed_action, strategy.value)
        )
        success = self._c.recovery_manager.recover(
            session_id    = session_id,
            failed_action = failed_action,
            handler_fn    = handler_fn,
            plan_id       = plan_id,
            max_retries   = max_retries,
        )
        self._c.event_bus.publish(
            RecoveryCompletedEvent.create(_SRC, session_id, success)
        )
        return success

    def register_rollback(
        self,
        plan_id:     str,
        step_id:     str,
        rollback_fn: Callable[[], None],
    ) -> None:
        self._c.rollback_manager.register_rollback(plan_id, step_id, rollback_fn)

    # ── TASK 7: Observability ─────────────────────────────────────────────────

    def get_progress(self, session_id: str) -> float:
        return self._c.progress_tracker.get_progress(session_id)

    def get_metrics(self, session_id: str) -> ExecutionMetrics:
        return self._c.execution_monitor.get_metrics(session_id)

    def get_timeline(self, session_id: str) -> Timeline:
        return self._c.execution_monitor.get_timeline(session_id)

    # ── introspection ─────────────────────────────────────────────────────────

    def health(self) -> Dict:
        c  = self._c
        return {
            "system_id":               SYSTEM_ID,
            "version":                 VERSION,
            "running":                 True,
            "active_sessions":         c.orch_manager.active_count(),
            "registered_workflows":    c.workflow_manager.definition_count(),
            "active_instances":        c.workflow_manager.instance_count(),
            "queued_tasks":            c.task_scheduler.queued_count(),
            "completed_tasks":         c.task_scheduler.completed_count(),
            "failed_tasks":            c.task_scheduler.failed_count(),
            "registered_agents":       c.agent_allocator.agent_count(),
            "active_reservations":     c.capability_allocator.reservation_count(),
            "recovery_strategies":     c.recovery_manager.strategy_count(),
            "monitored_sessions":      c.execution_monitor.session_count(),
            "plan_count":              c.planning_engine.plan_count(),
            "event_history_size":      c.event_bus.total_count(),
        }

    def status(self) -> Dict:
        return self.health()

    def snapshot(self) -> OrchestratorSnapshot:
        h = self.health()
        return OrchestratorSnapshot.build(
            is_running                = h["running"],
            active_sessions           = h["active_sessions"],
            registered_workflows      = h["registered_workflows"],
            active_workflow_instances = h["active_instances"],
            queued_tasks              = h["queued_tasks"],
            completed_tasks           = h["completed_tasks"],
            failed_tasks              = h["failed_tasks"],
            registered_agents         = h["registered_agents"],
            active_reservations       = h["active_reservations"],
            recovery_strategies       = h["recovery_strategies"],
            monitored_sessions        = h["monitored_sessions"],
            plan_count                = h["plan_count"],
            event_history_size        = h["event_history_size"],
        )
