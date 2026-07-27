"""
execution_context.py -- iios.ai.foundation.runtime
===================================================
ExecutionContext -- mutable per-request execution context threaded
through all runtime pipeline stages.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from ..cost.cost_models      import ExecutionCost, TokenUsage
from ..metrics.metrics_models import ExecutionMetrics
from ..timeout.timeout_models import ExecutionDeadline, TimeoutPolicy


class RuntimeStageRecord:
    """Outcome of one pipeline stage."""
    __slots__ = ("name", "started_at", "ended_at", "succeeded", "notes", "error")

    def __init__(self, name: str) -> None:
        self.name       = name
        self.started_at = time.time()
        self.ended_at:  Optional[float] = None
        self.succeeded: Optional[bool]  = None
        self.notes:     str             = ""
        self.error:     str             = ""

    def complete(self, succeeded: bool, notes: str = "", error: str = "") -> None:
        self.ended_at  = time.time()
        self.succeeded = succeeded
        self.notes     = notes
        self.error     = error

    @property
    def latency_ms(self) -> float:
        if self.ended_at is None:
            return (time.time() - self.started_at) * 1000.0
        return (self.ended_at - self.started_at) * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":       self.name,
            "latency_ms": round(self.latency_ms, 2),
            "succeeded":  self.succeeded,
            "notes":      self.notes,
            "error":      self.error,
        }


class ExecutionContext:
    """
    Mutable per-request execution context.

    Threaded through every stage of :class:`ExecutionRuntime`.
    Accumulates stage records, provider selection, token usage,
    and any per-stage scratch data.

    Not thread-safe -- owned by a single pipeline execution.
    """

    def __init__(
        self,
        request_id:     str,
        session_id:     str,
        trace_id:       str             = "",
        timeout_policy: Optional[TimeoutPolicy] = None,
    ) -> None:
        self.request_id      = request_id
        self.session_id      = session_id
        self.trace_id        = trace_id or str(uuid.uuid4())
        self.execution_id    = str(uuid.uuid4())
        self.timeout_policy  = timeout_policy or TimeoutPolicy()
        self.deadline        = ExecutionDeadline.from_timeout(
            self.timeout_policy.pipeline_timeout_s
        )

        # Filled in by pipeline stages
        self.provider_id:    str                = ""
        self.model_id:       str                = ""
        self.raw_response:   Optional[Any]      = None
        self.token_usage:    Optional[TokenUsage] = None
        self.cost:           Optional[ExecutionCost] = None
        self.error:          Optional[Exception] = None
        self.aborted:        bool                = False
        self.abort_reason:   str                 = ""

        # Stage history
        self._stages:  List[RuntimeStageRecord] = []
        self._scratch: Dict[str, Any]            = {}

        # Timing
        self._started_at = time.time()

    # ---- stage tracking --------------------------------------------------

    def begin_stage(self, name: str) -> RuntimeStageRecord:
        """Create and register a new stage record."""
        rec = RuntimeStageRecord(name)
        self._stages.append(rec)
        return rec

    def current_stage(self) -> Optional[RuntimeStageRecord]:
        return self._stages[-1] if self._stages else None

    def stage_records(self) -> List[RuntimeStageRecord]:
        return list(self._stages)

    # ---- scratch data ----------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        self._scratch[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._scratch.get(key, default)

    # ---- abort -----------------------------------------------------------

    def abort(self, reason: str) -> None:
        self.aborted      = True
        self.abort_reason = reason

    # ---- helpers ---------------------------------------------------------

    def elapsed_ms(self) -> float:
        return (time.time() - self._started_at) * 1000.0

    def is_deadline_exceeded(self) -> bool:
        return self.deadline.is_exceeded()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":  self.execution_id,
            "request_id":    self.request_id,
            "session_id":    self.session_id,
            "trace_id":      self.trace_id,
            "provider_id":   self.provider_id,
            "model_id":      self.model_id,
            "elapsed_ms":    round(self.elapsed_ms(), 2),
            "aborted":       self.aborted,
            "abort_reason":  self.abort_reason,
            "error":         str(self.error) if self.error else None,
            "stages":        [s.to_dict() for s in self._stages],
            "token_usage":   self.token_usage.to_dict() if self.token_usage else None,
        }
