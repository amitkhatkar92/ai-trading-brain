"""iios/execution/orders/order_context.py

Thread-local request context for OMS operations.

Usage
-----
    with order_session(request_id="req-123") as ctx:
        ctx.portfolio_id = "P001"
        ...

    with order_stage_scope("validation") as ctx:
        ...
"""
from __future__ import annotations

import contextlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class OrderContextState:
    """Mutable thread-local state for one OMS operation."""

    session_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:      str   = ""
    portfolio_id:  str   = ""
    strategy_id:   str   = ""
    stage:         str   = ""
    current_stage: str   = ""
    actor:         str   = "oms"
    started_at:    float = field(default_factory=time.time)
    diagnostics:   list[str]       = field(default_factory=list)
    metadata:      dict[str, Any]  = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0


# ── Thread-local storage ──────────────────────────────────────────────────────

_local: threading.local = threading.local()


def get_order_context() -> OrderContextState | None:
    """Return the current thread's OMS context, or None if not set."""
    return getattr(_local, "context", None)


def set_order_context(ctx: OrderContextState) -> None:
    _local.context = ctx


def clear_order_context() -> None:
    _local.context = None


def require_order_context() -> OrderContextState:
    """Return the active context; raises RuntimeError if none is set."""
    ctx = get_order_context()
    if ctx is None:
        raise RuntimeError("No active order context; wrap call in order_session()")
    return ctx


# ── Context managers ──────────────────────────────────────────────────────────

@contextlib.contextmanager
def order_session(
    request_id: str = "",
    metadata: dict[str, Any] | None = None,
    actor: str = "oms",
) -> Generator[OrderContextState, None, None]:
    """Open a top-level OMS request context."""
    ctx = OrderContextState(
        request_id=request_id or str(uuid.uuid4()),
        actor=actor,
        metadata=metadata or {},
    )
    set_order_context(ctx)
    try:
        yield ctx
    finally:
        clear_order_context()


@contextlib.contextmanager
def order_stage_scope(stage: str) -> Generator[OrderContextState, None, None]:
    """Narrow the current context to a named processing stage."""
    ctx = get_order_context()
    created = ctx is None
    if created:
        ctx = OrderContextState()
        set_order_context(ctx)
    prev_stage = ctx.stage
    ctx.stage = stage
    ctx.current_stage = stage
    try:
        yield ctx
    finally:
        ctx.stage = prev_stage
        ctx.current_stage = prev_stage
        if created:
            clear_order_context()
