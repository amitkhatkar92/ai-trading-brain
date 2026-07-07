"""
iios/knowledge/graph/graph_context.py
"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .graph_constants import SYSTEM_GRAPH_ACTOR

__all__ = [
    "GraphContext",
    "get_graph_context",
    "reset_graph_context",
    "current_graph_actor",
    "current_graph_operation_id",
    "graph_operation",
]

_local    = threading.local()
_mgr_lock = threading.Lock()
_ctx: Optional["GraphContext"] = None


class _ThreadState:
    actor_id:     str = SYSTEM_GRAPH_ACTOR
    operation_id: str = ""
    operation:    str = ""


def _get_state() -> _ThreadState:
    if not hasattr(_local, "state"):
        _local.state = _ThreadState()
    return _local.state


class GraphContext:
    """Thread-local context for knowledge graph operations."""

    @property
    def actor_id(self) -> str:
        return _get_state().actor_id

    @property
    def operation_id(self) -> str:
        return _get_state().operation_id

    @contextmanager
    def operation(
        self,
        name:     str,
        actor_id: str = SYSTEM_GRAPH_ACTOR,
    ) -> Generator[str, None, None]:
        state = _get_state()
        prev_actor = state.actor_id
        prev_op_id = state.operation_id
        prev_op    = state.operation

        state.actor_id     = actor_id
        state.operation_id = str(uuid.uuid4())
        state.operation    = name
        try:
            yield state.operation_id
        finally:
            state.actor_id     = prev_actor
            state.operation_id = prev_op_id
            state.operation    = prev_op

    def reset_thread(self) -> None:
        if hasattr(_local, "state"):
            _local.state = _ThreadState()


def current_graph_actor() -> str:
    return _get_state().actor_id


def current_graph_operation_id() -> str:
    return _get_state().operation_id


@contextmanager
def graph_operation(
    name:     str,
    actor_id: str = SYSTEM_GRAPH_ACTOR,
) -> Generator[str, None, None]:
    ctx = get_graph_context()
    with ctx.operation(name, actor_id=actor_id) as op_id:
        yield op_id


def get_graph_context() -> GraphContext:
    global _ctx
    with _mgr_lock:
        if _ctx is None:
            _ctx = GraphContext()
        return _ctx


def reset_graph_context() -> None:
    global _ctx
    with _mgr_lock:
        if _ctx is not None:
            _ctx.reset_thread()
        _ctx = None
