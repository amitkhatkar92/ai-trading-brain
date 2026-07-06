"""
iios/infrastructure/utilities/circuit_breaker.py
=================================================
Circuit breaker pattern with CLOSED / OPEN / HALF-OPEN states.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional, TypeVar

__all__ = ["CircuitBreaker", "CircuitBreakerOpen"]

F = TypeVar("F", bound=Callable[..., Any])

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted on an OPEN circuit."""


class CircuitBreaker:
    """Protects a callable against repeated failures.

    States:
        CLOSED    — normal operation; failures are counted
        OPEN      — rejects all calls for reset_timeout seconds
        HALF_OPEN — one probe call allowed; success closes, failure reopens

    Usage::

        cb = CircuitBreaker("dhan_api", threshold=5, reset_timeout=30)

        @cb
        def call_dhan():
            ...

        # or
        result = cb.call(my_fn, arg1, arg2)
    """

    def __init__(
        self,
        name: str = "default",
        threshold: int = 5,
        reset_timeout: float = 30.0,
    ) -> None:
        self._name = name
        self._threshold = threshold
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._last_failure_at: Optional[float] = None
        self._state = CLOSED
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        with self._lock:
            return self._current_state()

    def _current_state(self) -> str:
        """Internal — must be called under self._lock."""
        if self._state == OPEN:
            elapsed = time.monotonic() - (self._last_failure_at or 0)
            if elapsed >= self._reset_timeout:
                self._state = HALF_OPEN
        return self._state

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_at = time.monotonic()
        if self._failure_count >= self._threshold:
            self._state = OPEN

    # ------------------------------------------------------------------
    # Call interface
    # ------------------------------------------------------------------

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* through the circuit breaker."""
        with self._lock:
            state = self._current_state()
            if state == OPEN:
                raise CircuitBreakerOpen(
                    f"Circuit '{self._name}' is OPEN (threshold={self._threshold})"
                )

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception:
            with self._lock:
                self._on_failure()
            raise

    def __call__(self, fn: F) -> F:
        """Use as a decorator."""
        import functools

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(fn, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    @property
    def is_open(self) -> bool:
        return self.state == OPEN

    @property
    def is_closed(self) -> bool:
        return self.state == CLOSED

    @property
    def is_half_open(self) -> bool:
        return self.state == HALF_OPEN

    def reset(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._last_failure_at = None
            self._state = CLOSED
