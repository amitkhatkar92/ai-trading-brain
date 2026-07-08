"""iios/decision_optimization/optimization_context.py — Candidate model + session context."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .optimization_constants import OptimizationMode


@dataclass
class Candidate:
    """A decision candidate offered to the optimizer."""
    candidate_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    name:             str   = ""
    payload:          dict  = field(default_factory=dict)
    evaluation_score: float = 0.0          # pre-computed upstream score
    criterion_scores: dict[str, float] = field(default_factory=dict)
    rank:             int   = 0
    metadata:         dict  = field(default_factory=dict)
    created_at:       float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def to_dict(self) -> dict:
        return {
            "candidate_id":     self.candidate_id,
            "name":             self.name,
            "evaluation_score": self.evaluation_score,
            "rank":             self.rank,
            "payload_keys":     list(self.payload.keys()),
        }


@dataclass
class OptDiagnostic:
    level:   str
    message: str
    stage:   str  = ""
    source:  str  = ""
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"level": self.level, "message": self.message, "stage": self.stage}


@dataclass
class OptimizationContextState:
    session_id:    str  = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:     str  = ""
    mode:          OptimizationMode = OptimizationMode.LENIENT
    current_stage: str  = ""
    depth:         int  = 0
    started_at:    float = field(default_factory=time.time)
    _diagnostics:  list[OptDiagnostic] = field(default_factory=list, repr=False)

    def add_diagnostic(
        self, level: str, message: str, stage: str = "", source: str = ""
    ) -> None:
        self._diagnostics.append(
            OptDiagnostic(level=level, message=message, stage=stage, source=source)
        )

    def warnings(self) -> list[OptDiagnostic]:
        return [d for d in self._diagnostics if d.level.upper() == "WARNING"]

    def errors(self) -> list[OptDiagnostic]:
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


def get_optimization_context() -> OptimizationContextState:
    if not hasattr(_tls, "state") or _tls.state is None:
        _tls.state = OptimizationContextState()
    return _tls.state


def reset_optimization_context() -> None:
    _tls.state = None


@contextmanager
def optimization_session(
    source_id: str = "",
    mode: OptimizationMode = OptimizationMode.LENIENT,
) -> Generator[OptimizationContextState, None, None]:
    state = OptimizationContextState(source_id=source_id, mode=mode)
    _tls.state = state
    state.depth += 1
    try:
        yield state
    finally:
        state.depth -= 1
        if state.depth == 0:
            _tls.state = None


@contextmanager
def opt_stage_scope(stage: str) -> Generator[OptimizationContextState, None, None]:
    state = get_optimization_context()
    prev  = state.current_stage
    state.current_stage = stage
    try:
        yield state
    finally:
        state.current_stage = prev
