"""
agent_config.py -- iios.ai.agent_framework.core
================================================
:class:`AgentConfiguration` — immutable, versioned key-value configuration
for a single agent.

All mutation returns a *new* instance with an incremented version counter
so configuration history can be tracked without mutable state.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, FrozenSet, Tuple


@dataclass(frozen=True)
class AgentConfiguration:
    """
    Immutable configuration envelope for one agent.

    ``settings`` is stored as a frozenset of ``(key, value)`` tuples to
    guarantee immutability.  Use :meth:`get` for individual lookups and
    :meth:`with_settings` to derive an updated configuration.
    """

    config_id:  str
    agent_id:   str
    settings:   FrozenSet[Tuple[str, Any]]
    created_at: float
    version:    int

    @classmethod
    def create(cls, agent_id: str, **settings: Any) -> "AgentConfiguration":
        """
        Create a fresh configuration from keyword arguments.

        Example::

            cfg = AgentConfiguration.create(
                agent_id="abc-123",
                max_retries=3,
                timeout_ms=5000,
            )
        """
        return cls(
            config_id  = str(uuid.uuid4()),
            agent_id   = agent_id,
            settings   = frozenset(settings.items()),
            created_at = time.time(),
            version    = 1,
        )

    @classmethod
    def empty(cls, agent_id: str) -> "AgentConfiguration":
        """Return a configuration with no settings."""
        return cls.create(agent_id)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value by key, or *default* if absent."""
        for k, v in self.settings:
            if k == key:
                return v
        return default

    def as_dict(self) -> dict:
        """Return a plain ``dict`` copy of all settings."""
        return dict(self.settings)

    def with_settings(self, **new_settings: Any) -> "AgentConfiguration":
        """
        Return a new :class:`AgentConfiguration` with *new_settings* merged
        in, bumping the version counter.

        Existing keys are overwritten; new keys are added; no key is removed.
        """
        merged = dict(self.settings)
        merged.update(new_settings)
        return AgentConfiguration(
            config_id  = str(uuid.uuid4()),
            agent_id   = self.agent_id,
            settings   = frozenset(merged.items()),
            created_at = self.created_at,
            version    = self.version + 1,
        )
