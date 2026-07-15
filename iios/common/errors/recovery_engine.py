"""iios/common/errors/recovery_engine.py
Recovery strategies and execution engine for the IIOS platform.

Provides:
  • RecoveryStrategy enum — the six recovery modes
  • RecoveryResult         — immutable operation outcome
  • CircuitBreakerHook     — interface for circuit-breaker integration
  • DeadLetterHook         — interface for dead-letter-queue integration
  • RecoveryEngine         — executes operations with retry + fallback logic

Usage::

    from iios.common.errors.recovery_engine import RecoveryEngine, RecoveryStrategy
    from iios.common.errors.retry_policy import ExponentialBackoffWithJitter

    engine = RecoveryEngine(
        engine_id   = "iios:market:integration",
        retry_policy = ExponentialBackoffWithJitter(max_retries=3),
    )

    result = engine.execute(
        lambda: feed.get_multiple_quotes(symbols),
        operation = "get_multiple_quotes",
        fallback  = lambda: {},
    )
    if result.succeeded:
        use(result.value)
    else:
        handle_failure(result.error)
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from iios.common.errors.error_context import ErrorContext, get_error_context
from iios.common.errors.retry_policy import NoRetry, RetryPolicy


T = TypeVar("T")


# ── RecoveryStrategy ──────────────────────────────────────────────────────────

class RecoveryStrategy(str, Enum):
    """
    The recovery strategy that was applied or chosen for an operation.

    RETRY            — Re-execute the operation after a delay.
    FALLBACK         — Execute the fallback callable instead.
    SKIP_STAGE       — Skip the failing stage and continue the workflow.
    RESUME_WORKFLOW  — Resume the workflow from a checkpoint.
    ABORT_WORKFLOW   — Terminate the current workflow cleanly.
    SAFE_SHUTDOWN    — Initiate a graceful engine shutdown.
    """
    RETRY           = "retry"
    FALLBACK        = "fallback"
    SKIP_STAGE      = "skip_stage"
    RESUME_WORKFLOW = "resume_workflow"
    ABORT_WORKFLOW  = "abort_workflow"
    SAFE_SHUTDOWN   = "safe_shutdown"


# ── RecoveryResult ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RecoveryResult(Generic[T]):
    """
    Immutable outcome of executing an operation through the RecoveryEngine.

    Attributes
    ----------
    succeeded:  True if the operation (or fallback) returned successfully.
    strategy:   The recovery strategy that was applied.
    value:      The return value of the successful operation/fallback, or None.
    error:      The final exception if all recovery attempts failed, or None.
    attempts:   Total number of attempts (original + retries).
    elapsed_sec: Wall time spent across all attempts and delays.
    context:    Snapshot of error context at completion time.
    """
    succeeded:   bool
    strategy:    RecoveryStrategy
    value:       Optional[T]
    error:       Optional[BaseException]
    attempts:    int
    elapsed_sec: float
    context:     Dict[str, Any] = field(default_factory=dict)


# ── Hook interfaces ───────────────────────────────────────────────────────────

class CircuitBreakerHook(ABC):
    """
    Interface for circuit-breaker integration.

    Implementations wrap the execution to short-circuit when failure
    thresholds are exceeded, preventing cascade failures.

    Future distributed implementations can back this with Redis or etcd
    for cross-node circuit state.
    """

    @abstractmethod
    def allow_request(self, engine_id: str, operation: str) -> bool:
        """Return True if the request is allowed; False if circuit is open."""
        ...

    @abstractmethod
    def record_success(self, engine_id: str, operation: str) -> None:
        """Record a successful call (may close the circuit)."""
        ...

    @abstractmethod
    def record_failure(self, engine_id: str, operation: str) -> None:
        """Record a failed call (may open the circuit)."""
        ...


class DeadLetterHook(ABC):
    """
    Interface for dead-letter queue integration.

    Implementations capture failed operations that cannot be recovered
    for later replay, auditing, or manual intervention.

    Future distributed implementations can send to Kafka, SQS, or similar.
    """

    @abstractmethod
    def send(
        self,
        operation:  str,
        engine_id:  str,
        error:      BaseException,
        context:    Dict[str, Any],
    ) -> None:
        """
        Forward an irrecoverable failure to the dead-letter store.

        :param operation:  The name of the failed operation.
        :param engine_id:  The engine that failed.
        :param error:      The terminal exception.
        :param context:    Error context snapshot at time of failure.
        """
        ...


# ── No-op hooks (default) ─────────────────────────────────────────────────────

class _NoOpCircuitBreaker(CircuitBreakerHook):
    def allow_request(self, engine_id: str, operation: str) -> bool:   return True
    def record_success(self, engine_id: str, operation: str) -> None:  pass
    def record_failure(self, engine_id: str, operation: str) -> None:  pass


class _NoOpDeadLetter(DeadLetterHook):
    def send(self, operation, engine_id, error, context) -> None:      pass


# ── RecoveryEngine ────────────────────────────────────────────────────────────

class RecoveryEngine:
    """
    Executes operations with configurable retry + fallback logic.

    Thread-safe: each ``execute()`` call is independent.

    Dependency injection points:
    • ``retry_policy``     — swap policy at runtime or per-operation
    • ``circuit_breaker``  — plug in distributed circuit-breaker
    • ``dead_letter``      — plug in distributed dead-letter queue
    """

    def __init__(
        self,
        engine_id:       str                           = "",
        retry_policy:    Optional[RetryPolicy]         = None,
        circuit_breaker: Optional[CircuitBreakerHook]  = None,
        dead_letter:     Optional[DeadLetterHook]      = None,
        sleep_fn:        Callable[[float], None]       = time.sleep,
    ) -> None:
        self._engine_id:       str                  = engine_id
        self._retry_policy:    RetryPolicy          = retry_policy or NoRetry()
        self._circuit_breaker: CircuitBreakerHook   = circuit_breaker or _NoOpCircuitBreaker()
        self._dead_letter:     DeadLetterHook        = dead_letter or _NoOpDeadLetter()
        self._sleep_fn:        Callable[[float], None] = sleep_fn

    # ── Public API ────────────────────────────────────────────────────────────

    def execute(
        self,
        operation_fn:  Callable[[], T],
        *,
        operation:     str = "",
        fallback:      Optional[Callable[[], T]] = None,
        policy:        Optional[RetryPolicy] = None,
        context:       Optional[ErrorContext] = None,
    ) -> RecoveryResult[T]:
        """
        Execute *operation_fn* with retry and optional fallback.

        Retry policy precedence: ``policy`` arg > engine-level ``retry_policy``.

        :param operation_fn: The callable to execute.
        :param operation:    Human-readable name for logging.
        :param fallback:     Called if all retries exhausted (no exception raised).
        :param policy:       Per-call override of the retry policy.
        :param context:      Error context to enrich on failure.
        :returns:            RecoveryResult describing the outcome.
        """
        active_policy = policy or self._retry_policy
        effective_ctx = context or get_error_context()
        wall_start    = time.perf_counter()

        if not self._circuit_breaker.allow_request(self._engine_id, operation):
            err = RuntimeError(
                f"Circuit open for {self._engine_id}/{operation} — request denied"
            )
            elapsed = time.perf_counter() - wall_start
            return RecoveryResult(
                succeeded   = False,
                strategy    = RecoveryStrategy.ABORT_WORKFLOW,
                value       = None,
                error       = err,
                attempts    = 0,
                elapsed_sec = elapsed,
                context     = effective_ctx.to_dict() if effective_ctx else {},
            )

        attempt    = 0
        last_error: Optional[BaseException] = None

        while True:
            attempt += 1
            try:
                value = operation_fn()
                self._circuit_breaker.record_success(self._engine_id, operation)
                elapsed = time.perf_counter() - wall_start
                strategy = RecoveryStrategy.RETRY if attempt > 1 else RecoveryStrategy.FALLBACK
                return RecoveryResult(
                    succeeded   = True,
                    strategy    = strategy,
                    value       = value,
                    error       = None,
                    attempts    = attempt,
                    elapsed_sec = elapsed,
                    context     = effective_ctx.to_dict() if effective_ctx else {},
                )
            except BaseException as exc:
                last_error = exc
                self._circuit_breaker.record_failure(self._engine_id, operation)
                if effective_ctx:
                    effective_ctx.add_to_chain(exc)

                decision = active_policy.should_retry(attempt, exc)
                if decision.should_retry:
                    if decision.delay_sec > 0:
                        self._sleep_fn(decision.delay_sec)
                    continue
                break

        # All retries exhausted — try fallback
        if fallback is not None:
            try:
                fb_value = fallback()
                elapsed = time.perf_counter() - wall_start
                return RecoveryResult(
                    succeeded   = True,
                    strategy    = RecoveryStrategy.FALLBACK,
                    value       = fb_value,
                    error       = last_error,
                    attempts    = attempt,
                    elapsed_sec = elapsed,
                    context     = effective_ctx.to_dict() if effective_ctx else {},
                )
            except BaseException:
                pass  # fallback also failed — fall through to failure result

        # Report to dead-letter queue
        ctx_dict = effective_ctx.to_dict() if effective_ctx else {}
        self._dead_letter.send(
            operation = operation,
            engine_id = self._engine_id,
            error     = last_error,  # type: ignore[arg-type]
            context   = ctx_dict,
        )

        elapsed = time.perf_counter() - wall_start
        return RecoveryResult(
            succeeded   = False,
            strategy    = RecoveryStrategy.ABORT_WORKFLOW,
            value       = None,
            error       = last_error,
            attempts    = attempt,
            elapsed_sec = elapsed,
            context     = ctx_dict,
        )

    def execute_with_skip(
        self,
        operation_fn: Callable[[], T],
        *,
        operation:    str = "",
        default:      T,
        policy:       Optional[RetryPolicy] = None,
        context:      Optional[ErrorContext] = None,
    ) -> RecoveryResult[T]:
        """
        Execute *operation_fn*, returning *default* if all retries fail.

        Models the SKIP_STAGE recovery strategy: the stage is treated as
        optional and the workflow continues with a default/empty result.
        """
        result = self.execute(
            operation_fn,
            operation = operation,
            fallback  = lambda: default,
            policy    = policy,
            context   = context,
        )
        if result.succeeded and result.error is None:
            # Operation itself succeeded — return as-is (not a skip)
            return result
        # Operation failed, fallback (default) was used — this is a skip
        return RecoveryResult(
            succeeded   = True,
            strategy    = RecoveryStrategy.SKIP_STAGE,
            value       = default if (result.value is None or result.error is not None) else result.value,
            error       = result.error,
            attempts    = result.attempts,
            elapsed_sec = result.elapsed_sec,
            context     = result.context,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def engine_id(self) -> str:
        return self._engine_id

    def with_policy(self, policy: RetryPolicy) -> "RecoveryEngine":
        """Return a new RecoveryEngine with the given policy, sharing other state."""
        return RecoveryEngine(
            engine_id       = self._engine_id,
            retry_policy    = policy,
            circuit_breaker = self._circuit_breaker,
            dead_letter     = self._dead_letter,
            sleep_fn        = self._sleep_fn,
        )
