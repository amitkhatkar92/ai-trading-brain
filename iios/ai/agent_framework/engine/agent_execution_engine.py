"""
agent_execution_engine.py -- iios.ai.agent_framework.engine
============================================================
:class:`AgentExecutionEngine` — orchestrates task dispatch to agents.

Responsibilities
----------------
1. Locate the target agent in the registry.
2. Verify the agent is active and healthy.
3. Build an :class:`AgentExecutionContext`.
4. Delegate to the agent's ``execute_task()`` method.
5. Record metrics and publish task lifecycle events.

All A1–A4 gateway dependencies are optional injections — the engine works
without them; agents receive ``None`` for absent gateways.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
from typing import Any, Optional

from ..events.agent_event_bus import AgentEventBus
from ..events.agent_events    import (
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
)
from ..exceptions import AIAgentNotRunningError, AITaskExecutionError
from .agent_execution_context import AgentExecutionContext
from .agent_task               import AgentResult, AgentTask


class AgentExecutionEngine:
    """
    Task dispatch and execution orchestrator.

    Wired by :class:`AgentFrameworkContainer` with the shared registry and
    event bus.  All A1–A4 gateways are optional.

    Usage::

        engine = AgentExecutionEngine(registry=registry, event_bus=bus)
        result = engine.assign_task(task)
    """

    def __init__(
        self,
        registry:       Any,                  # AgentRegistry (avoid circular import)
        event_bus:      AgentEventBus,
        memory_gateway: Optional[Any] = None,  # A4 MemoryKnowledgeGateway
        prompt_gateway: Optional[Any] = None,  # A3 PromptContextGateway
        model_gateway:  Optional[Any] = None,  # A2 ModelManagementGateway
    ) -> None:
        self._registry       = registry
        self._event_bus      = event_bus
        self._memory_gateway = memory_gateway
        self._prompt_gateway = prompt_gateway
        self._model_gateway  = model_gateway

    # ── Public API ────────────────────────────────────────────────────────────

    def assign_task(self, task: AgentTask) -> AgentResult:
        """
        Dispatch *task* to the agent identified by ``task.agent_id``.

        Publishes :class:`TaskAssignedEvent`, :class:`TaskStartedEvent`,
        and either :class:`TaskCompletedEvent` or :class:`TaskFailedEvent`.
        Updates agent metrics via :meth:`BaseAIAgent.record_task_result`.

        Raises
        ------
        AIAgentNotFoundError   — agent not registered
        AIAgentNotRunningError — agent exists but is not active
        """
        agent = self._registry.get(task.agent_id)

        if not agent.is_active:
            raise AIAgentNotRunningError(task.agent_id)

        # Publish TASK_ASSIGNED
        self._event_bus.publish(
            TaskAssignedEvent.create(
                agent_id  = task.agent_id,
                task_id   = task.task_id,
                task_type = task.task_type,
                priority  = task.priority.value,
            )
        )

        # Update agent metrics: assigned
        agent.record_task_assigned()

        # Build context and execute
        context    = self.build_context(task.agent_id, task.task_id)
        started_at = time.time()

        self._event_bus.publish(TaskStartedEvent.create(task.agent_id, task.task_id))

        try:
            result = agent.execute_task(task, context)
        except Exception as exc:  # noqa: BLE001
            result = AgentResult.failure(task, str(exc), started_at)

        # Publish outcome event and update metrics
        if result.is_success():
            self._event_bus.publish(
                TaskCompletedEvent.create(
                    agent_id     = task.agent_id,
                    task_id      = task.task_id,
                    execution_ms = result.execution_ms,
                )
            )
            agent.record_task_completed(result.execution_ms)
        else:
            self._event_bus.publish(
                TaskFailedEvent.create(
                    agent_id      = task.agent_id,
                    task_id       = task.task_id,
                    error_message = result.error or "",
                )
            )
            agent.record_task_failed()

        return result

    def build_context(
        self,
        agent_id:  str,
        task_id:   str,
        **metadata: Any,
    ) -> AgentExecutionContext:
        """Build an :class:`AgentExecutionContext` for one task invocation."""
        return AgentExecutionContext.create(
            agent_id       = agent_id,
            task_id        = task_id,
            memory_gateway = self._memory_gateway,
            prompt_gateway = self._prompt_gateway,
            model_gateway  = self._model_gateway,
            **metadata,
        )
