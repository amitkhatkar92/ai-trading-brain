"""
orchestrator_container.py -- iios.ai.orchestrator.container
=============================================================
:class:`OrchestratorContainer` — dependency-injection root.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

from ..engine.orchestration_engine  import Orchestrator, OrchestrationManager
from ..engine.planning_engine       import PlanningEngine
from ..engine.workflow_engine       import WorkflowManager
from ..events.orchestrator_event_bus import OrchestratorEventBus
from ..observability.execution_monitor import ExecutionMonitor, ProgressTracker
from ..policy.recovery_manager      import RecoveryManager, RetryCoordinator, RollbackManager
from ..policy.resource_coordinator  import (
    AgentAllocator,
    CapabilityAllocator,
    ExecutionCoordinator,
)
from ..policy.task_scheduler        import TaskScheduler


class OrchestratorContainer:
    """
    Dependency-injection root for the A10 Enterprise AI Orchestrator.

    Instantiating this class creates and wires all sub-systems.
    A single instance is owned by :class:`OrchestratorGateway`.
    """

    def __init__(self) -> None:
        # Infrastructure
        self._event_bus         = OrchestratorEventBus()

        # M2 Engine
        self._planning_engine   = PlanningEngine()
        self._workflow_manager  = WorkflowManager()
        self._orch_manager      = OrchestrationManager()
        self._orchestrator      = Orchestrator(
            manager         = self._orch_manager,
            planning_engine = self._planning_engine,
        )

        # M3 Policy
        self._task_scheduler         = TaskScheduler()
        self._agent_allocator        = AgentAllocator()
        self._capability_allocator   = CapabilityAllocator()
        self._execution_coordinator  = ExecutionCoordinator(
            agent_allocator      = self._agent_allocator,
            capability_allocator = self._capability_allocator,
        )
        self._retry_coordinator = RetryCoordinator()
        self._rollback_manager  = RollbackManager()
        self._recovery_manager  = RecoveryManager(
            retry_coordinator = self._retry_coordinator,
            rollback_manager  = self._rollback_manager,
        )

        # Observability
        self._progress_tracker  = ProgressTracker()
        self._execution_monitor = ExecutionMonitor()

    # ── accessors ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> OrchestratorEventBus:
        return self._event_bus

    @property
    def planning_engine(self) -> PlanningEngine:
        return self._planning_engine

    @property
    def workflow_manager(self) -> WorkflowManager:
        return self._workflow_manager

    @property
    def orch_manager(self) -> OrchestrationManager:
        return self._orch_manager

    @property
    def orchestrator(self) -> Orchestrator:
        return self._orchestrator

    @property
    def task_scheduler(self) -> TaskScheduler:
        return self._task_scheduler

    @property
    def agent_allocator(self) -> AgentAllocator:
        return self._agent_allocator

    @property
    def capability_allocator(self) -> CapabilityAllocator:
        return self._capability_allocator

    @property
    def execution_coordinator(self) -> ExecutionCoordinator:
        return self._execution_coordinator

    @property
    def retry_coordinator(self) -> RetryCoordinator:
        return self._retry_coordinator

    @property
    def rollback_manager(self) -> RollbackManager:
        return self._rollback_manager

    @property
    def recovery_manager(self) -> RecoveryManager:
        return self._recovery_manager

    @property
    def progress_tracker(self) -> ProgressTracker:
        return self._progress_tracker

    @property
    def execution_monitor(self) -> ExecutionMonitor:
        return self._execution_monitor
