"""
iios/execution/recovery/engine/recovery_snapshot.py
===================================================
RecoverySnapshot — point-in-time capture of the recovery workflow state.

Published after verification to provide an auditable record of the recovery.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    PipelineStage,
    RecoveryEngineState,
    RecoveryOutcome,
    RecoveryResponseStatus,
)


@dataclass(frozen=True)
class RecoverySnapshot:
    """
    Immutable point-in-time capture of the recovery workflow state.

    Published at the PUBLISH_SNAPSHOT pipeline stage and stored in history.
    """

    snapshot_id:        str
    session_id:         str
    request_id:         str
    subsystem_id:       str
    engine_state:       RecoveryEngineState
    current_stage:      Optional[PipelineStage]
    stages_completed:   int
    stages_total:       int
    failure_type:       str
    failure_severity:   str
    failure_reason:     str
    recovery_outcome:   RecoveryOutcome
    is_complete:        bool
    captured_at:        float
    started_at:         Optional[float]
    completed_at:       Optional[float]
    duration_ms:        float
    has_policy_result:  bool                 = False
    has_failover_result: bool                = False
    error_message:      str                  = ""
    metadata:           Dict[str, Any]       = field(default_factory=dict)
    framework_version:  str                  = VERSION

    @property
    def pipeline_progress(self) -> float:
        """Fraction of pipeline stages completed (0.0 – 1.0)."""
        if self.stages_total == 0:
            return 0.0
        return min(1.0, self.stages_completed / self.stages_total)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "session_id":          self.session_id,
            "request_id":          self.request_id,
            "subsystem_id":        self.subsystem_id,
            "engine_state":        self.engine_state.value,
            "current_stage":       self.current_stage.value if self.current_stage else None,
            "stages_completed":    self.stages_completed,
            "stages_total":        self.stages_total,
            "pipeline_progress":   self.pipeline_progress,
            "failure_type":        self.failure_type,
            "failure_severity":    self.failure_severity,
            "failure_reason":      self.failure_reason,
            "recovery_outcome":    self.recovery_outcome.value,
            "is_complete":         self.is_complete,
            "captured_at":         self.captured_at,
            "started_at":          self.started_at,
            "completed_at":        self.completed_at,
            "duration_ms":         self.duration_ms,
            "has_policy_result":   self.has_policy_result,
            "has_failover_result": self.has_failover_result,
            "error_message":       self.error_message,
            "framework_version":   self.framework_version,
        }


def make_recovery_snapshot(
    session_id: str,
    request_id: str,
    subsystem_id: str,
    engine_state: RecoveryEngineState,
    current_stage: Optional[PipelineStage],
    stages_completed: int,
    stages_total: int,
    failure_type: str,
    failure_severity: str,
    failure_reason: str,
    recovery_outcome: RecoveryOutcome,
    *,
    is_complete: bool = False,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
    duration_ms: float = 0.0,
    has_policy_result: bool = False,
    has_failover_result: bool = False,
    error_message: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    snapshot_id: Optional[str] = None,
) -> RecoverySnapshot:
    """Factory for RecoverySnapshot."""
    return RecoverySnapshot(
        snapshot_id         = snapshot_id or str(uuid.uuid4()),
        session_id          = session_id,
        request_id          = request_id,
        subsystem_id        = subsystem_id,
        engine_state        = engine_state,
        current_stage       = current_stage,
        stages_completed    = stages_completed,
        stages_total        = stages_total,
        failure_type        = failure_type,
        failure_severity    = failure_severity,
        failure_reason      = failure_reason,
        recovery_outcome    = recovery_outcome,
        is_complete         = is_complete,
        captured_at         = time.time(),
        started_at          = started_at,
        completed_at        = completed_at,
        duration_ms         = duration_ms,
        has_policy_result   = has_policy_result,
        has_failover_result = has_failover_result,
        error_message       = error_message,
        metadata            = dict(metadata) if metadata else {},
    )
