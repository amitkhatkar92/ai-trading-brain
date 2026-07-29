"""
permission_policy.py -- iios.ai.agent_framework.policy
========================================================
:class:`PermissionPolicy`          — base protocol.
:class:`DefaultPermissionPolicy`   — allow all (no enforcement).
:class:`StrictPermissionPolicy`    — enforce :class:`AgentPermissions` checks.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..core.agent_permissions import PermissionLevel
from ..exceptions              import AIPermissionDeniedError

if TYPE_CHECKING:
    from ..base.base_agent import BaseAIAgent


class PermissionPolicy(ABC):
    """Abstract permission policy evaluated before resource access."""

    @abstractmethod
    def check(
        self,
        agent:    "BaseAIAgent",
        resource: str,
        level:    PermissionLevel,
    ) -> None:
        """Raise :class:`AIPermissionDeniedError` if access is not permitted."""


class DefaultPermissionPolicy(PermissionPolicy):
    """Permissive policy — never blocks any access."""

    def check(
        self,
        agent:    "BaseAIAgent",
        resource: str,
        level:    PermissionLevel,
    ) -> None:
        pass


class StrictPermissionPolicy(PermissionPolicy):
    """
    Enforce the agent's :class:`AgentPermissions` for every resource access.

    Raises :class:`AIPermissionDeniedError` when the agent's permission set
    does not satisfy the required level.
    """

    def check(
        self,
        agent:    "BaseAIAgent",
        resource: str,
        level:    PermissionLevel,
    ) -> None:
        agent.spec.permissions.assert_permission(resource, level)
