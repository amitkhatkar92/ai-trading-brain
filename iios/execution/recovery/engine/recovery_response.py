"""
iios/execution/recovery/engine/recovery_response.py
===================================================
RecoveryResponse — the primary output from the Execution Recovery Engine.

Returned from ExecutionRecoveryEngine.start_recovery() after the workflow
completes (successfully or not).

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    RecoveryOutcome,
    RecoveryResponseStatus,
)


@dataclass(frozen=True)
class RecoveryResponse:
    """
    Immutable summary of a completed recovery workflow.

    Contains status, outcome, timing, and references to the session and
    snapshot produced during the workflow.
    """

    response_id:    str
    request_id:     str
    session_id:     str
    status:         RecoveryResponseStatus
    outcome:        RecoveryOutcome
    subsystem_id:   str
    started_at:     Optional[float]
    completed_at:   Optional[float]
    duration_ms:    float
    error_message:  str             = ""
    snapshot_id:    str             = ""
    pipeline_stages_completed: int  = 0
    pipeline_stages_total:     int  = 0
    metadata:       Dict[str, Any]  = field(default_factory=dict)
    framework_version: str          = VERSION

    @property
    def is_success(self) -> bool:
        return self.status == RecoveryResponseStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == RecoveryResponseStatus.FAILED

    @property
    def pipeline_completion_rate(self) -> float:
        if self.pipeline_stages_total == 0:
            return 0.0
        return self.pipeline_stages_completed / self.pipeline_stages_total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":                self.response_id,
            "request_id":                 self.request_id,
            "session_id":                 self.session_id,
            "status":                     self.status.value,
            "outcome":                    self.outcome.value,
            "subsystem_id":               self.subsystem_id,
            "started_at":                 self.started_at,
            "completed_at":               self.completed_at,
            "duration_ms":                self.duration_ms,
            "error_message":              self.error_message,
            "snapshot_id":                self.snapshot_id,
            "pipeline_stages_completed":  self.pipeline_stages_completed,
            "pipeline_stages_total":      self.pipeline_stages_total,
            "pipeline_completion_rate":   self.pipeline_completion_rate,
            "framework_version":          self.framework_version,
        }


def make_recovery_response(
    request_id: str,
    session_id: str,
    status: RecoveryResponseStatus,
    outcome: RecoveryOutcome,
    subsystem_id: str,
    *,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
    duration_ms: float = 0.0,
    error_message: str = "",
    snapshot_id: str = "",
    pipeline_stages_completed: int = 0,
    pipeline_stages_total: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
    response_id: Optional[str] = None,
) -> RecoveryResponse:
    """Factory for RecoveryResponse."""
    return RecoveryResponse(
        response_id               = response_id or str(uuid.uuid4()),
        request_id                = request_id,
        session_id                = session_id,
        status                    = status,
        outcome                   = outcome,
        subsystem_id              = subsystem_id,
        started_at                = started_at,
        completed_at              = completed_at or time.time(),
        duration_ms               = duration_ms,
        error_message             = error_message,
        snapshot_id               = snapshot_id,
        pipeline_stages_completed = pipeline_stages_completed,
        pipeline_stages_total     = pipeline_stages_total,
        metadata                  = dict(metadata) if metadata else {},
    )


def make_success_response(
    request_id: str,
    session_id: str,
    subsystem_id: str,
    *,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
    snapshot_id: str = "",
    pipeline_stages_completed: int = 0,
    pipeline_stages_total: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> RecoveryResponse:
    """Convenience factory for a successful recovery response."""
    end = completed_at or time.time()
    duration = (end - started_at) * 1000.0 if started_at is not None else 0.0
    return make_recovery_response(
        request_id                = request_id,
        session_id                = session_id,
        status                    = RecoveryResponseStatus.SUCCESS,
        outcome                   = RecoveryOutcome.RECOVERED,
        subsystem_id              = subsystem_id,
        started_at                = started_at,
        completed_at              = end,
        duration_ms               = duration,
        snapshot_id               = snapshot_id,
        pipeline_stages_completed = pipeline_stages_completed,
        pipeline_stages_total     = pipeline_stages_total,
        metadata                  = metadata,
    )


def make_failure_response(
    request_id: str,
    session_id: str,
    subsystem_id: str,
    error_message: str,
    *,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
    pipeline_stages_completed: int = 0,
    pipeline_stages_total: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> RecoveryResponse:
    """Convenience factory for a failed recovery response."""
    end = completed_at or time.time()
    duration = (end - started_at) * 1000.0 if started_at is not None else 0.0
    return make_recovery_response(
        request_id                = request_id,
        session_id                = session_id,
        status                    = RecoveryResponseStatus.FAILED,
        outcome                   = RecoveryOutcome.UNRECOVERABLE,
        subsystem_id              = subsystem_id,
        started_at                = started_at,
        completed_at              = end,
        duration_ms               = duration,
        error_message             = error_message,
        pipeline_stages_completed = pipeline_stages_completed,
        pipeline_stages_total     = pipeline_stages_total,
        metadata                  = metadata,
    )
