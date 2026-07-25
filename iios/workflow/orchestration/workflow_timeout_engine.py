"""
workflow_timeout_engine.py — iios.workflow.orchestration
---------------------------------------------------------
WorkflowTimeoutEngine — enforces per-step timeout limits by running
steps in daemon threads and joining with a timeout.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowTimeoutError
from .workflow_step import StepResult, WorkflowStep

_log = get_logger(__name__)


class WorkflowTimeoutEngine:
    """
    Enforces per-step timeouts using daemon threads.

    When `timeout_seconds > 0`, the callable runs in a background
    thread and the engine waits at most `timeout_seconds` for it to
    complete.  If the thread does not complete in time, a StepResult
    with TIMED_OUT status is returned (the background thread is left
    to finish naturally as a daemon).

    Thread-safe — stateless.
    """

    def execute_with_timeout(
        self,
        step:             WorkflowStep,
        execute:          Callable[[], StepResult],
        timeout_seconds:  float,
    ) -> StepResult:
        """
        Execute `execute()` with a hard time limit.

        If timeout_seconds <= 0, the callable is executed directly
        (no timeout enforcement).

        Returns:
            StepResult — either the step's own result or a TIMED_OUT result.
        """
        if timeout_seconds <= 0:
            return execute()

        result_box: list = [None]
        error_box:  list = [None]
        t0 = time.monotonic()

        def _run() -> None:
            try:
                result_box[0] = execute()
            except Exception as exc:
                error_box[0] = exc

        thread = threading.Thread(target=_run, daemon=True, name=f"wf-step-{step.step_id}")
        thread.start()
        thread.join(timeout=timeout_seconds)

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        if thread.is_alive():
            _log.warning(
                f"TimeoutEngine: step={step.step_id!r} "
                f"timed out after {timeout_seconds:.1f}s"
            )
            return StepResult.timed_out(step, elapsed_ms)

        if error_box[0] is not None:
            raise error_box[0]   # re-raise in calling thread

        return result_box[0]     # type: ignore[return-value]
