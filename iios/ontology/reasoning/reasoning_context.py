"""
iios/ontology/reasoning/reasoning_context.py
=============================================
Thread-local context for in-flight reasoning operations.

Singleton: get_reasoning_context() / reset_reasoning_context()
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from .reasoning_constants import (
    ReasoningType,
    ReasoningPhase,
    SYSTEM_REASONING_ACTOR,
)

__all__ = [
    "ReasoningDiagnostic",
    "ReasoningContext",
    "get_reasoning_context",
    "reset_reasoning_context",
    "reasoning_session",
]


@dataclass
class ReasoningDiagnostic:
    level:   str
    message: str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"level": self.level, "message": self.message, "source": self.source}


class _TLS(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self._session_id:    Optional[str]          = None
        self._actor:         str                    = SYSTEM_REASONING_ACTOR
        self._reasoning_type: Optional[ReasoningType] = None
        self._phase:         Optional[ReasoningPhase] = None
        self._depth:         int                    = 0
        self._started_at:    float                  = 0.0
        self._diagnostics:   list[ReasoningDiagnostic] = []


_tls = _TLS()


class ReasoningContext:
    """Thread-local context tracking for the reasoning engine."""

    @property
    def session_id(self) -> Optional[str]:
        return _tls._session_id

    @property
    def actor(self) -> str:
        return _tls._actor

    @property
    def reasoning_type(self) -> Optional[ReasoningType]:
        return _tls._reasoning_type

    @property
    def phase(self) -> Optional[ReasoningPhase]:
        return _tls._phase

    @property
    def depth(self) -> int:
        return _tls._depth

    @property
    def started_at(self) -> float:
        return _tls._started_at

    @property
    def diagnostics(self) -> list[ReasoningDiagnostic]:
        return list(_tls._diagnostics)

    def elapsed_ms(self) -> float:
        return (time.time() - _tls._started_at) * 1_000.0 if _tls._started_at else 0.0

    @contextmanager
    def reasoning_session(
        self,
        reasoning_type: ReasoningType,
        actor:          str           = SYSTEM_REASONING_ACTOR,
        session_id:     Optional[str] = None,
    ) -> Generator[None, None, None]:
        prev_sid  = _tls._session_id
        prev_type = _tls._reasoning_type
        prev_act  = _tls._actor
        prev_ts   = _tls._started_at
        prev_diag = _tls._diagnostics
        prev_dep  = _tls._depth

        _tls._session_id     = session_id or str(uuid.uuid4())
        _tls._reasoning_type = reasoning_type
        _tls._actor          = actor
        _tls._started_at     = time.time()
        _tls._diagnostics    = []
        _tls._depth          = 0
        try:
            yield
        finally:
            _tls._session_id     = prev_sid
            _tls._reasoning_type = prev_type
            _tls._actor          = prev_act
            _tls._started_at     = prev_ts
            _tls._diagnostics    = prev_diag
            _tls._depth          = prev_dep

    @contextmanager
    def inference_step(self) -> Generator[None, None, None]:
        _tls._depth += 1
        try:
            yield
        finally:
            _tls._depth -= 1

    @contextmanager
    def phase_context(self, phase: ReasoningPhase) -> Generator[None, None, None]:
        prev_phase = _tls._phase
        _tls._phase = phase
        try:
            yield
        finally:
            _tls._phase = prev_phase

    def add_diagnostic(self, level: str, message: str, source: str = "") -> None:
        _tls._diagnostics.append(ReasoningDiagnostic(level, message, source))

    def warnings(self) -> list[ReasoningDiagnostic]:
        return [d for d in _tls._diagnostics if d.level == "WARNING"]

    def errors(self) -> list[ReasoningDiagnostic]:
        return [d for d in _tls._diagnostics if d.level == "ERROR"]


_ctx_lock = threading.Lock()
_ctx_inst: Optional[ReasoningContext] = None


def get_reasoning_context() -> ReasoningContext:
    global _ctx_inst
    if _ctx_inst is None:
        with _ctx_lock:
            if _ctx_inst is None:
                _ctx_inst = ReasoningContext()
    return _ctx_inst


def reset_reasoning_context() -> None:
    global _ctx_inst
    with _ctx_lock:
        _ctx_inst = None
    _tls._session_id     = None
    _tls._actor          = SYSTEM_REASONING_ACTOR
    _tls._reasoning_type = None
    _tls._phase          = None
    _tls._depth          = 0
    _tls._started_at     = 0.0
    _tls._diagnostics    = []


@contextmanager
def reasoning_session(
    reasoning_type: ReasoningType,
    actor:          str           = SYSTEM_REASONING_ACTOR,
    session_id:     Optional[str] = None,
) -> Generator[None, None, None]:
    """Module-level convenience wrapper for get_reasoning_context().reasoning_session(...)."""
    ctx = get_reasoning_context()
    with ctx.reasoning_session(reasoning_type, actor=actor, session_id=session_id):
        yield
