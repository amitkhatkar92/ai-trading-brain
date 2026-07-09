"""iios/investment/investment_context.py
Thread-local session context for the Investment Intelligence Engine.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator

from iios.investment.investment_constants import InvestmentObjective, WorkflowStatus


@dataclass
class _Diagnostic:
    level:   str
    message: str
    stage:   str
    ts:      float = field(default_factory=time.time)


@dataclass
class InvestmentContextState:
    """Thread-local state for one investment pipeline execution."""

    session_id:    str               = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:     str               = ""
    current_stage: str               = ""
    depth:         int               = 0
    started_at:    float             = field(default_factory=time.time)
    _diagnostics:  list[_Diagnostic] = field(default_factory=list, repr=False)

    def add_diagnostic(self, level: str, message: str, stage: str = "") -> None:
        self._diagnostics.append(
            _Diagnostic(level, message, stage or self.current_stage)
        )

    def warnings(self) -> list[_Diagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "WARNING"]

    def errors(self) -> list[_Diagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000

    def to_dict(self) -> dict:
        return {
            "session_id":    self.session_id,
            "source_id":     self.source_id,
            "current_stage": self.current_stage,
            "elapsed_ms":    self.elapsed_ms(),
            "warnings":      len(self.warnings()),
            "errors":        len(self.errors()),
        }


_tls: threading.local = threading.local()


def get_investment_context() -> InvestmentContextState:
    if not hasattr(_tls, "ctx"):
        _tls.ctx = InvestmentContextState()
    return _tls.ctx  # type: ignore[return-value]


def reset_investment_context() -> None:
    if hasattr(_tls, "ctx"):
        del _tls.ctx


@contextmanager
def investment_session(
    source_id: str = "",
) -> Generator[InvestmentContextState, None, None]:
    ctx = InvestmentContextState(source_id=source_id)
    _tls.ctx = ctx
    try:
        yield ctx
    finally:
        if getattr(_tls, "ctx", None) is ctx:
            del _tls.ctx


@contextmanager
def inv_stage_scope(stage: str) -> Generator[InvestmentContextState, None, None]:
    ctx = get_investment_context()
    prev = ctx.current_stage
    ctx.current_stage = stage
    ctx.depth += 1
    try:
        yield ctx
    finally:
        ctx.current_stage = prev
        ctx.depth -= 1
