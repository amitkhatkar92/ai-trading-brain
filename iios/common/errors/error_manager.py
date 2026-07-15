"""iios/common/errors/error_manager.py
Central error handler registry and dispatcher for the IIOS platform.

Responsibilities:
  • Register per-exception-type handlers
  • Dispatch exceptions to the correct handler
  • Report failures to the audit logger and failure metrics
  • Provide RecoveryEngine instances per engine (DI factory)
  • Expose platform-wide failure statistics

Thread-safe via RLock.

Usage::

    from iios.common.errors.error_manager import ErrorManager, get_error_manager

    mgr = get_error_manager()

    # Register a handler for IntegrationError
    def on_integration_error(exc, ctx):
        notify_ops(exc)
    mgr.register_handler(IntegrationError, on_integration_error)

    # Dispatch
    try:
        risky_op()
    except IntegrationError as exc:
        mgr.dispatch(exc)

    # Get a pre-configured RecoveryEngine for an engine
    recovery = mgr.get_recovery_engine("iios:market:intelligence:integration")
    result = recovery.execute(lambda: feed.get_quotes(symbols))
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Tuple, Type

from iios.common.errors.error_context import ErrorContext, get_error_context
from iios.common.errors.exceptions import IIOSError
from iios.common.errors.failure_metrics import FailureTracker, get_failure_tracker
from iios.common.errors.recovery_engine import (
    CircuitBreakerHook,
    DeadLetterHook,
    RecoveryEngine,
)
from iios.common.errors.retry_policy import ExponentialBackoffWithJitter, RetryPolicy
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger


# ── Types ─────────────────────────────────────────────────────────────────────

# An error handler receives (exception, optional_context) and may return a
# replacement exception (for wrapping) or None (to suppress the exception —
# only safe when the caller explicitly handles None returns).
ErrorHandler = Callable[[BaseException, Optional[ErrorContext]], Optional[BaseException]]


# ── ErrorManager ─────────────────────────────────────────────────────────────

class ErrorManager:
    """
    Thread-safe central error handler registry and dispatcher.

    Handler lookup uses MRO order: the most specific registered type
    in the exception's MRO is used.
    """

    def __init__(
        self,
        failure_tracker: Optional[FailureTracker] = None,
        default_policy:  Optional[RetryPolicy]    = None,
        circuit_breaker: Optional[CircuitBreakerHook] = None,
        dead_letter:     Optional[DeadLetterHook]     = None,
    ) -> None:
        self._lock:            threading.RLock                          = threading.RLock()
        self._handlers:        Dict[Type[BaseException], List[ErrorHandler]] = {}
        self._recovery_cache:  Dict[str, RecoveryEngine]                = {}
        self._failure_tracker: FailureTracker                           = (
            failure_tracker or get_failure_tracker()
        )
        self._default_policy:  RetryPolicy = default_policy or ExponentialBackoffWithJitter(
            max_retries = 3,
            base_delay  = 0.5,
            max_delay   = 10.0,
        )
        self._circuit_breaker: Optional[CircuitBreakerHook] = circuit_breaker
        self._dead_letter:     Optional[DeadLetterHook]     = dead_letter
        self._log   = get_logger(__name__, engine_id="iios:error:manager", component="ErrorManager")
        self._audit = get_audit_logger(__name__, engine_id="iios:error:manager", component="ErrorManager")

    # ── Handler registration ──────────────────────────────────────────────────

    def register_handler(
        self,
        exc_type: Type[BaseException],
        handler:  ErrorHandler,
    ) -> None:
        """
        Register *handler* for exceptions of type *exc_type*.

        Multiple handlers can be registered for the same type; they are
        called in registration order.
        """
        with self._lock:
            if exc_type not in self._handlers:
                self._handlers[exc_type] = []
            self._handlers[exc_type].append(handler)

    def unregister_handlers(self, exc_type: Type[BaseException]) -> None:
        """Remove all handlers registered for *exc_type*."""
        with self._lock:
            self._handlers.pop(exc_type, None)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def dispatch(
        self,
        exc:     BaseException,
        context: Optional[ErrorContext] = None,
    ) -> None:
        """
        Dispatch *exc* to the most specific registered handler.

        Also records the failure in metrics and emits an audit record.
        If no handler is registered, the failure is recorded but no
        exception is raised by this method (the original exception
        propagates as normal — dispatch is advisory, not a barrier).

        :param exc:     The exception to dispatch.
        :param context: Optional explicit error context; falls back to
                        the current contextvars context.
        """
        effective_ctx = context or get_error_context()
        engine_id = (effective_ctx.engine_id if effective_ctx else "") or "unknown"

        # Record in metrics
        self._failure_tracker.record_failure(engine_id, type(exc))

        # Emit audit record
        try:
            self._audit.log_failure(
                engine_id,
                error_type = type(exc).__name__,
                message    = str(exc),
                exc        = exc,
            )
        except Exception:
            pass  # Never crash the dispatch loop

        # Find and call handlers
        handlers = self._find_handlers(type(exc))
        for handler in handlers:
            try:
                handler(exc, effective_ctx)
            except Exception as handler_exc:
                self._log.error(
                    f"Error handler raised an exception; ignoring: {handler_exc}",
                    exc=handler_exc,
                )

    def _find_handlers(
        self, exc_type: Type[BaseException]
    ) -> List[ErrorHandler]:
        """Return handlers for the most specific matching type via MRO lookup."""
        with self._lock:
            for cls in exc_type.__mro__:
                if cls in self._handlers:
                    return list(self._handlers[cls])
        return []

    # ── Recovery engine factory (DI) ──────────────────────────────────────────

    def get_recovery_engine(
        self,
        engine_id: str,
        *,
        policy: Optional[RetryPolicy] = None,
    ) -> RecoveryEngine:
        """
        Return (or create) a RecoveryEngine for *engine_id*.

        Cached per engine_id with the default policy.  Pass *policy* to
        create an uncached engine with a custom policy.
        """
        if policy is not None:
            return RecoveryEngine(
                engine_id       = engine_id,
                retry_policy    = policy,
                circuit_breaker = self._circuit_breaker,
                dead_letter     = self._dead_letter,
            )

        with self._lock:
            if engine_id not in self._recovery_cache:
                self._recovery_cache[engine_id] = RecoveryEngine(
                    engine_id       = engine_id,
                    retry_policy    = self._default_policy,
                    circuit_breaker = self._circuit_breaker,
                    dead_letter     = self._dead_letter,
                )
            return self._recovery_cache[engine_id]

    # ── Failure reporting ─────────────────────────────────────────────────────

    def report_failure(
        self,
        engine_id:  str,
        exc:        BaseException,
        context:    Optional[ErrorContext] = None,
        *,
        recovery_time_sec: float = 0.0,
        recovery_succeeded: bool = False,
    ) -> None:
        """
        Explicitly report a failure (and optional recovery outcome) to
        the metrics tracker.

        Use this when exceptions are handled at a higher level but you still
        want them captured in the failure metrics.
        """
        effective_ctx = context or get_error_context()
        self._failure_tracker.record_failure(engine_id, type(exc))
        if recovery_time_sec > 0:
            self._failure_tracker.record_recovery(
                engine_id,
                recovery_time_sec = recovery_time_sec,
                succeeded         = recovery_succeeded,
            )

    def report_retry(self, engine_id: str) -> None:
        """Record a retry attempt in the metrics tracker."""
        self._failure_tracker.record_retry(engine_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self):  # -> FailureMetricsSnapshot
        """Return a platform-wide failure metrics snapshot."""
        return self._failure_tracker.snapshot()

    def engine_statistics(self, engine_id: str):  # -> Optional[EngineMetricsSnapshot]
        """Return metrics snapshot for a single engine."""
        return self._failure_tracker.engine_snapshot(engine_id)

    # ── Reset (test isolation) ────────────────────────────────────────────────

    def reset(self) -> None:
        """
        Clear all registered handlers and recovery engine cache.

        Intended for test isolation only.
        """
        with self._lock:
            self._handlers.clear()
            self._recovery_cache.clear()
        self._failure_tracker.reset()


# ── Module-level singleton ────────────────────────────────────────────────────

_singleton_lock: threading.Lock               = threading.Lock()
_singleton:      Optional[ErrorManager]       = None


def get_error_manager() -> ErrorManager:
    """
    Return the platform-wide singleton ErrorManager.

    Thread-safe; creates on first call.
    """
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ErrorManager()
    return _singleton


def reset_error_manager() -> None:
    """
    Replace the singleton with a fresh instance.

    Intended for test isolation only — never call in production.
    """
    global _singleton
    with _singleton_lock:
        _singleton = ErrorManager()
