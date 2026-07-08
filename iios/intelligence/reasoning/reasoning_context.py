"""
iios/intelligence/reasoning/reasoning_context.py
=================================================
Thread-local execution context for the Reasoning & Debate Engine.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .reasoning_constants import ReasoningType


# ── Diagnostic model ──────────────────────────────────────────────────────────

@dataclass
class ReasoningDiagnostic:
    level:   str
    message: str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":   self.level,
            "message": self.message,
            "source":  self.source,
            "ts":      self.ts,
        }


# ── Per-thread state ──────────────────────────────────────────────────────────

class ReasoningContextState:
    """Mutable per-thread context for an active reasoning chain."""

    def __init__(self) -> None:
        self.session_id:     str | None            = None
        self.debate_id:      str | None            = None
        self.reasoner_id:    str | None            = None
        self.reasoning_type: ReasoningType | None  = None
        self.depth:          int                   = 0
        self.started_at:     float                 = time.time()
        self._diagnostics:   list[ReasoningDiagnostic] = []

    # -- Diagnostics ───────────────────────────────────────────────────────────

    def add_diagnostic(self, level: str, message: str, source: str) -> None:
        self._diagnostics.append(
            ReasoningDiagnostic(level=level, message=message, source=source)
        )

    def warnings(self) -> list[ReasoningDiagnostic]:
        return [d for d in self._diagnostics if d.level == "WARNING"]

    def errors(self) -> list[ReasoningDiagnostic]:
        return [d for d in self._diagnostics if d.level == "ERROR"]

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":     self.session_id,
            "debate_id":      self.debate_id,
            "reasoner_id":    self.reasoner_id,
            "reasoning_type": (
                self.reasoning_type.value if self.reasoning_type else None
            ),
            "depth":          self.depth,
            "elapsed_s":      round(self.elapsed_s, 4),
            "diagnostics":    [d.to_dict() for d in self._diagnostics],
        }


# ── Thread-local manager ──────────────────────────────────────────────────────

_CONTEXT_LOCAL: threading.local = threading.local()
_LOCK = threading.Lock()
_INSTANCE: _ReasoningContextManager | None = None


class _ReasoningContextManager:
    """Thin wrapper providing context-manager helpers over thread-local state."""

    @staticmethod
    def _current() -> ReasoningContextState:
        if not hasattr(_CONTEXT_LOCAL, "state"):
            _CONTEXT_LOCAL.state = ReasoningContextState()
        return _CONTEXT_LOCAL.state

    def get(self) -> ReasoningContextState:
        return self._current()

    @contextmanager
    def session(
        self,
        session_id:     str,
        reasoner_id:    str | None            = None,
        reasoning_type: ReasoningType | None  = None,
    ) -> Generator[ReasoningContextState, None, None]:
        ctx = self._current()
        saved = (
            ctx.session_id, ctx.reasoner_id,
            ctx.reasoning_type, ctx.depth,
        )
        ctx.session_id     = session_id
        ctx.reasoner_id    = reasoner_id
        ctx.reasoning_type = reasoning_type
        ctx.depth          = saved[3] + 1
        ctx.started_at     = time.time()
        try:
            yield ctx
        finally:
            ctx.session_id, ctx.reasoner_id, ctx.reasoning_type, ctx.depth = saved

    @contextmanager
    def debate(
        self,
        debate_id: str,
    ) -> Generator[ReasoningContextState, None, None]:
        ctx  = self._current()
        prev = ctx.debate_id
        ctx.debate_id = debate_id
        try:
            yield ctx
        finally:
            ctx.debate_id = prev


# ── Singletons ─────────────────────────────────────────────────────────────────

def _get_manager() -> _ReasoningContextManager:
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _ReasoningContextManager()
    return _INSTANCE


def get_reasoning_context() -> ReasoningContextState:
    return _get_manager().get()


def reset_reasoning_context() -> None:
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
    if hasattr(_CONTEXT_LOCAL, "state"):
        del _CONTEXT_LOCAL.state


# ── Module-level convenience context managers ─────────────────────────────────

@contextmanager
def reasoning_session_scope(
    session_id:     str,
    reasoner_id:    str | None            = None,
    reasoning_type: ReasoningType | None  = None,
) -> Generator[ReasoningContextState, None, None]:
    with _get_manager().session(session_id, reasoner_id, reasoning_type) as ctx:
        yield ctx


@contextmanager
def debate_scope(debate_id: str) -> Generator[ReasoningContextState, None, None]:
    with _get_manager().debate(debate_id) as ctx:
        yield ctx
