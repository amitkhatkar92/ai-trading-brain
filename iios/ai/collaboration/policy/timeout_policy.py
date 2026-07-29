"""
timeout_policy.py -- iios.ai.collaboration.policy
===================================================
Abstract :class:`TimeoutPolicy` and :class:`DefaultTimeoutPolicy`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from ..core.collaboration_context import CollaborationContext


class TimeoutPolicy(ABC):
    """Abstract policy for session and round timeout logic."""

    @abstractmethod
    def is_session_timed_out(self, ctx: CollaborationContext, started_at: float) -> bool: ...

    @abstractmethod
    def default_session_timeout_s(self) -> Optional[float]: ...

    @abstractmethod
    def default_round_timeout_s(self) -> Optional[float]: ...


class DefaultTimeoutPolicy(TimeoutPolicy):
    """
    Default timeout policy.

    * Session timeout: 3 600 seconds (1 hour)
    * Round timeout: 300 seconds (5 minutes)
    """

    _SESSION_TIMEOUT_S = 3_600.0
    _ROUND_TIMEOUT_S   = 300.0

    def is_session_timed_out(self, ctx: CollaborationContext, started_at: float) -> bool:
        return (time.time() - started_at) > self._SESSION_TIMEOUT_S

    def default_session_timeout_s(self) -> Optional[float]:
        return self._SESSION_TIMEOUT_S

    def default_round_timeout_s(self) -> Optional[float]:
        return self._ROUND_TIMEOUT_S
