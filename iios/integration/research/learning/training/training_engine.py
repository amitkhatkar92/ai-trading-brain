"""training/training_engine.py — Executes training jobs against BaseModel implementations."""
from __future__ import annotations

import inspect
import threading
import time
from typing import Any, Optional

from iios.integration.research.learning.learning_exceptions import (
    JobNotFoundError,
    JobStateError,
    TrainingError,
)
from iios.integration.research.learning.core.training_result import TrainingResult
from iios.integration.research.learning.training.training_job import TrainingJob


class TrainingEngine:
    """
    Executes TrainingJob records by delegating to a BaseModel's ``fit()`` method.

    Supports both sync and async ``fit()``.  The caller is responsible for
    providing the correct event loop context when calling ``run_job`` from an
    async context.

    Thread-safety: a single RLock guards the ``_running`` dict.
    """

    def __init__(self) -> None:
        self._running: dict[str, TrainingJob] = {}
        self._lock     = threading.RLock()
        self._total_run = 0
        self._total_failed = 0

    # ── Public ────────────────────────────────────────────────────────────────

    async def run_job(
        self,
        job:     TrainingJob,
        model:   Any,          # BaseModel (Any avoids Protocol import cycle)
        dataset: Any,          # TrainingDataset
    ) -> TrainingResult:
        """
        Execute a training job.

        1. Marks the job as RUNNING
        2. Calls ``model.fit(dataset, job.config)`` (async or sync)
        3. Wraps the returned metrics dict in a TrainingResult
        4. Marks the job COMPLETED (or FAILED on exception)
        """
        job_id = job.job_id

        with self._lock:
            if job_id in self._running:
                raise TrainingError(f"Job '{job_id}' is already running")
            self._running[job_id] = job

        t0 = time.time()
        try:
            job.start()

            fit_fn = getattr(model, "fit", None)
            if fit_fn is None:
                raise TrainingError(f"Model {model!r} has no fit() method")

            if inspect.iscoroutinefunction(fit_fn):
                metrics = await fit_fn(dataset, job.config)
            else:
                metrics = fit_fn(dataset, job.config)

            if not isinstance(metrics, dict):
                metrics = {}

            training_sec = time.time() - t0
            result = TrainingResult.create(
                job_id        = job_id,
                model_id      = job.model_id,
                model_version = getattr(model, "version", "1.0.0"),
                metrics       = {k: float(v) for k, v in metrics.items()
                                 if isinstance(v, (int, float))},
                training_sec  = training_sec,
            )
            job.complete(result.result_id)
            with self._lock:
                self._total_run += 1
            return result

        except Exception as exc:
            job.fail(str(exc))
            with self._lock:
                self._total_failed += 1
            raise TrainingError(f"Job '{job_id}' failed: {exc}") from exc
        finally:
            with self._lock:
                self._running.pop(job_id, None)

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_running(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._running

    def running_jobs(self) -> list[TrainingJob]:
        with self._lock:
            return list(self._running.values())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "currently_running": len(self._running),
                "total_run":         self._total_run,
                "total_failed":      self._total_failed,
            }
