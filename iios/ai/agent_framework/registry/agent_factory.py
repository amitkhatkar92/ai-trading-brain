"""
agent_factory.py -- iios.ai.agent_framework.registry
=====================================================
:class:`AgentFactory` — creates :class:`BaseAIAgent` instances from an
:class:`AgentSpec` using registered builder functions.

Builders are callables with signature ``(spec: AgentSpec) -> BaseAIAgent``.
The factory dispatches on ``spec.agent_type``.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from typing import Callable, Dict, List

from ..base.base_agent  import BaseAIAgent
from ..core.agent_spec  import AgentSpec
from ..exceptions       import AIRegistrationFailedError, AIAgentNotFoundError


Builder = Callable[[AgentSpec], BaseAIAgent]


class AgentFactory:
    """
    Registry of builder functions keyed by ``agent_type`` string.

    Usage::

        factory = AgentFactory()
        factory.register_builder("MarketAnalyst", lambda spec: MarketAnalystAgent(spec))
        agent = factory.create(spec)
    """

    def __init__(self) -> None:
        self._builders: Dict[str, Builder] = {}

    # ── Builder registration ──────────────────────────────────────────────────

    def register_builder(self, agent_type: str, builder: Builder) -> None:
        """
        Register *builder* for *agent_type*.

        Overwrites any previously registered builder for the same type.
        """
        if not callable(builder):
            raise AIRegistrationFailedError(
                f"Builder for {agent_type!r} must be callable"
            )
        self._builders[agent_type] = builder

    def unregister_builder(self, agent_type: str) -> None:
        """Remove the builder for *agent_type*.  No-op if not registered."""
        self._builders.pop(agent_type, None)

    # ── Agent creation ────────────────────────────────────────────────────────

    def create(self, spec: AgentSpec) -> BaseAIAgent:
        """
        Instantiate an agent for *spec* using the registered builder.

        Raises :class:`AIAgentNotFoundError` if no builder is registered for
        ``spec.agent_type``.
        """
        builder = self._builders.get(spec.agent_type)
        if builder is None:
            raise AIAgentNotFoundError(
                f"No builder registered for agent_type={spec.agent_type!r}"
            )
        try:
            return builder(spec)
        except Exception as exc:
            raise AIRegistrationFailedError(
                f"Builder for {spec.agent_type!r} raised: {exc}"
            ) from exc

    def can_create(self, agent_type: str) -> bool:
        """Return True if a builder is registered for *agent_type*."""
        return agent_type in self._builders

    def available_types(self) -> List[str]:
        """Return all registered agent type strings."""
        return list(self._builders.keys())
