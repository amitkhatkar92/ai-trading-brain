"""
iios/knowledge/governance/governance_context.py
================================================
Thread-local governance context.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .governance_constants import SYSTEM_GOVERNANCE_ACTOR

__all__ = [
    "GovernanceContext",
    "get_governance_context",
    "reset_governance_context",
    "governance_operation",
    "current_governance_actor",
    "current_governance_operation_id",
]

_lock = threading.Lock()
_ctx: Optional["GovernanceContext"] = None


class GovernanceContext:
    """Thread-local context for governance engine operations."""

    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def actor(self) -> str:
        return getattr(self._local, "actor", SYSTEM_GOVERNANCE_ACTOR)

    @actor.setter
    def actor(self, value: str) -> None:
        self._local.actor = value

    @property
    def operation_id(self) -> Optional[str]:
        return getattr(self._local, "operation_id", None)

    @operation_id.setter
    def operation_id(self, value: Optional[str]) -> None:
        self._local.operation_id = value

    @contextmanager
    def operation(
        self,
        actor:        Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> Generator[None, None, None]:
        prev_actor = self.actor
        prev_op    = self.operation_id
        self.actor        = actor or SYSTEM_GOVERNANCE_ACTOR
        self.operation_id = operation_id or str(uuid.uuid4())
        try:
            yield
        finally:
            self.actor        = prev_actor
            self.operation_id = prev_op


def get_governance_context() -> GovernanceContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = GovernanceContext()
    return _ctx


def reset_governance_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


@contextmanager
def governance_operation(
    actor:        Optional[str] = None,
    operation_id: Optional[str] = None,
) -> Generator[None, None, None]:
    with get_governance_context().operation(actor=actor, operation_id=operation_id):
        yield


def current_governance_actor() -> str:
    return get_governance_context().actor


def current_governance_operation_id() -> Optional[str]:
    return get_governance_context().operation_id
