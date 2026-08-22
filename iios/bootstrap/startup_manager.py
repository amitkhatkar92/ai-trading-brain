"""
iios/bootstrap/startup_manager.py
====================================
Executes bootstrap stages in declaration order, enforcing dependency
constraints, timing SLAs, and retry semantics.

``StartupManager`` receives the ordered list of ``BootstrapStage`` objects
from ``BootstrapEngine`` and drives them to completion. It writes results
back into ``StartupContext`` after every stage.

Design:
  - Stages run sequentially (single-threaded by design)
  - Dependencies are checked before each stage — a stage is skipped if any
    dependency failed, unless the stage is marked optional
  - Each stage gets up to ``stage.max_retries`` attempts on failure
  - A stage that exceeds ``stage.timeout_seconds`` is still allowed to
    complete but gets a WARNING (hard-kill would require a thread, which
    we avoid in the bootstrap path)
  - Progress callbacks let the engine emit real-time status

Architecture Reference: IIOS-BSS-001 §3 Stage Execution Model
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .startup_context import StartupContext
from .startup_state import (
    BootstrapError,
    BootstrapStage,
    StageStatus,
    StartupStageResult,
)

__all__ = [
    "StartupManager",
    "StageProgressCallback",
    "StartupManagerConfig",
]

logger = logging.getLogger(__name__)

# Callback type: (stage_number, stage_name, status, elapsed_ms) → None
StageProgressCallback = Callable[[int, str, StageStatus, float], None]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class StartupManagerConfig:
    """Tuning parameters for the StartupManager."""

    abort_on_critical_failure: bool = True   # If False, continue past CRITICAL failures
    skip_optional_on_dep_failure: bool = True # Skip optional stages if deps failed
    max_retry_delay_seconds: float = 5.0     # Max back-off between retries
    retry_base_delay_seconds: float = 0.5    # Initial back-off delay
    log_stage_start: bool = True
    log_stage_complete: bool = True
    timing_warn_multiplier: float = 2.0      # Warn if stage takes >N× timeout


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class StartupManager:
    """Drives bootstrap stages through to completion.

    Typical usage::

        manager = StartupManager(context, stages)
        manager.add_progress_callback(my_callback)
        try:
            manager.run()
        except BootstrapError as exc:
            logger.critical("Bootstrap failed: %s", exc)
    """

    def __init__(
        self,
        context: StartupContext,
        stages: list[BootstrapStage],
        config: Optional[StartupManagerConfig] = None,
    ) -> None:
        self._ctx = context
        self._stages: dict[int, BootstrapStage] = {s.number: s for s in stages}
        self._ordered: list[BootstrapStage] = sorted(stages, key=lambda s: s.number)
        self._config = config or StartupManagerConfig()
        self._progress_callbacks: list[StageProgressCallback] = []
        self._completed: set[int] = set()
        self._failed: set[int] = set()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def add_progress_callback(self, callback: StageProgressCallback) -> None:
        """Register a callback invoked after each stage completes or fails."""
        self._progress_callbacks.append(callback)

    def run(self) -> None:
        """Execute all stages in order. Raises ``BootstrapError`` on critical failure."""
        logger.info(
            "StartupManager: running %d stages", len(self._ordered)
        )
        t_total = time.monotonic()

        for stage in self._ordered:
            self._run_stage(stage)

            # Check if we should abort
            if stage.number in self._failed:
                result = self._ctx.get_stage_result(stage.number)
                if result and result.error:
                    if not stage.optional and self._config.abort_on_critical_failure:
                        raise BootstrapError(
                            f"Critical stage {stage.number}:{stage.name} failed",
                            stage_number=stage.number,
                            stage_name=stage.name,
                            cause=result.error,
                        )

        total_ms = (time.monotonic() - t_total) * 1000.0
        logger.info(
            "StartupManager: all stages complete in %.1f ms (%d completed, %d failed)",
            total_ms,
            len(self._completed),
            len(self._failed),
        )

    def run_stage(self, stage_number: int) -> StartupStageResult:
        """Execute a single stage by number. Useful for targeted recovery."""
        stage = self._stages.get(stage_number)
        if stage is None:
            raise ValueError(f"Stage {stage_number} not registered")
        self._run_stage(stage)
        result = self._ctx.get_stage_result(stage_number)
        assert result is not None
        return result

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal execution
    # ─────────────────────────────────────────────────────────────────────────

    def _run_stage(self, stage: BootstrapStage) -> None:
        """Execute ``stage`` with retry and dependency logic."""
        # Check dependencies
        skip_reason = self._check_dependencies(stage)
        if skip_reason:
            result = StartupStageResult(
                stage_number=stage.number,
                stage_name=stage.name,
                status=StageStatus.SKIPPED,
            )
            result.mark_skipped(skip_reason)
            self._ctx.record_stage(result)
            self._notify_progress(stage, result)
            if not stage.optional:
                self._failed.add(stage.number)
                logger.warning(
                    "Stage %d:%s SKIPPED (non-optional): %s",
                    stage.number, stage.name, skip_reason,
                )
            else:
                logger.debug("Optional stage %d:%s skipped: %s", stage.number, stage.name, skip_reason)
            return

        # Execute with retries
        result = self._execute_with_retries(stage)
        self._ctx.record_stage(result)
        self._notify_progress(stage, result)

        if result.succeeded:
            self._completed.add(stage.number)
        else:
            self._failed.add(stage.number)

    def _check_dependencies(self, stage: BootstrapStage) -> str:
        """Return a non-empty skip reason if any dependency is not met."""
        for dep_num in stage.dependencies:
            dep_result = self._ctx.get_stage_result(dep_num)
            if dep_result is None:
                return f"dependency stage {dep_num} not yet run"
            if not dep_result.succeeded:
                dep_stage = self._stages.get(dep_num)
                dep_name = dep_stage.name if dep_stage else str(dep_num)
                if stage.optional or self._config.skip_optional_on_dep_failure:
                    return f"dependency {dep_num}:{dep_name} did not succeed"
                return f"required dependency {dep_num}:{dep_name} did not succeed"
        return ""

    def _execute_with_retries(self, stage: BootstrapStage) -> StartupStageResult:
        """Attempt to execute ``stage`` up to ``max_retries`` times."""
        max_attempts = stage.max_retries if stage.can_retry else 1
        last_result: Optional[StartupStageResult] = None

        for attempt in range(1, max_attempts + 1):
            result = StartupStageResult(
                stage_number=stage.number,
                stage_name=stage.name,
                status=StageStatus.RUNNING,
                attempt=attempt,
            )

            if self._config.log_stage_start:
                logger.info(
                    "Stage %d/%d  [%s]%s",
                    stage.number,
                    self._ctx.total_stages,
                    stage.name,
                    f" (attempt {attempt}/{max_attempts})" if attempt > 1 else "",
                )

            t0 = time.monotonic()
            try:
                stage.handler(self._ctx)
                result.mark_completed()
                elapsed = result.duration_ms

                if elapsed > stage.timeout_seconds * 1000 * self._config.timing_warn_multiplier:
                    logger.warning(
                        "Stage %d:%s exceeded timing threshold: %.1f ms (limit %.0f ms)",
                        stage.number, stage.name, elapsed, stage.timeout_seconds * 1000,
                    )

                if self._config.log_stage_complete:
                    logger.info(
                        "Stage %d:%s COMPLETED in %.1f ms",
                        stage.number, stage.name, elapsed,
                    )
                return result

            except Exception as exc:  # noqa: BLE001
                result.mark_failed(exc)
                elapsed = result.duration_ms
                logger.error(
                    "Stage %d:%s FAILED (attempt %d/%d) in %.1f ms: %s",
                    stage.number, stage.name, attempt, max_attempts, elapsed, exc,
                )
                last_result = result

                if attempt < max_attempts:
                    delay = min(
                        self._config.retry_base_delay_seconds * (2 ** (attempt - 1)),
                        self._config.max_retry_delay_seconds,
                    )
                    logger.info(
                        "Stage %d:%s retrying in %.1f s...",
                        stage.number, stage.name, delay,
                    )
                    time.sleep(delay)

        # All attempts exhausted
        assert last_result is not None
        return last_result

    def _notify_progress(
        self, stage: BootstrapStage, result: StartupStageResult
    ) -> None:
        for cb in self._progress_callbacks:
            try:
                cb(stage.number, stage.name, result.status, result.duration_ms)
            except Exception:  # noqa: BLE001
                logger.debug("Progress callback raised for stage %d", stage.number)
