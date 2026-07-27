"""
pipeline_context.py -- iios.ai.foundation.pipeline
====================================================
:class:`PipelineContext` -- mutable context that flows through all
pipeline stages.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..request.request_models import (
    AIExecutionRequest,
    AIResponse,
)


@dataclass
class StageRecord:
    """Timing and outcome record for one pipeline stage."""
    stage_name:  str
    started_at:  float
    ended_at:    float
    succeeded:   bool
    error:       str = ""

    @property
    def duration_ms(self) -> float:
        return (self.ended_at - self.started_at) * 1000.0


class PipelineContext:
    """
    Mutable execution context threaded through every pipeline stage.

    Stages read inputs from and write outputs to this object.
    It is never exposed outside the pipeline.

    Parameters
    ----------
    execution_request : The initial :class:`AIExecutionRequest`.
    pipeline_id :       Unique pipeline run identifier.
    """

    def __init__(
        self,
        execution_request: AIExecutionRequest,
        pipeline_id:       str = "",
    ) -> None:
        self.pipeline_id:      str               = pipeline_id or str(uuid.uuid4())
        self.execution_request: AIExecutionRequest = execution_request
        self.started_at:       float             = time.time()
        self.response:         Optional[AIResponse] = None
        self.provider_id:      str               = ""
        self.model_id:         str               = ""
        self.policy_decisions: List[str]         = []
        self.stage_records:    List[StageRecord] = []
        self.data:             Dict[str, Any]    = {}   # cross-stage scratch space
        self._aborted:         bool              = False
        self._abort_reason:    str               = ""

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def request_id(self) -> str:
        return self.execution_request.request_id

    @property
    def session_id(self) -> str:
        return self.execution_request.session_id

    @property
    def is_aborted(self) -> bool:
        return self._aborted

    @property
    def abort_reason(self) -> str:
        return self._abort_reason

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000.0

    # ── Stage recording ───────────────────────────────────────────────────────

    def record_stage(
        self,
        stage_name: str,
        started_at: float,
        succeeded:  bool,
        error:      str = "",
    ) -> None:
        self.stage_records.append(StageRecord(
            stage_name = stage_name,
            started_at = started_at,
            ended_at   = time.time(),
            succeeded  = succeeded,
            error      = error,
        ))

    def abort(self, reason: str) -> None:
        """Signal pipeline abort -- subsequent stages will be skipped."""
        self._aborted     = True
        self._abort_reason = reason

    # ── Data exchange ─────────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id":      self.pipeline_id,
            "request_id":       self.request_id,
            "session_id":       self.session_id,
            "elapsed_ms":       round(self.elapsed_ms, 2),
            "stages_completed": len(self.stage_records),
            "is_aborted":       self._aborted,
            "abort_reason":     self._abort_reason,
            "provider_id":      self.provider_id,
        }
