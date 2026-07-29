"""
agent_execution_context.py -- iios.ai.agent_framework.engine
=============================================================
:class:`AgentExecutionContext` — immutable execution context injected into
every agent task call.

The context provides the agent with access to the A1–A4 infrastructure
(memory, prompt, model) via optional gateway references that are wired
at call time by the :class:`AgentExecutionEngine`.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class AgentExecutionContext:
    """
    Immutable context injected into each ``execute_task()`` call.

    Gateway fields are typed as ``Optional[Any]`` to avoid A5 importing
    concrete A1–A4 gateway classes at module load time.  Type-check with
    ``isinstance(ctx.memory_gateway, MemoryKnowledgeGateway)`` where needed.

    Fields
    ------
    context_id      — UUID for this particular execution invocation
    agent_id        — ID of the executing agent
    task_id         — ID of the task being executed
    created_at      — wall-clock timestamp
    memory_gateway  — A4 :class:`MemoryKnowledgeGateway` or None
    prompt_gateway  — A3 :class:`PromptContextGateway` or None
    model_gateway   — A2 :class:`ModelManagementGateway` or None
    metadata        — arbitrary caller-supplied key-value pairs
    """

    context_id:     str
    agent_id:       str
    task_id:        str
    created_at:     float
    memory_gateway: Optional[Any]   # MemoryKnowledgeGateway (A4)
    prompt_gateway: Optional[Any]   # PromptContextGateway   (A3)
    model_gateway:  Optional[Any]   # ModelManagementGateway (A2)
    metadata:       FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        agent_id:       str,
        task_id:        str,
        *,
        memory_gateway: Optional[Any] = None,
        prompt_gateway: Optional[Any] = None,
        model_gateway:  Optional[Any] = None,
        **metadata: Any,
    ) -> "AgentExecutionContext":
        """
        Build a context for one task invocation.

        Example::

            ctx = AgentExecutionContext.create(
                agent_id       = agent.agent_id,
                task_id        = task.task_id,
                memory_gateway = memory_gw,
            )
        """
        return cls(
            context_id     = str(uuid.uuid4()),
            agent_id       = agent_id,
            task_id        = task_id,
            created_at     = time.time(),
            memory_gateway = memory_gateway,
            prompt_gateway = prompt_gateway,
            model_gateway  = model_gateway,
            metadata       = frozenset(metadata.items()),
        )

    def get_meta(self, key: str, default: Any = None) -> Any:
        """Retrieve a metadata value by key."""
        for k, v in self.metadata:
            if k == key:
                return v
        return default

    @property
    def has_memory(self) -> bool:
        return self.memory_gateway is not None

    @property
    def has_prompt(self) -> bool:
        return self.prompt_gateway is not None

    @property
    def has_model(self) -> bool:
        return self.model_gateway is not None
