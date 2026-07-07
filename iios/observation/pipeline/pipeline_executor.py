"""
iios/observation/pipeline/pipeline_executor.py
==============================================
Executes a ``PipelineDefinition`` against a single ``Observation``.

Features
--------
* Sequential stage execution
* Per-stage timeout enforcement via a separate thread
* Retry with fixed / linear / exponential backoff
* Failure policy handling (fail_fast, continue, quarantine, dead_letter)
* Conditional stage skipping
* Checkpoint writing at configured policy points
* Structured per-stage and total timing
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation import Observation
from ..observation_constants import ObservationStatus, SYSTEM_OBSERVER
from .pipeline_constants import (
    CheckpointPolicy, FailurePolicy, PipelineState, RetryBackoff,
    StageMode,
)
from .pipeline_context import PipelineContext, StageResult, pipeline_execution
from .pipeline_exceptions import (
    PipelineAbortedError, StageExecutionError, StageTimeoutError,
)
from .pipeline_registry import PipelineDefinition, StageDefinition

__all__ = [
    "PipelineExecutionResult",
    "PipelineExecutor",
]

_LOG = logging.getLogger("iios.observation.pipeline.executor")


@dataclass
class PipelineExecutionResult:
    """Full result of one pipeline run against one observation."""
    obs_id:           str
    pipeline_name:    str
    run_id:           str
    success:          bool
    final_status:     ObservationStatus
    stage_results:    list[StageResult]         = field(default_factory=list)
    rejection_reason: str                       = ""
    total_ms:         float                     = 0.0
    aborted:          bool                      = False
    dead_lettered:    bool                      = False
    context:          Optional[PipelineContext] = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":           self.obs_id,
            "pipeline_name":    self.pipeline_name,
            "run_id":           self.run_id,
            "success":          self.success,
            "final_status":     self.final_status.value,
            "stages_run":       len(self.stage_results),
            "stages_failed":    sum(1 for r in self.stage_results if not r.success and not r.skipped),
            "total_ms":         round(self.total_ms, 3),
            "aborted":          self.aborted,
            "dead_lettered":    self.dead_lettered,
            "rejection_reason": self.rejection_reason,
            "stages":           [r.to_dict() for r in self.stage_results],
        }

    @property
    def failed_stages(self) -> list[StageResult]:
        return [r for r in self.stage_results if not r.success and not r.skipped]


class PipelineExecutor:
    """Runs a PipelineDefinition's stages against an Observation."""

    def __init__(
        self,
        actor:               str   = SYSTEM_OBSERVER,
        default_timeout_ms:  float = 10_000.0,
    ) -> None:
        self._actor              = actor
        self._default_timeout_ms = default_timeout_ms
        # Single-threaded pool used for timeout enforcement
        self._timeout_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pip-timeout")

    def execute(
        self,
        obs:      Observation,
        pipeline: PipelineDefinition,
    ) -> PipelineExecutionResult:
        """Run all stages of *pipeline* against *obs* sequentially."""
        t_start = time.perf_counter()

        with pipeline_execution(obs.id, pipeline.name) as ctx:
            dead_lettered    = False
            rejection_reason = ""

            for stage_def in pipeline.stages:
                if ctx.state == PipelineState.ABORTED:
                    break

                stage_result = self._run_stage(obs, stage_def, ctx)
                ctx.record_stage(stage_result)

                # Write checkpoint if policy demands it
                if ctx.checkpoint_policy in (CheckpointPolicy.ALWAYS, CheckpointPolicy.PER_STAGE):
                    try:
                        ctx.checkpoint(stage_def.name, obs.to_dict())
                    except Exception as exc:
                        _LOG.debug("Checkpoint write failed at %r: %s", stage_def.name, exc)
                elif (
                    ctx.checkpoint_policy == CheckpointPolicy.ON_FAILURE
                    and not stage_result.success
                ):
                    try:
                        ctx.checkpoint(stage_def.name, obs.to_dict())
                    except Exception:
                        pass

                if not stage_result.success and not stage_result.skipped:
                    # Handle failure policy
                    policy = stage_def.failure_policy
                    if policy == FailurePolicy.FAIL_FAST:
                        rejection_reason = stage_result.error or f"stage {stage_def.name!r} failed"
                        ctx.abort()
                        break
                    elif policy == FailurePolicy.QUARANTINE:
                        rejection_reason = stage_result.error or f"quarantined at {stage_def.name!r}"
                        try:
                            if not obs.is_terminal:
                                obs.reject(rejection_reason, self._actor)
                        except Exception:
                            pass
                        ctx.abort()
                        break
                    elif policy == FailurePolicy.DEAD_LETTER:
                        rejection_reason = stage_result.error or f"dead-letter at {stage_def.name!r}"
                        dead_lettered = True
                        ctx.abort()
                        break
                    elif policy == FailurePolicy.ROLLBACK:
                        self._rollback(obs, ctx)
                        rejection_reason = stage_result.error or f"rollback at {stage_def.name!r}"
                        ctx.abort()
                        break
                    # FailurePolicy.CONTINUE → fall through

            # Capture aborted state BEFORE the CM calls ctx.complete()
            _aborted = ctx.state == PipelineState.ABORTED
            success  = not _aborted and ctx.all_stages_successful()
            total_ms = (time.perf_counter() - t_start) * 1_000.0
            final_status = obs.status

        return PipelineExecutionResult(
            obs_id           = obs.id,
            pipeline_name    = pipeline.name,
            run_id           = ctx.run_id,
            success          = success,
            final_status     = final_status,
            stage_results    = ctx.stage_results(),
            rejection_reason = rejection_reason,
            total_ms         = total_ms,
            aborted          = _aborted,
            dead_lettered    = dead_lettered,
            context          = ctx,
        )

    # ── Internal stage execution ──────────────────────────────────────────────

    def _run_stage(
        self,
        obs:      Observation,
        stage:    StageDefinition,
        ctx:      PipelineContext,
    ) -> StageResult:
        """Execute one stage, applying retry and timeout logic."""

        # Conditional mode: check condition first
        if stage.mode == StageMode.CONDITIONAL and stage.condition is not None:
            try:
                should_run = stage.condition(obs, ctx)
            except Exception as exc:
                _LOG.debug("Condition check for %r raised: %s", stage.name, exc)
                should_run = False
            if not should_run:
                return StageResult(stage_name=stage.name, success=True, skipped=True)

        timeout_s   = (stage.timeout_ms or self._default_timeout_ms) / 1_000.0
        retry_count = max(0, stage.retry_count)
        last_error  = ""

        for attempt in range(retry_count + 1):
            t0  = time.perf_counter()
            try:
                result = self._run_with_timeout(obs, stage, ctx, timeout_s)
                result.retries = attempt
                return result
            except StageTimeoutError as exc:
                last_error = str(exc)
                _LOG.warning("Stage %r timeout (attempt %d/%d)", stage.name, attempt + 1, retry_count + 1)
            except Exception as exc:
                last_error = str(exc)
                _LOG.debug("Stage %r error (attempt %d/%d): %s", stage.name, attempt + 1, retry_count + 1, exc)

            if attempt < retry_count:
                delay_s = self._backoff(stage, attempt)
                time.sleep(delay_s)

        # Exhausted all retries
        duration_ms = (time.perf_counter() - t0) * 1_000.0  # type: ignore[possibly-undefined]
        if stage.mode == StageMode.OPTIONAL:
            return StageResult(
                stage_name  = stage.name,
                success     = True,
                skipped     = True,
                duration_ms = duration_ms,
                error       = last_error,
            )
        return StageResult(
            stage_name  = stage.name,
            success     = False,
            duration_ms = duration_ms,
            retries     = retry_count,
            error       = last_error,
        )

    def _run_with_timeout(
        self,
        obs:       Observation,
        stage:     StageDefinition,
        ctx:       PipelineContext,
        timeout_s: float,
    ) -> StageResult:
        """Submit stage handler and wait. Propagates handler exceptions for retry."""
        future = self._timeout_pool.submit(stage.handler, obs, ctx)
        try:
            result = future.result(timeout=timeout_s)
        except FutureTimeout:
            raise StageTimeoutError(stage.name, timeout_ms=timeout_s * 1_000.0)
        # Other exceptions (from handler) propagate to _run_stage retry loop

        if result is None:
            return StageResult(stage_name=stage.name, success=True)
        return result

    @staticmethod
    def _backoff(stage: StageDefinition, attempt: int) -> float:
        base_s = stage.retry_delay_ms / 1_000.0
        if stage.retry_backoff == RetryBackoff.NONE:
            return 0.0
        if stage.retry_backoff == RetryBackoff.FIXED:
            return base_s
        if stage.retry_backoff == RetryBackoff.LINEAR:
            return base_s * (attempt + 1)
        if stage.retry_backoff == RetryBackoff.EXPONENTIAL:
            return base_s * (2 ** attempt)
        return base_s

    @staticmethod
    def _rollback(obs: Observation, ctx: PipelineContext) -> None:
        """Best-effort rollback: restore from last checkpoint if available."""
        cp = ctx.last_checkpoint()
        if cp is None:
            return
        # Restore observation status from checkpoint snapshot
        try:
            snapshot_status = cp.obs_snapshot.get("status")
            if snapshot_status and not obs.is_terminal:
                target = ObservationStatus(snapshot_status)
                obs.status = target
        except Exception as exc:
            _LOG.debug("Rollback restore failed: %s", exc)

    def shutdown(self) -> None:
        self._timeout_pool.shutdown(wait=False)
