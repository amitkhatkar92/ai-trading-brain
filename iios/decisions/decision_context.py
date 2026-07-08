"""
iios/decisions/decision_context.py
====================================
Thread-local execution context for an active Decision Engine workflow.
Context-manager helpers use the ``_scope`` suffix to avoid shadowing
the ``workflow`` and ``evaluation`` subpackage names.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .decision_constants import DecisionPriority, DecisionType, WorkflowStage


# ── Context state ─────────────────────────────────────────────────────────────

@dataclass
class DecisionDiagnostic:
    """A single diagnostic message captured during a decision workflow."""
    level:   str            # "INFO" | "WARNING" | "ERROR"
    message: str
    stage:   str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":   self.level,
            "message": self.message,
            "stage":   self.stage,
            "source":  self.source,
            "ts":      self.ts,
        }


class DecisionContextState:
    """Mutable per-thread state for an active decision workflow."""

    def __init__(self) -> None:
        self.request_id:    str | None              = None
        self.decision_type: DecisionType | None     = None
        self.source_id:     str | None              = None
        self.priority:      DecisionPriority | None = None
        self.current_stage: WorkflowStage | None    = None
        self.depth:         int                     = 0
        self.started_at:    float                   = time.time()
        self._diagnostics:  list[DecisionDiagnostic] = []

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        stage:   str  = "",
        source:  str  = "",
    ) -> None:
        self._diagnostics.append(
            DecisionDiagnostic(level=level, message=message, stage=stage, source=source)
        )

    def warnings(self) -> list[DecisionDiagnostic]:
        return [d for d in self._diagnostics if d.level == "WARNING"]

    def errors(self) -> list[DecisionDiagnostic]:
        return [d for d in self._diagnostics if d.level == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "decision_type": self.decision_type.value if self.decision_type else None,
            "source_id":     self.source_id,
            "priority":      self.priority.value if self.priority else None,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "depth":         self.depth,
            "elapsed_ms":    round(self.elapsed_ms(), 2),
            "diagnostics":   [d.to_dict() for d in self._diagnostics],
        }


# ── Thread-local storage ──────────────────────────────────────────────────────

_CTX_LOCAL: threading.local = threading.local()


class _DecisionContextManager:
    """Thread-local context manager for decision workflow scopes."""

    def get(self) -> DecisionContextState:
        if not hasattr(_CTX_LOCAL, "state"):
            _CTX_LOCAL.state = DecisionContextState()
        return _CTX_LOCAL.state

    def _push(
        self,
        request_id:    str | None = None,
        decision_type: DecisionType | None = None,
        source_id:     str | None = None,
        priority:      DecisionPriority | None = None,
    ) -> DecisionContextState:
        state = self.get()
        state.depth       += 1
        state.started_at   = time.time()
        if request_id:
            state.request_id = request_id
        if decision_type:
            state.decision_type = decision_type
        if source_id:
            state.source_id = source_id
        if priority:
            state.priority = priority
        return state

    def _pop(self) -> None:
        state = self.get()
        state.depth = max(0, state.depth - 1)
        if state.depth == 0:
            _CTX_LOCAL.state = DecisionContextState()

    @contextmanager
    def workflow_scope(
        self,
        request_id:    str,
        decision_type: DecisionType | None = None,
        source_id:     str | None = None,
        priority:      DecisionPriority | None = None,
    ) -> Generator[DecisionContextState, None, None]:
        state = self._push(request_id, decision_type, source_id, priority)
        try:
            yield state
        finally:
            self._pop()

    @contextmanager
    def stage_scope(
        self,
        stage: WorkflowStage,
    ) -> Generator[DecisionContextState, None, None]:
        state = self.get()
        prev  = state.current_stage
        state.current_stage = stage
        try:
            yield state
        finally:
            state.current_stage = prev


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock                 = threading.Lock()
_INSTANCE: _DecisionContextManager | None = None


def _get_manager() -> _DecisionContextManager:
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _DecisionContextManager()
    return _INSTANCE


def get_decision_context() -> DecisionContextState:
    return _get_manager().get()


def reset_decision_context() -> None:
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
    if hasattr(_CTX_LOCAL, "state"):
        del _CTX_LOCAL.state


# ── Module-level helpers ──────────────────────────────────────────────────────

@contextmanager
def workflow_scope(
    request_id:    str,
    decision_type: DecisionType | None  = None,
    source_id:     str | None           = None,
    priority:      DecisionPriority | None = None,
) -> Generator[DecisionContextState, None, None]:
    with _get_manager().workflow_scope(request_id, decision_type, source_id, priority) as ctx:
        yield ctx


@contextmanager
def stage_scope(
    stage: WorkflowStage,
) -> Generator[DecisionContextState, None, None]:
    with _get_manager().stage_scope(stage) as ctx:
        yield ctx
