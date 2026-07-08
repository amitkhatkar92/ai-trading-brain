"""
iios/intelligence/intelligence_context.py
==========================================
Thread-local execution context for the Intelligence Orchestration Engine.

Tracks the current session, workflow, step, actor, and nesting depth
for every thread participating in intelligence execution.

Singleton: get_intelligence_context() / reset_intelligence_context()
Module-level CM: intelligence_session() / workflow_step()
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from .intelligence_constants import (
    Priority,
    SessionStatus,
    ExecutionStatus,
    SYSTEM_ACTOR,
)

__all__ = [
    "IntelligenceDiagnostic",
    "IntelligenceContext",
    "get_intelligence_context",
    "reset_intelligence_context",
    "intelligence_execution",
    "workflow_scope",
    "step_scope",
]


@dataclass
class IntelligenceDiagnostic:
    level:   str
    message: str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "level":   self.level,
            "message": self.message,
            "source":  self.source,
            "ts":      self.ts,
        }


class _TLS(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.session_id:   Optional[str]   = None
        self.workflow_id:  Optional[str]   = None
        self.step_id:      Optional[str]   = None
        self.actor:        str             = SYSTEM_ACTOR
        self.priority:     Priority        = Priority.NORMAL
        self.depth:        int             = 0
        self.started_at:   float           = 0.0
        self.diagnostics:  list[IntelligenceDiagnostic] = []
        self.metadata:     dict            = {}


_tls = _TLS()


class IntelligenceContext:
    """
    Thread-local context for in-flight intelligence operations.

    Allows any code called during execution to inspect the current
    session, workflow, step, and actor without passing them as parameters.
    """

    # ── Read-only properties ──────────────────────────────────────────────────

    @property
    def session_id(self) -> Optional[str]:
        return _tls.session_id

    @property
    def workflow_id(self) -> Optional[str]:
        return _tls.workflow_id

    @property
    def step_id(self) -> Optional[str]:
        return _tls.step_id

    @property
    def actor(self) -> str:
        return _tls.actor

    @property
    def priority(self) -> Priority:
        return _tls.priority

    @property
    def depth(self) -> int:
        return _tls.depth

    @property
    def started_at(self) -> float:
        return _tls.started_at

    def elapsed_ms(self) -> float:
        return (time.time() - _tls.started_at) * 1_000.0 if _tls.started_at else 0.0

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        source:  str = "",
    ) -> None:
        _tls.diagnostics.append(IntelligenceDiagnostic(level, message, source))

    def warnings(self) -> list[IntelligenceDiagnostic]:
        return [d for d in _tls.diagnostics if d.level == "WARNING"]

    def errors(self) -> list[IntelligenceDiagnostic]:
        return [d for d in _tls.diagnostics if d.level == "ERROR"]

    def all_diagnostics(self) -> list[IntelligenceDiagnostic]:
        return list(_tls.diagnostics)

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def execution(
        self,
        session_id:  Optional[str]  = None,
        actor:       str            = SYSTEM_ACTOR,
        priority:    Priority       = Priority.NORMAL,
    ) -> Generator[None, None, None]:
        """Top-level execution context — binds session ID and actor."""
        prev_sid   = _tls.session_id
        prev_actor = _tls.actor
        prev_pri   = _tls.priority
        prev_ts    = _tls.started_at
        prev_diag  = _tls.diagnostics

        _tls.session_id  = session_id or str(uuid.uuid4())
        _tls.actor       = actor
        _tls.priority    = priority
        _tls.started_at  = time.time()
        _tls.diagnostics = []
        try:
            yield
        finally:
            _tls.session_id  = prev_sid
            _tls.actor       = prev_actor
            _tls.priority    = prev_pri
            _tls.started_at  = prev_ts
            _tls.diagnostics = prev_diag

    @contextmanager
    def workflow(
        self,
        workflow_id: str,
    ) -> Generator[None, None, None]:
        """Scopes execution to a specific workflow."""
        prev_wf = _tls.workflow_id
        _tls.workflow_id = workflow_id
        try:
            yield
        finally:
            _tls.workflow_id = prev_wf

    @contextmanager
    def step(
        self,
        step_id: str,
    ) -> Generator[None, None, None]:
        """Scopes execution to a specific workflow step; tracks nesting depth."""
        prev_step = _tls.step_id
        _tls.step_id = step_id
        _tls.depth  += 1
        try:
            yield
        finally:
            _tls.step_id = prev_step
            _tls.depth  -= 1


_ctx_lock = threading.Lock()
_ctx_inst: Optional[IntelligenceContext] = None


def get_intelligence_context() -> IntelligenceContext:
    global _ctx_inst
    if _ctx_inst is None:
        with _ctx_lock:
            if _ctx_inst is None:
                _ctx_inst = IntelligenceContext()
    return _ctx_inst


def reset_intelligence_context() -> None:
    global _ctx_inst
    with _ctx_lock:
        _ctx_inst = None
    _tls.session_id  = None
    _tls.workflow_id = None
    _tls.step_id     = None
    _tls.actor       = SYSTEM_ACTOR
    _tls.priority    = Priority.NORMAL
    _tls.depth       = 0
    _tls.started_at  = 0.0
    _tls.diagnostics = []
    _tls.metadata    = {}


# ── Module-level convenience context managers ─────────────────────────────────

@contextmanager
def intelligence_execution(
    session_id: Optional[str] = None,
    actor:      str           = SYSTEM_ACTOR,
    priority:   Priority      = Priority.NORMAL,
) -> Generator[None, None, None]:
    ctx = get_intelligence_context()
    with ctx.execution(session_id=session_id, actor=actor, priority=priority):
        yield


@contextmanager
def workflow_scope(workflow_id: str) -> Generator[None, None, None]:
    ctx = get_intelligence_context()
    with ctx.workflow(workflow_id):
        yield


@contextmanager
def step_scope(step_id: str) -> Generator[None, None, None]:
    ctx = get_intelligence_context()
    with ctx.step(step_id):
        yield
