"""
iios/knowledge/search/search_context.py
==========================================
Thread-local context for the Knowledge Indexing & Search Engine.
Tracks current actor ID and search operation ID per thread.
"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .search_constants import SYSTEM_SEARCH_ACTOR

__all__ = [
    "SearchContext",
    "get_search_context",
    "reset_search_context",
    "current_search_actor",
    "current_search_operation_id",
    "search_operation",
]

_local    = threading.local()
_ctx_lock = threading.Lock()
_ctx:     Optional["SearchContext"] = None


class _ThreadState:
    actor_id:     str = SYSTEM_SEARCH_ACTOR
    operation_id: str = ""
    operation:    str = ""


def _get_state() -> _ThreadState:
    if not hasattr(_local, "state"):
        _local.state = _ThreadState()
    return _local.state


class SearchContext:
    """Thread-local context for search operations."""

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
        actor_id: str = SYSTEM_SEARCH_ACTOR,
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


def current_search_actor() -> str:
    return _get_state().actor_id


def current_search_operation_id() -> str:
    return _get_state().operation_id


@contextmanager
def search_operation(
    name:     str,
    actor_id: str = SYSTEM_SEARCH_ACTOR,
) -> Generator[str, None, None]:
    ctx = get_search_context()
    with ctx.operation(name, actor_id=actor_id) as op_id:
        yield op_id


def get_search_context() -> SearchContext:
    global _ctx
    with _ctx_lock:
        if _ctx is None:
            _ctx = SearchContext()
        return _ctx


def reset_search_context() -> None:
    global _ctx
    with _ctx_lock:
        if _ctx is not None:
            _ctx.reset_thread()
        _ctx = None
