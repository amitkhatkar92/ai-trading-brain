"""
iios/observation/pipeline/pipeline_manager.py
=============================================
Top-level manager: ``process()`` / ``process_batch()`` entry points
with stats, history, and dead-letter queue.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation    import Observation
from ..observation_constants import SYSTEM_OBSERVER
from .pipeline_constants     import PIPELINE_STANDARD, MAX_PIPELINE_HISTORY
from .pipeline_engine        import (
    PipelineEngine, PipelineExecutionResult, get_pipeline_engine,
    reset_pipeline_engine,
)
from .pipeline_monitor       import get_pipeline_monitor, reset_pipeline_monitor
from .pipeline_metrics       import get_pipeline_metrics, reset_pipeline_metrics
from .pipeline_registry      import reset_pipeline_registry

__all__ = [
    "DeadLetterEntry",
    "PipelineManager",
    "get_pipeline_manager",
    "reset_pipeline_manager",
]

_LOG     = logging.getLogger("iios.observation.pipeline.manager")
_lock    = threading.Lock()
_manager: Optional["PipelineManager"] = None


@dataclass
class DeadLetterEntry:
    """An observation that could not be processed after all retries."""
    obs_id:           str
    pipeline_name:    str
    rejection_reason: str
    stage_results:    list[dict[str, Any]]
    total_ms:         float

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":           self.obs_id,
            "pipeline_name":    self.pipeline_name,
            "rejection_reason": self.rejection_reason,
            "total_ms":         round(self.total_ms, 3),
        }


class PipelineManager:
    """
    Orchestrates the complete observation processing lifecycle.

    Usage::

        manager = get_pipeline_manager()
        result  = manager.process(obs)
        results = manager.process_batch(observations)
        health  = manager.health()
    """

    def __init__(
        self,
        engine:          Optional[PipelineEngine] = None,
        default_pipeline: str                     = PIPELINE_STANDARD,
        max_history:     int                      = MAX_PIPELINE_HISTORY,
    ) -> None:
        self._engine           = engine or get_pipeline_engine()
        self._default_pipeline = default_pipeline
        self._max_history      = max_history
        self._history:   list[PipelineExecutionResult] = []
        self._dead_letter: list[DeadLetterEntry]       = []
        self._total      = 0
        self._successful = 0
        self._failed     = 0
        self._lock       = threading.RLock()

    def process(
        self,
        obs:           Observation,
        pipeline_name: Optional[str] = None,
    ) -> PipelineExecutionResult:
        """Run obs through the pipeline; track result."""
        name   = pipeline_name or self._default_pipeline
        result = self._engine.execute(obs, name)
        self._record(result)
        if result.dead_lettered:
            self._add_dead_letter(result)
        return result

    def process_batch(
        self,
        observations:  list[Observation],
        pipeline_name: Optional[str] = None,
    ) -> list[PipelineExecutionResult]:
        """Run a batch of observations through the pipeline."""
        name    = pipeline_name or self._default_pipeline
        results = self._engine.execute_batch(observations, name)
        for r in results:
            self._record(r)
            if r.dead_lettered:
                self._add_dead_letter(r)
        return results

    def process_priority(
        self,
        observations:  list[Observation],
        pipeline_name: Optional[str] = None,
    ) -> list[PipelineExecutionResult]:
        name    = pipeline_name or self._default_pipeline
        results = self._engine.execute_priority(observations, name)
        for r in results:
            self._record(r)
        return results

    def health(self) -> dict[str, Any]:
        return self._engine.health()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":             self._total,
                "successful":        self._successful,
                "failed":            self._failed,
                "dead_letter_count": len(self._dead_letter),
                "success_rate":      round(self._successful / self._total, 4) if self._total else 0.0,
                "default_pipeline":  self._default_pipeline,
            }

    def history(self, limit: Optional[int] = None) -> list[PipelineExecutionResult]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def dead_letter_queue(self) -> list[DeadLetterEntry]:
        with self._lock:
            return list(self._dead_letter)

    def clear_dead_letter(self) -> int:
        with self._lock:
            n = len(self._dead_letter)
            self._dead_letter.clear()
            return n

    def engine(self) -> PipelineEngine:
        return self._engine

    # ── Internal ──────────────────────────────────────────────────────────────

    def _record(self, result: PipelineExecutionResult) -> None:
        with self._lock:
            self._total += 1
            if result.success:
                self._successful += 1
            else:
                self._failed += 1
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def _add_dead_letter(self, result: PipelineExecutionResult) -> None:
        entry = DeadLetterEntry(
            obs_id           = result.obs_id,
            pipeline_name    = result.pipeline_name,
            rejection_reason = result.rejection_reason,
            stage_results    = [r.to_dict() for r in result.stage_results],
            total_ms         = result.total_ms,
        )
        with self._lock:
            self._dead_letter.append(entry)
        _LOG.error(
            "DEAD LETTER | obs=%s | pipeline=%s | reason=%s",
            result.obs_id[:8], result.pipeline_name, result.rejection_reason,
        )


def get_pipeline_manager() -> PipelineManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = PipelineManager()
    return _manager


def reset_pipeline_manager() -> None:
    global _manager
    with _lock:
        _manager = None
    reset_pipeline_engine()
    reset_pipeline_monitor()
    reset_pipeline_metrics()
    reset_pipeline_registry()
