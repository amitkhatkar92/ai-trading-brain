"""iios/investment/strategy/strategy_context.py
Thread-local context for strategy intelligence operations.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class StrategyContextState:
    """Per-thread context for a strategy analysis or selection session."""

    session_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:   str            = ""
    stage:         str            = ""
    current_stage: str            = ""
    source_id:     str            = ""
    market_regime: str            = ""
    started_at:    float          = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)
    diagnostics:   list[tuple[str, str]] = field(default_factory=list)

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
            "strategy_id":   self.strategy_id,
            "stage":         self.stage,
            "current_stage": self.current_stage,
            "source_id":     self.source_id,
            "market_regime": self.market_regime,
            "started_at":    self.started_at,
            "elapsed_ms":    self.elapsed_ms(),
        }


_local: threading.local = threading.local()


def get_strategy_context() -> StrategyContextState:
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = StrategyContextState()
    return _local.ctx


def reset_strategy_context() -> None:
    _local.ctx = None


@contextmanager
def strategy_session(
    request_id:    str            = "",
    strategy_id:   str            = "",
    metadata:      dict | None    = None,
    market_regime: str            = "",
) -> Iterator[StrategyContextState]:
    prev = getattr(_local, "ctx", None)
    ctx  = StrategyContextState(
        request_id    = request_id or str(uuid.uuid4()),
        strategy_id   = strategy_id,
        market_regime = market_regime,
        metadata      = metadata or {},
    )
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = prev


@contextmanager
def strategy_stage_scope(stage: str) -> Iterator[StrategyContextState]:
    ctx        = get_strategy_context()
    prev_stage = ctx.stage
    prev_curr  = ctx.current_stage
    ctx.stage         = stage
    ctx.current_stage = stage
    try:
        yield ctx
    finally:
        ctx.stage         = prev_stage
        ctx.current_stage = prev_curr
