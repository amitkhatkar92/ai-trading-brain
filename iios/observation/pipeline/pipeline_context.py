"""
iios/observation/pipeline/pipeline_context.py
=============================================
Per-run execution context threaded through all pipeline stages.

The context carries:
  - Identity (obs_id, pipeline_name, run_id)
  - Per-stage results and timing
  - Checkpoints for resume
  - Shared attributes so stages can pass data forward
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .pipeline_constants import CheckpointPolicy, PipelineState, PIPELINE_NAMESPACE

__all__ = [
    "Checkpoint",
    "StageResult",
    "PipelineContext",
    "get_pipeline_context",
    "reset_pipeline_context",
    "pipeline_execution",
]

_thread_local = threading.local()


@dataclass
class Checkpoint:
    """Snapshot of pipeline state at a particular stage."""
    stage_name:  str
    obs_snapshot: dict[str, Any]   # obs.to_dict() at this point
    attributes:  dict[str, Any]
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name":  self.stage_name,
            "recorded_at": self.recorded_at,
            "attributes":  list(self.attributes.keys()),
        }


@dataclass
class StageResult:
    """Outcome of a single pipeline stage execution."""
    stage_name:  str
    success:     bool
    duration_ms: float        = 0.0
    skipped:     bool         = False
    retries:     int          = 0
    error:       Optional[str] = None
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name":  self.stage_name,
            "success":     self.success,
            "skipped":     self.skipped,
            "retries":     self.retries,
            "duration_ms": round(self.duration_ms, 3),
            "error":       self.error,
        }


class PipelineContext:
    """Full execution context for one pipeline run."""

    def __init__(
        self,
        obs_id:            str,
        pipeline_name:     str,
        run_id:            str                 = "",
        checkpoint_policy: CheckpointPolicy    = CheckpointPolicy.ON_FAILURE,
    ) -> None:
        self.obs_id             = obs_id
        self.pipeline_name      = pipeline_name
        self.run_id             = run_id or uuid.uuid4().hex
        self.checkpoint_policy  = checkpoint_policy
        self.state              = PipelineState.IDLE
        self.started_at:  float = time.time()
        self.finished_at: Optional[float] = None

        self._stage_results:  list[StageResult]       = []
        self._checkpoints:    list[Checkpoint]         = []
        self._attributes:     dict[str, Any]           = {}
        self._lock                                     = threading.RLock()

    # ── Attribute store (shared between stages) ───────────────────────────────

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._attributes[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._attributes.get(key, default)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._attributes

    def snapshot_attributes(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._attributes)

    # ── Stage result tracking ─────────────────────────────────────────────────

    def record_stage(self, result: StageResult) -> None:
        with self._lock:
            self._stage_results.append(result)

    def stage_results(self) -> list[StageResult]:
        with self._lock:
            return list(self._stage_results)

    def last_stage(self) -> Optional[StageResult]:
        with self._lock:
            return self._stage_results[-1] if self._stage_results else None

    def stage_by_name(self, name: str) -> Optional[StageResult]:
        with self._lock:
            for r in reversed(self._stage_results):
                if r.stage_name == name:
                    return r
        return None

    def all_stages_successful(self) -> bool:
        with self._lock:
            return all(r.success or r.skipped for r in self._stage_results)

    def failed_stages(self) -> list[StageResult]:
        with self._lock:
            return [r for r in self._stage_results if not r.success and not r.skipped]

    # ── Checkpoints ───────────────────────────────────────────────────────────

    def checkpoint(self, stage_name: str, obs_snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._checkpoints.append(Checkpoint(
                stage_name   = stage_name,
                obs_snapshot = obs_snapshot,
                attributes   = dict(self._attributes),
            ))

    def last_checkpoint(self) -> Optional[Checkpoint]:
        with self._lock:
            return self._checkpoints[-1] if self._checkpoints else None

    def checkpoints(self) -> list[Checkpoint]:
        with self._lock:
            return list(self._checkpoints)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def elapsed_ms(self) -> float:
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1_000.0

    def complete(self) -> None:
        self.state       = PipelineState.COMPLETED
        self.finished_at = time.time()

    def fail(self) -> None:
        self.state       = PipelineState.FAILED
        self.finished_at = time.time()

    def abort(self) -> None:
        self.state       = PipelineState.ABORTED
        self.finished_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":        self.obs_id,
            "pipeline_name": self.pipeline_name,
            "run_id":        self.run_id,
            "state":         self.state.value,
            "elapsed_ms":    round(self.elapsed_ms, 3),
            "stages_run":    len(self._stage_results),
            "checkpoints":   len(self._checkpoints),
        }


# ── Thread-local context ─────────────────────────────────────────────────────

def get_pipeline_context() -> Optional[PipelineContext]:
    """Return the current thread's pipeline context (or None)."""
    return getattr(_thread_local, "ctx", None)


def reset_pipeline_context() -> None:
    """Clear thread-local pipeline context."""
    _thread_local.ctx = None


@contextmanager
def pipeline_execution(
    obs_id:            str,
    pipeline_name:     str,
    run_id:            str              = "",
    checkpoint_policy: CheckpointPolicy = CheckpointPolicy.ON_FAILURE,
) -> Generator[PipelineContext, None, None]:
    """Context manager that creates and installs a ``PipelineContext``."""
    ctx = PipelineContext(
        obs_id            = obs_id,
        pipeline_name     = pipeline_name,
        run_id            = run_id or uuid.uuid4().hex,
        checkpoint_policy = checkpoint_policy,
    )
    ctx.state = PipelineState.RUNNING
    prev = getattr(_thread_local, "ctx", None)
    _thread_local.ctx = ctx
    try:
        yield ctx
        # Only mark completed if the executor did not already abort/fail it
        if ctx.state == PipelineState.RUNNING:
            ctx.complete()
    except Exception:
        ctx.fail()
        raise
    finally:
        _thread_local.ctx = prev
