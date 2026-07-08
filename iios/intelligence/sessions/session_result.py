"""
iios/intelligence/sessions/session_result.py
=============================================
Session result model capturing everything produced during an intelligence session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..intelligence_constants import SessionStatus, ExecutionStatus

__all__ = ["SessionResult"]


@dataclass
class SessionResult:
    """
    Complete output of one intelligence session.

    Attributes
    ----------
    session_id:     Unique session identifier
    status:         Final session status
    outputs:        Key → value map of results from all steps
    errors:         List of error dicts {step_id, message, ts}
    warnings:       List of warning strings
    duration_ms:    Total session duration
    step_count:     Number of steps executed
    workflow_ids:   Workflows executed in this session
    checkpoints:    Checkpoint IDs saved during execution
    metadata:       Arbitrary key/value metadata
    started_at:     Unix epoch start time
    finished_at:    Unix epoch finish time (None if not complete)
    """
    session_id:   str
    status:       SessionStatus                = SessionStatus.PENDING
    outputs:      dict[str, Any]               = field(default_factory=dict)
    errors:       list[dict[str, Any]]         = field(default_factory=list)
    warnings:     list[str]                    = field(default_factory=list)
    duration_ms:  float                        = 0.0
    step_count:   int                          = 0
    workflow_ids: list[str]                    = field(default_factory=list)
    checkpoints:  list[str]                    = field(default_factory=list)
    metadata:     dict[str, Any]               = field(default_factory=dict)
    started_at:   float                        = field(default_factory=time.time)
    finished_at:  Optional[float]              = None

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def succeeded(self) -> bool:
        return self.status == SessionStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == SessionStatus.FAILED

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def add_output(self, key: str, value: Any) -> None:
        self.outputs[key] = value

    def add_error(self, step_id: str, message: str) -> None:
        self.errors.append({"step_id": step_id, "message": message, "ts": time.time()})

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def complete(self) -> None:
        self.status      = SessionStatus.COMPLETED
        self.finished_at = time.time()
        if self.finished_at and self.started_at:
            self.duration_ms = (self.finished_at - self.started_at) * 1_000.0

    def fail(self, reason: str = "") -> None:
        self.status      = SessionStatus.FAILED
        self.finished_at = time.time()
        if reason:
            self.add_error("session", reason)
        if self.finished_at and self.started_at:
            self.duration_ms = (self.finished_at - self.started_at) * 1_000.0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "session_id":  self.session_id,
            "status":      self.status.value,
            "outputs":     {k: str(v) for k, v in self.outputs.items()},
            "errors":      self.errors,
            "warnings":    self.warnings,
            "duration_ms": round(self.duration_ms, 3),
            "step_count":  self.step_count,
            "workflow_ids": self.workflow_ids,
            "checkpoints": self.checkpoints,
            "metadata":    self.metadata,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
        }
