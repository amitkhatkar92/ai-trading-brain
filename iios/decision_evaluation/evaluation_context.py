"""iios/decision_evaluation/evaluation_context.py — Alternative model + session context."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .evaluation_constants import EvaluationMode


@dataclass
class Alternative:
    """A decision alternative — the unit being evaluated."""
    alternative_id: str        = field(default_factory=lambda: str(uuid.uuid4()))
    name:           str        = ""
    payload:        dict       = field(default_factory=dict)
    confidence:     float      = 1.0
    metadata:       dict       = field(default_factory=dict)
    created_at:     float      = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def to_dict(self) -> dict:
        return {
            "alternative_id": self.alternative_id,
            "name":           self.name,
            "payload_keys":   list(self.payload.keys()),
            "confidence":     self.confidence,
            "created_at":     self.created_at,
        }


@dataclass
class EvalDiagnostic:
    level:   str
    message: str
    stage:   str = ""
    source:  str = ""
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"level": self.level, "message": self.message, "stage": self.stage}


@dataclass
class EvaluationContextState:
    """Thread-local state for an in-progress evaluation session."""
    session_id:    str  = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:     str  = ""
    mode:          EvaluationMode = EvaluationMode.LENIENT
    current_stage: str  = ""
    depth:         int  = 0
    started_at:    float = field(default_factory=time.time)
    _diagnostics:  list[EvalDiagnostic] = field(default_factory=list, repr=False)

    def add_diagnostic(self, level: str, message: str, stage: str = "", source: str = "") -> None:
        self._diagnostics.append(EvalDiagnostic(level=level, message=message, stage=stage, source=source))

    def warnings(self) -> list[EvalDiagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "WARNING"]

    def errors(self) -> list[EvalDiagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    def to_dict(self) -> dict:
        return {
            "session_id":    self.session_id,
            "source_id":     self.source_id,
            "mode":          self.mode.value,
            "current_stage": self.current_stage,
            "elapsed_ms":    self.elapsed_ms(),
        }


# ── Thread-local singleton ────────────────────────────────────────────────────

_tls = threading.local()


def get_evaluation_context() -> EvaluationContextState:
    if not hasattr(_tls, "state") or _tls.state is None:
        _tls.state = EvaluationContextState()
    return _tls.state


def reset_evaluation_context() -> None:
    _tls.state = None


@contextmanager
def evaluation_session(
    source_id: str = "",
    mode: EvaluationMode = EvaluationMode.LENIENT,
) -> Generator[EvaluationContextState, None, None]:
    state = EvaluationContextState(source_id=source_id, mode=mode)
    _tls.state = state
    state.depth += 1
    try:
        yield state
    finally:
        state.depth -= 1
        if state.depth == 0:
            _tls.state = None


@contextmanager
def eval_stage_scope(stage: str) -> Generator[EvaluationContextState, None, None]:
    state = get_evaluation_context()
    prev  = state.current_stage
    state.current_stage = stage
    try:
        yield state
    finally:
        state.current_stage = prev
