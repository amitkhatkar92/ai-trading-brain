"""iios/investment/portfolio/portfolio_context.py
Thread-local context for portfolio intelligence operations.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class PortfolioContextState:
    """Per-thread context for a portfolio analysis session."""

    session_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:  str   = ""
    stage:         str   = ""
    current_stage: str   = ""
    source_id:     str   = ""
    started_at:    float = field(default_factory=time.time)
    diagnostics:   list  = field(default_factory=list)
    metadata:      dict  = field(default_factory=dict)

    def add_diagnostic(self, level: str, message: str) -> None:
        self.diagnostics.append((level, message))

    def warnings(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "WARNING"]

    def errors(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "request_id":    self.request_id,
            "portfolio_id":  self.portfolio_id,
            "stage":         self.stage,
            "current_stage": self.current_stage,
            "source_id":     self.source_id,
            "started_at":    self.started_at,
            "elapsed_ms":    self.elapsed_ms(),
        }


_local: threading.local = threading.local()


def get_portfolio_context() -> PortfolioContextState:
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = PortfolioContextState()
    return _local.ctx


def reset_portfolio_context() -> None:
    _local.ctx = None


@contextmanager
def portfolio_session(
    request_id:   str  = "",
    metadata:     dict | None = None,
    portfolio_id: str  = "",
    source_id:    str  = "",
) -> Iterator[PortfolioContextState]:
    prev = getattr(_local, "ctx", None)
    ctx  = PortfolioContextState(
        request_id  = request_id or str(uuid.uuid4()),
        portfolio_id = portfolio_id,
        source_id   = source_id,
        metadata    = metadata or {},
    )
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = prev


@contextmanager
def portfolio_stage_scope(stage: str) -> Iterator[PortfolioContextState]:
    ctx            = get_portfolio_context()
    prev_stage     = ctx.stage
    prev_curr      = ctx.current_stage
    ctx.stage      = stage
    ctx.current_stage = stage
    try:
        yield ctx
    finally:
        ctx.stage         = prev_stage
        ctx.current_stage = prev_curr
