"""iios/investment/market/market_context.py
Thread-local context state for market intelligence operations.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class MarketContextState:
    """Per-thread context for a market analysis session."""

    session_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:     str   = ""
    current_stage: str   = ""
    source_id:     str   = ""
    started_at:    float = field(default_factory=time.time)
    diagnostics:   list  = field(default_factory=list)  # list[tuple[str, str]]

    def add_diagnostic(self, level: str, message: str) -> None:
        self.diagnostics.append((level, message))

    def warnings(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "WARNING"]

    def errors(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "market_id":     self.market_id,
            "current_stage": self.current_stage,
            "source_id":     self.source_id,
            "started_at":    self.started_at,
            "elapsed_ms":    self.elapsed_ms(),
        }


_local: threading.local = threading.local()


def get_market_context() -> MarketContextState:
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = MarketContextState()
    return _local.ctx


def reset_market_context() -> None:
    _local.ctx = None


@contextmanager
def market_session(
    market_id: str = "",
    source_id: str = "",
) -> Iterator[MarketContextState]:
    """Context manager that creates a fresh market analysis session."""
    prev = getattr(_local, "ctx", None)
    ctx = MarketContextState(market_id=market_id, source_id=source_id)
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = prev


@contextmanager
def market_stage_scope(stage: str) -> Iterator[None]:
    """Context manager that sets the current analysis stage."""
    ctx = get_market_context()
    prev = ctx.current_stage
    ctx.current_stage = stage
    try:
        yield
    finally:
        ctx.current_stage = prev
