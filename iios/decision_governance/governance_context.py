"""iios/decision_governance/governance_context.py

Thread-local governance session context + GovernanceSubject dataclass.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from iios.decision_governance.governance_constants import GovernanceMode


# ─────────────────────────────────────────────────────────────────────────────
# GovernanceSubject — the artifact being governed
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GovernanceSubject:
    """Generic subject submitted for governance. Carries the decision payload."""

    subject_id:  str  = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str  = ""
    payload:     dict = field(default_factory=dict)
    score:       float = 0.0
    metadata:    dict = field(default_factory=dict)
    submitted_at: float = field(default_factory=time.time)

    # ── convenience ──────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def to_dict(self) -> dict:
        return {
            "subject_id":   self.subject_id,
            "decision_id":  self.decision_id,
            "score":        self.score,
            "payload":      self.payload,
            "metadata":     self.metadata,
            "submitted_at": self.submitted_at,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Governance session context (thread-local)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Diagnostic:
    level:   str
    message: str
    stage:   str
    source:  str
    ts:      float = field(default_factory=time.time)


@dataclass
class GovernanceContextState:
    """Thread-local state for one governance pipeline execution."""

    session_id:     str           = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:      str           = ""
    mode:           GovernanceMode = GovernanceMode.LENIENT
    current_stage:  str           = ""
    depth:          int           = 0
    started_at:     float         = field(default_factory=time.time)
    _diagnostics:   list[_Diagnostic] = field(default_factory=list, repr=False)

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        stage:   str = "",
        source:  str = "",
    ) -> None:
        self._diagnostics.append(
            _Diagnostic(level, message, stage or self.current_stage, source)
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
            "mode":          self.mode.value,
            "current_stage": self.current_stage,
            "depth":         self.depth,
            "elapsed_ms":    self.elapsed_ms(),
            "warnings":      len(self.warnings()),
            "errors":        len(self.errors()),
        }


# ── thread-local storage ──────────────────────────────────────────────────────

_tls: threading.local = threading.local()


def get_governance_context() -> GovernanceContextState:
    """Return the current thread's context, creating one if absent."""
    if not hasattr(_tls, "ctx"):
        _tls.ctx = GovernanceContextState()
    return _tls.ctx  # type: ignore[return-value]


def reset_governance_context() -> None:
    """Clear the current thread's context."""
    if hasattr(_tls, "ctx"):
        del _tls.ctx


# ── context managers ─────────────────────────────────────────────────────────

@contextmanager
def governance_session(
    source_id: str = "",
    mode: GovernanceMode = GovernanceMode.LENIENT,
) -> Generator[GovernanceContextState, None, None]:
    """Enter a governance session scope on the current thread."""
    ctx = GovernanceContextState(source_id=source_id, mode=mode)
    _tls.ctx = ctx
    try:
        yield ctx
    finally:
        if getattr(_tls, "ctx", None) is ctx:
            del _tls.ctx


@contextmanager
def gov_stage_scope(stage: str) -> Generator[GovernanceContextState, None, None]:
    """Enter a named pipeline stage within the current governance session."""
    ctx = get_governance_context()
    prev_stage = ctx.current_stage
    ctx.current_stage = stage
    ctx.depth += 1
    try:
        yield ctx
    finally:
        ctx.current_stage = prev_stage
        ctx.depth -= 1
