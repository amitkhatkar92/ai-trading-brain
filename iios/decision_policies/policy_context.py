"""
iios/decision_policies/policy_context.py
=========================================
EvaluationContext (data container passed to rules/constraints/compliance)
and thread-local PolicyContextState for session tracking.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .policy_constants import EvaluationMode


# ── Core data containers ──────────────────────────────────────────────────────

@dataclass
class EvaluationContext:
    """
    Immutable-style data bag passed to every rule, constraint, and
    compliance check during a single evaluation pass.
    """
    context_id:      str           = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:       str           = ""
    decision_type:   str           = "generic"
    payload:         dict          = field(default_factory=dict)
    constraints_data: dict         = field(default_factory=dict)
    metadata:        dict          = field(default_factory=dict)
    evaluation_mode: EvaluationMode = EvaluationMode.LENIENT
    created_at:      float         = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def to_dict(self) -> dict:
        return {
            "context_id":      self.context_id,
            "source_id":       self.source_id,
            "decision_type":   self.decision_type,
            "payload_keys":    list(self.payload.keys()),
            "evaluation_mode": self.evaluation_mode.value,
            "created_at":      self.created_at,
        }


@dataclass
class PolicyDiagnostic:
    level:   str
    message: str
    stage:   str = ""
    source:  str = ""
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "level":   self.level,
            "message": self.message,
            "stage":   self.stage,
            "source":  self.source,
            "ts":      self.ts,
        }


@dataclass
class PolicyContextState:
    """Thread-local state tracking an in-progress policy evaluation session."""
    evaluation_id: str           = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:     str           = ""
    mode:          EvaluationMode = EvaluationMode.LENIENT
    current_stage: str           = ""
    depth:         int           = 0
    started_at:    float         = field(default_factory=time.time)
    _diagnostics:  list[PolicyDiagnostic] = field(default_factory=list, repr=False)

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        stage:   str = "",
        source:  str = "",
    ) -> None:
        self._diagnostics.append(
            PolicyDiagnostic(level=level, message=message, stage=stage, source=source)
        )

    def warnings(self) -> list[PolicyDiagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "WARNING"]

    def errors(self) -> list[PolicyDiagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    def to_dict(self) -> dict:
        return {
            "evaluation_id": self.evaluation_id,
            "source_id":     self.source_id,
            "mode":          self.mode.value,
            "current_stage": self.current_stage,
            "depth":         self.depth,
            "elapsed_ms":    self.elapsed_ms(),
            "diagnostics":   [d.to_dict() for d in self._diagnostics],
        }


# ── Thread-local singleton ────────────────────────────────────────────────────

_tls = threading.local()


def get_policy_context() -> PolicyContextState:
    """Return the current thread's PolicyContextState (create default if absent)."""
    if not hasattr(_tls, "state") or _tls.state is None:
        _tls.state = PolicyContextState()
    return _tls.state


def reset_policy_context() -> None:
    """Clear the current thread's PolicyContextState."""
    _tls.state = None


# ── Context managers ──────────────────────────────────────────────────────────

@contextmanager
def evaluation_scope(
    source_id: str = "",
    mode: EvaluationMode = EvaluationMode.LENIENT,
) -> Generator[PolicyContextState, None, None]:
    """Open a new evaluation session scope on the current thread."""
    state = PolicyContextState(source_id=source_id, mode=mode)
    _tls.state = state
    state.depth += 1
    try:
        yield state
    finally:
        state.depth -= 1
        if state.depth == 0:
            _tls.state = None


@contextmanager
def policy_stage_scope(
    stage: str,
) -> Generator[PolicyContextState, None, None]:
    """Track the current evaluation stage within an active evaluation_scope."""
    state = get_policy_context()
    prev  = state.current_stage
    state.current_stage = stage
    try:
        yield state
    finally:
        state.current_stage = prev
