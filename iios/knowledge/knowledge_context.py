"""
iios/knowledge/knowledge_context.py
=====================================
Thread-local context for the current knowledge operation.
Provides principal identity, transaction tracking, and audit trail hooks.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .knowledge_constants import SYSTEM_OWNER, ANONYMOUS_OWNER

__all__ = [
    "KnowledgeContext",
    "get_knowledge_context",
    "reset_knowledge_context",
    "current_actor",
    "current_operation_id",
    "knowledge_operation",
]

_local = threading.local()
_mgr_lock = threading.Lock()
_ctx: Optional["KnowledgeContext"] = None


class _ThreadState:
    actor_id:     str = ANONYMOUS_OWNER
    operation_id: str = ""
    operation:    str = ""
    source:       str = ""


def _get_state() -> _ThreadState:
    if not hasattr(_local, "state"):
        _local.state = _ThreadState()
    return _local.state


class KnowledgeContext:
    """Manages thread-local state for knowledge operations.

    Usage::

        ctx = get_knowledge_context()
        with ctx.operation("write", actor_id="user:alice"):
            # current_actor() == "user:alice"
            repo.add(record)
    """

    @property
    def actor_id(self) -> str:
        return _get_state().actor_id

    @property
    def operation_id(self) -> str:
        return _get_state().operation_id

    @property
    def operation(self) -> str:
        return _get_state().operation

    @contextmanager
    def operation(
        self,
        operation_name: str,
        actor_id: str = SYSTEM_OWNER,
        source: str = "",
    ) -> Generator[str, None, None]:
        """Context manager that sets actor and operation tracking."""
        state = _get_state()
        prev_actor    = state.actor_id
        prev_op_id    = state.operation_id
        prev_op       = state.operation
        prev_source   = state.source

        state.actor_id     = actor_id
        state.operation_id = str(uuid.uuid4())
        state.operation    = operation_name
        state.source       = source
        try:
            yield state.operation_id
        finally:
            state.actor_id     = prev_actor
            state.operation_id = prev_op_id
            state.operation    = prev_op
            state.source       = prev_source

    def system_operation(self, name: str = "system") -> "contextmanager":
        return self.operation(name, actor_id=SYSTEM_OWNER)

    def reset_thread(self) -> None:
        if hasattr(_local, "state"):
            _local.state = _ThreadState()


def current_actor() -> str:
    return _get_state().actor_id


def current_operation_id() -> str:
    return _get_state().operation_id


@contextmanager
def knowledge_operation(
    name: str,
    actor_id: str = SYSTEM_OWNER,
    source: str = "",
) -> Generator[str, None, None]:
    """Shortcut context manager."""
    ctx = get_knowledge_context()
    with ctx.operation(name, actor_id=actor_id, source=source) as op_id:
        yield op_id


def get_knowledge_context() -> KnowledgeContext:
    global _ctx
    with _mgr_lock:
        if _ctx is None:
            _ctx = KnowledgeContext()
        return _ctx


def reset_knowledge_context() -> None:
    global _ctx
    with _mgr_lock:
        if _ctx is not None:
            _ctx.reset_thread()
        _ctx = None
