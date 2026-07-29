"""
workflow_engine.py -- iios.ai.orchestrator.engine
===================================================
:class:`WorkflowManager` — registers, starts, pauses, resumes, and cancels
workflow instances.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from ..core.orchestration_context import OrchestrationContext
from ..core.orchestration_types import StepStatus, WorkflowStatus
from ..core.workflow_types import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowState,
    WorkflowStep,
)
from ..exceptions.orchestrator_exceptions import (
    AIWorkflowAlreadyExistsError,
    AIWorkflowExecutionError,
    AIWorkflowNotFoundError,
    AIWorkflowStateError,
)


class WorkflowManager:
    """
    Manages workflow lifecycle: definition registration, instance creation,
    step execution, and state transitions.

    Step handlers are registered by action name::

        wm.register_step_handler("my_action", lambda params: params["x"] * 2)

    The handler receives a ``dict`` of step parameters.
    Its return value is stored in the instance state under the step_id.
    """

    def __init__(self) -> None:
        self._lock:        threading.Lock                          = threading.Lock()
        self._definitions: Dict[str, WorkflowDefinition]          = {}
        self._instances:   Dict[str, WorkflowInstance]            = {}
        self._states:      Dict[str, WorkflowState]               = {}
        self._handlers:    Dict[str, Callable[[Dict], Any]]       = {}

    # ── definition management ─────────────────────────────────────────────────

    def register(self, definition: WorkflowDefinition) -> None:
        with self._lock:
            if definition.workflow_id in self._definitions:
                raise AIWorkflowAlreadyExistsError(
                    f"Workflow '{definition.workflow_id}' already registered"
                )
            self._definitions[definition.workflow_id] = definition

    def deregister(self, workflow_id: str) -> None:
        with self._lock:
            if workflow_id not in self._definitions:
                raise AIWorkflowNotFoundError(f"Workflow '{workflow_id}' not found")
            del self._definitions[workflow_id]

    def get_definition(self, workflow_id: str) -> WorkflowDefinition:
        with self._lock:
            defn = self._definitions.get(workflow_id)
        if defn is None:
            raise AIWorkflowNotFoundError(f"Workflow '{workflow_id}' not found")
        return defn

    def list_definitions(self) -> List[WorkflowDefinition]:
        with self._lock:
            return list(self._definitions.values())

    # ── handler registration ──────────────────────────────────────────────────

    def register_step_handler(self, action: str, handler_fn: Callable[[Dict], Any]) -> None:
        with self._lock:
            self._handlers[action] = handler_fn

    def has_handler(self, action: str) -> bool:
        with self._lock:
            return action in self._handlers

    # ── instance lifecycle ────────────────────────────────────────────────────

    def start(self, workflow_id: str, context: OrchestrationContext) -> WorkflowInstance:
        with self._lock:
            defn = self._definitions.get(workflow_id)
            if defn is None:
                raise AIWorkflowNotFoundError(f"Workflow '{workflow_id}' not found")
            instance = WorkflowInstance.create(
                workflow_id = workflow_id,
                context_id  = context.context_id,
            ).with_status(WorkflowStatus.RUNNING)
            state          = WorkflowState.create(instance.instance_id, defn.initial_step)
            state.status   = WorkflowStatus.RUNNING
            self._instances[instance.instance_id] = instance
            self._states[instance.instance_id]    = state
        return instance

    def pause(self, instance_id: str) -> None:
        with self._lock:
            self._require_instance(instance_id)
            state = self._states[instance_id]
            if state.status != WorkflowStatus.RUNNING:
                raise AIWorkflowStateError(
                    f"Cannot pause workflow in state '{state.status}'"
                )
            state.status = WorkflowStatus.PAUSED
            self._instances[instance_id] = self._instances[instance_id].with_status(
                WorkflowStatus.PAUSED
            )

    def resume(self, instance_id: str) -> None:
        with self._lock:
            self._require_instance(instance_id)
            state = self._states[instance_id]
            if state.status != WorkflowStatus.PAUSED:
                raise AIWorkflowStateError(
                    f"Cannot resume workflow in state '{state.status}'"
                )
            state.status = WorkflowStatus.RUNNING
            self._instances[instance_id] = self._instances[instance_id].with_status(
                WorkflowStatus.RUNNING
            )

    def cancel(self, instance_id: str) -> None:
        with self._lock:
            self._require_instance(instance_id)
            state = self._states[instance_id]
            if state.status.is_terminal():
                raise AIWorkflowStateError(
                    f"Cannot cancel workflow in terminal state '{state.status}'"
                )
            state.status       = WorkflowStatus.CANCELLED
            state.completed_at = time.time()
            self._instances[instance_id] = self._instances[instance_id].with_status(
                WorkflowStatus.CANCELLED
            )

    # ── step execution ────────────────────────────────────────────────────────

    def execute_step(self, instance_id: str, step_id: str) -> Any:
        """
        Execute a single step in the workflow instance.

        Returns the handler's return value.
        The step's ``on_success`` / ``on_failure`` pointer advances
        ``current_step_id`` in the instance state.
        """
        with self._lock:
            self._require_instance(instance_id)
            wf_id = self._instances[instance_id].workflow_id
            defn  = self._definitions.get(wf_id)
            state = self._states[instance_id]

        if defn is None:
            raise AIWorkflowNotFoundError(
                f"Definition missing for workflow instance '{instance_id}'"
            )

        step: Optional[WorkflowStep] = defn.get_step(step_id)
        if step is None:
            raise AIWorkflowNotFoundError(f"Step '{step_id}' not in workflow")

        with self._lock:
            state.step_statuses[step_id] = StepStatus.RUNNING
            handler = self._handlers.get(step.action)

        if handler is None:
            with self._lock:
                state.step_statuses[step_id] = StepStatus.FAILED
            raise AIWorkflowExecutionError(
                f"No handler registered for action '{step.action}'"
            )

        try:
            params = dict(step.parameters)
            result = handler(params)
            with self._lock:
                state.step_outputs[step_id]  = result
                state.step_statuses[step_id] = StepStatus.COMPLETED
                state.current_step_id        = step.on_success
                if step.on_success is None:
                    state.status       = WorkflowStatus.COMPLETED
                    state.completed_at = time.time()
                    self._instances[instance_id] = self._instances[instance_id].with_status(
                        WorkflowStatus.COMPLETED
                    )
            return result

        except Exception as exc:
            with self._lock:
                state.step_statuses[step_id] = StepStatus.FAILED
                state.error = str(exc)
                if step.on_failure is None:
                    state.status       = WorkflowStatus.FAILED
                    state.completed_at = time.time()
                    self._instances[instance_id] = self._instances[instance_id].with_status(
                        WorkflowStatus.FAILED
                    )
                else:
                    state.current_step_id = step.on_failure
            raise AIWorkflowExecutionError(
                f"Step '{step.name}' failed: {exc}"
            ) from exc

    # ── accessors ─────────────────────────────────────────────────────────────

    def get_instance(self, instance_id: str) -> WorkflowInstance:
        with self._lock:
            inst = self._instances.get(instance_id)
        if inst is None:
            raise AIWorkflowNotFoundError(f"Instance '{instance_id}' not found")
        return inst

    def get_state(self, instance_id: str) -> WorkflowState:
        with self._lock:
            state = self._states.get(instance_id)
        if state is None:
            raise AIWorkflowNotFoundError(
                f"State for instance '{instance_id}' not found"
            )
        return state

    def instance_count(self) -> int:
        with self._lock:
            return len(self._instances)

    def definition_count(self) -> int:
        with self._lock:
            return len(self._definitions)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _require_instance(self, instance_id: str) -> None:
        if instance_id not in self._instances:
            raise AIWorkflowNotFoundError(f"Instance '{instance_id}' not found")
