"""
agent_framework_container.py -- iios.ai.agent_framework.container
===================================================================
:class:`AgentFrameworkContainer` — DI composition root for A5.

Wires every A5 component into a coherent unit; ``build()`` is idempotent.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from typing import Optional

from ..engine.agent_execution_engine  import AgentExecutionEngine
from ..events.agent_event_bus         import AgentEventBus
from ..manager.agent_manager          import AgentManager
from ..policy.capability_policy       import CapabilityPolicy, DefaultCapabilityPolicy
from ..policy.execution_policy        import ExecutionPolicy, DefaultExecutionPolicy
from ..policy.permission_policy       import PermissionPolicy, DefaultPermissionPolicy
from ..registry.agent_factory         import AgentFactory
from ..registry.agent_registry        import AgentRegistry
from ..specialists.specialist_agents  import ALL_SPECIALIST_CLASSES


class AgentFrameworkContainer:
    """
    DI composition root for the A5 Agent Framework.

    Usage::

        container = AgentFrameworkContainer()
        container.build()
        container.agent_manager.start_agent(agent_id)
    """

    def __init__(
        self,
        execution_policy:  Optional[ExecutionPolicy]  = None,
        permission_policy: Optional[PermissionPolicy] = None,
        capability_policy: Optional[CapabilityPolicy] = None,
    ) -> None:
        self._execution_policy_arg  = execution_policy
        self._permission_policy_arg = permission_policy
        self._capability_policy_arg = capability_policy

        self._built: bool = False

        # Components (set by build())
        self._event_bus:          Optional[AgentEventBus]          = None
        self._registry:           Optional[AgentRegistry]          = None
        self._factory:            Optional[AgentFactory]           = None
        self._agent_manager:      Optional[AgentManager]           = None
        self._execution_engine:   Optional[AgentExecutionEngine]   = None
        self._execution_policy:   Optional[ExecutionPolicy]        = None
        self._permission_policy:  Optional[PermissionPolicy]       = None
        self._capability_policy:  Optional[CapabilityPolicy]       = None

    def build(self) -> None:
        """Wire all components.  Safe to call multiple times (idempotent)."""
        if self._built:
            return

        self._event_bus  = AgentEventBus()
        self._registry   = AgentRegistry()
        self._factory    = AgentFactory()

        # Register specialist builders
        for cls in ALL_SPECIALIST_CLASSES:
            self._factory.register_builder(cls.AGENT_TYPE, cls)

        self._agent_manager = AgentManager(
            registry  = self._registry,
            factory   = self._factory,
            event_bus = self._event_bus,
        )
        self._execution_engine = AgentExecutionEngine(
            registry  = self._registry,
            event_bus = self._event_bus,
        )

        self._execution_policy  = self._execution_policy_arg  or DefaultExecutionPolicy()
        self._permission_policy = self._permission_policy_arg or DefaultPermissionPolicy()
        self._capability_policy = self._capability_policy_arg or DefaultCapabilityPolicy()

        self._built = True

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> AgentEventBus:
        self._assert_built()
        return self._event_bus  # type: ignore[return-value]

    @property
    def registry(self) -> AgentRegistry:
        self._assert_built()
        return self._registry  # type: ignore[return-value]

    @property
    def factory(self) -> AgentFactory:
        self._assert_built()
        return self._factory  # type: ignore[return-value]

    @property
    def agent_manager(self) -> AgentManager:
        self._assert_built()
        return self._agent_manager  # type: ignore[return-value]

    @property
    def execution_engine(self) -> AgentExecutionEngine:
        self._assert_built()
        return self._execution_engine  # type: ignore[return-value]

    @property
    def execution_policy(self) -> ExecutionPolicy:
        self._assert_built()
        return self._execution_policy  # type: ignore[return-value]

    @property
    def permission_policy(self) -> PermissionPolicy:
        self._assert_built()
        return self._permission_policy  # type: ignore[return-value]

    @property
    def capability_policy(self) -> CapabilityPolicy:
        self._assert_built()
        return self._capability_policy  # type: ignore[return-value]

    def _assert_built(self) -> None:
        if not self._built:
            raise RuntimeError(
                "AgentFrameworkContainer has not been built. Call build() first."
            )
