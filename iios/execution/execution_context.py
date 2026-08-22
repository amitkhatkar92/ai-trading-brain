"""iios/execution/execution_context.py"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class ExecutionContextState:
    """Immutable-ish snapshot of the current execution request context."""

    request_id:   str = field(default_factory=lambda: str(uuid.uuid4()))
    stage:        str = "idle"
    current_stage: str = ""

    # Optional — populated as work progresses.
    execution_id: str = ""
    session_id:   str = ""
    strategy_id:  str = ""
    portfolio_id: str = ""
    ticker:       str = ""

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "stage":         self.stage,
            "current_stage": self.current_stage,
            "execution_id":  self.execution_id,
            "session_id":    self.session_id,
            "strategy_id":   self.strategy_id,
            "portfolio_id":  self.portfolio_id,
            "ticker":        self.ticker,
            "metadata":      dict(self.metadata),
        }


_local = threading.local()
_lock:  threading.Lock = threading.Lock()


def get_execution_context() -> ExecutionContextState:
    """Return the context for the current thread, creating one if absent."""
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = ExecutionContextState()
    return _local.ctx


def reset_execution_context() -> None:
    """Reset the current thread's context to a fresh state."""
    _local.ctx = ExecutionContextState()


@contextmanager
def execution_session(
    request_id: str | None = None,
    *,
    metadata: dict[str, Any] | None = None,
) -> Generator[ExecutionContextState, None, None]:
    """
    Context manager that installs a fresh ExecutionContextState for the
    duration of a block, then restores the previous state.
    """
    previous = getattr(_local, "ctx", None)
    ctx = ExecutionContextState(
        request_id=request_id or str(uuid.uuid4()),
        metadata=metadata or {},
    )
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = previous


@contextmanager
def execution_stage_scope(
    stage_name: str,
) -> Generator[ExecutionContextState, None, None]:
    """
    Narrow context manager that records the current stage name.

    Yields the active context with ``current_stage`` updated.
    """
    ctx = get_execution_context()
    previous_stage = ctx.current_stage
    ctx.current_stage = stage_name
    ctx.stage         = stage_name
    try:
        yield ctx
    finally:
        ctx.current_stage = previous_stage
        ctx.stage         = previous_stage or "idle"
