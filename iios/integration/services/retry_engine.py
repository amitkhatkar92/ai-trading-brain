"""
retry_engine.py — iios.integration.services
---------------------------------------------
RetryEngine — implements 5 retry back-off strategies for failed
integration requests.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_MS, FIBONACCI_DELAYS_MS, RetryStrategy

_log = get_logger(__name__)

ExecutorFn = Callable[[], Any]


@dataclass
class RetryConfig:
    """Configuration for a retry sequence."""
    max_attempts:     int           = DEFAULT_RETRY_COUNT
    delay_ms:         int           = DEFAULT_RETRY_DELAY_MS
    strategy:         RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_delay_ms:     int           = 60_000
    jitter_ms:        int           = 0      # not randomised in this simulation


@dataclass
class RetryAttempt:
    """Record of a single attempt."""
    attempt:    int
    success:    bool
    error:      str
    latency_ms: float
    delay_ms:   float   # time waited before this attempt


@dataclass
class RetryResult:
    """Result of a RetryEngine.execute() call."""
    success:  bool
    attempts: List[RetryAttempt]
    result:   Any               # return value from the last successful call
    error:    str               # last error if all failed

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)


class RetryEngine:
    """
    Retries a callable according to the configured back-off strategy.

    ``execute(fn)`` calls fn() up to max_attempts times, waiting between
    attempts according to the strategy. The first successful result is returned.
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self._cfg = config or RetryConfig()

    def execute(
        self,
        fn:     ExecutorFn,
        config: Optional[RetryConfig] = None,
    ) -> RetryResult:
        """
        Execute fn() with retries.

        Returns RetryResult. Caller must check .success.
        """
        cfg      = config or self._cfg
        attempts: List[RetryAttempt] = []
        result   = None
        error    = ""

        for attempt_no in range(1, cfg.max_attempts + 1):
            delay_ms = self._compute_delay(attempt_no, cfg)
            if attempt_no > 1:
                time.sleep(delay_ms / 1_000)

            start = time.perf_counter_ns()
            try:
                result     = fn()
                latency_ms = (time.perf_counter_ns() - start) / 1_000_000
                attempts.append(RetryAttempt(
                    attempt=attempt_no, success=True, error="",
                    latency_ms=latency_ms, delay_ms=delay_ms,
                ))
                return RetryResult(success=True, attempts=attempts, result=result, error="")
            except Exception as exc:
                latency_ms = (time.perf_counter_ns() - start) / 1_000_000
                error      = str(exc)
                attempts.append(RetryAttempt(
                    attempt=attempt_no, success=False, error=error,
                    latency_ms=latency_ms, delay_ms=delay_ms,
                ))
                _log.debug(f"retry-engine: attempt {attempt_no}/{cfg.max_attempts} failed — {error}")

        return RetryResult(success=False, attempts=attempts, result=None, error=error)

    # ── Internals ─────────────────────────────────────────────────────────

    def _compute_delay(self, attempt: int, cfg: RetryConfig) -> float:
        """Return the delay in milliseconds before attempt N (1-indexed)."""
        if attempt <= 1:
            return 0.0
        n = attempt - 2   # 0-indexed retry count
        if cfg.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        if cfg.strategy == RetryStrategy.FIXED_DELAY:
            delay = cfg.delay_ms
        elif cfg.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = cfg.delay_ms * (n + 1)
        elif cfg.strategy == RetryStrategy.FIBONACCI:
            idx   = min(n, len(FIBONACCI_DELAYS_MS) - 1)
            delay = FIBONACCI_DELAYS_MS[idx]
        else:  # EXPONENTIAL_BACKOFF (default)
            delay = cfg.delay_ms * (2 ** n)
        return float(min(delay, cfg.max_delay_ms))
