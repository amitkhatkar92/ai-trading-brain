"""
timeout_engine.py — iios.integration.services
-----------------------------------------------
TimeoutEngine — enforces per-request time budgets for integration calls.

Runs callables in a daemon thread and joins with a timeout. Thread-safe.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_TIMEOUT_MS

_log = get_logger(__name__)

ExecutorFn = Callable[[], Any]


@dataclass
class TimeoutResult:
    """Result of a timeout-guarded execution."""
    success:     bool
    timed_out:   bool
    result:      Any
    latency_ms:  float
    error:       str = ""


class TimeoutEngine:
    """
    Wraps callable execution in a timeout budget.

    Uses a daemon thread so the main thread is never blocked indefinitely.
    If the callable does not complete within timeout_ms, the result is a
    timed-out TimeoutResult.
    """

    def __init__(self, default_timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        self._default_timeout_ms = default_timeout_ms
        self._lock   = threading.Lock()
        self._timed_out   = 0
        self._successful  = 0
        self._failed      = 0

    # ── Public ───────────────────────────────────────────────────────────

    def execute(
        self,
        fn:         ExecutorFn,
        timeout_ms: Optional[int] = None,
    ) -> TimeoutResult:
        """
        Execute fn() within timeout_ms. If timeout elapses, return a timed-out
        result. Exceptions from fn() are caught and returned as error results.
        """
        budget_ms   = timeout_ms if timeout_ms is not None else self._default_timeout_ms
        budget_s    = budget_ms / 1_000.0
        result_box: Dict[str, Any] = {}
        error_box:  Dict[str, Any] = {}

        def worker() -> None:
            try:
                result_box["value"] = fn()
            except Exception as exc:
                error_box["error"] = str(exc)

        start  = time.perf_counter_ns()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=budget_s)
        latency_ms = (time.perf_counter_ns() - start) / 1_000_000

        if thread.is_alive():
            # Thread still running — timeout exceeded
            with self._lock:
                self._timed_out += 1
            _log.debug(
                f"timeout-engine: timed out after {budget_ms} ms"
            )
            return TimeoutResult(
                success=False, timed_out=True, result=None,
                latency_ms=latency_ms,
                error=f"Execution timed out after {budget_ms} ms",
            )

        if error_box:
            with self._lock:
                self._failed += 1
            return TimeoutResult(
                success=False, timed_out=False, result=None,
                latency_ms=latency_ms, error=error_box["error"],
            )

        with self._lock:
            self._successful += 1
        return TimeoutResult(
            success=True, timed_out=False,
            result=result_box.get("value"),
            latency_ms=latency_ms,
        )

    # ── Stats ─────────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "successful": self._successful,
                "failed":     self._failed,
                "timed_out":  self._timed_out,
            }
