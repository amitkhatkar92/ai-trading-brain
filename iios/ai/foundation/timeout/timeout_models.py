"""
timeout_models.py -- iios.ai.foundation.timeout
================================================
TimeoutPolicy, ExecutionDeadline, TimeoutController.

Provider-independent timeout management.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

SCHEMA_VER = "1.0"


# ---------------------------------------------------------------------------
# TimeoutPolicy -- immutable configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeoutPolicy:
    """
    Immutable timeout configuration for one operation type.

    Fields
    ------
    request_timeout_s :  Hard wall-clock timeout for a single provider request.
    provider_timeout_s : Timeout applied at the provider adapter level.
    session_timeout_s :  Session-level TTL (0 = no session timeout).
    pipeline_timeout_s : Total timeout for the entire pipeline execution.
    """
    request_timeout_s:  float = 30.0
    provider_timeout_s: float = 25.0
    session_timeout_s:  float = 0.0
    pipeline_timeout_s: float = 60.0
    schema:             str   = SCHEMA_VER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_timeout_s":  self.request_timeout_s,
            "provider_timeout_s": self.provider_timeout_s,
            "session_timeout_s":  self.session_timeout_s,
            "pipeline_timeout_s": self.pipeline_timeout_s,
        }

    @classmethod
    def default(cls) -> "TimeoutPolicy":
        return cls()

    @classmethod
    def fast(cls) -> "TimeoutPolicy":
        """Tight timeouts for latency-sensitive paths."""
        return cls(
            request_timeout_s  = 10.0,
            provider_timeout_s =  8.0,
            pipeline_timeout_s = 15.0,
        )

    @classmethod
    def relaxed(cls) -> "TimeoutPolicy":
        """Generous timeouts for background / batch operations."""
        return cls(
            request_timeout_s  = 120.0,
            provider_timeout_s = 100.0,
            pipeline_timeout_s = 180.0,
        )


# ---------------------------------------------------------------------------
# ExecutionDeadline -- tracks a single operation's deadline
# ---------------------------------------------------------------------------

class ExecutionDeadline:
    """
    Tracks a single operation's wall-clock deadline.

    Usage::

        deadline = ExecutionDeadline.from_timeout(30.0)
        # ... do work ...
        if deadline.is_exceeded():
            raise TimeoutError
        remaining = deadline.remaining_s()
    """

    def __init__(self, deadline_at: float) -> None:
        self._deadline_at = deadline_at

    @classmethod
    def from_timeout(cls, timeout_s: float) -> "ExecutionDeadline":
        """Create a deadline ``timeout_s`` seconds from now."""
        return cls(time.monotonic() + timeout_s)

    @classmethod
    def no_deadline(cls) -> "ExecutionDeadline":
        """Create a deadline that never expires."""
        return cls(float("inf"))

    def is_exceeded(self) -> bool:
        return time.monotonic() >= self._deadline_at

    def remaining_s(self) -> float:
        """Remaining seconds until deadline (0.0 if already exceeded)."""
        return max(0.0, self._deadline_at - time.monotonic())

    def elapsed_s(self) -> float:
        """Seconds elapsed since deadline was created (always positive)."""
        return max(0.0, time.monotonic() - (self._deadline_at - self.remaining_s()))

    def assert_not_exceeded(self, label: str = "operation") -> None:
        """Raise ``TimeoutError`` if the deadline is exceeded."""
        if self.is_exceeded():
            raise TimeoutError(
                f"{label} deadline exceeded "
                f"(deadline_at={self._deadline_at:.3f}, now={time.monotonic():.3f})"
            )


# ---------------------------------------------------------------------------
# TimeoutController
# ---------------------------------------------------------------------------

class TimeoutController:
    """
    Manages timeouts for an operation using a background thread.

    On timeout, calls the provided ``on_timeout`` callback on a
    dedicated thread -- does NOT raise directly into the calling thread.
    The caller is responsible for checking :meth:`is_timed_out`.

    Usage::

        ctrl = TimeoutController(timeout_s=5.0, on_timeout=my_callback)
        ctrl.start()
        # ... do work ...
        ctrl.stop()   # cancel if completed in time
        if ctrl.is_timed_out():
            # handle timeout
    """

    def __init__(
        self,
        timeout_s:  float,
        on_timeout: Optional[Callable[[], None]] = None,
    ) -> None:
        self._timeout_s   = timeout_s
        self._on_timeout  = on_timeout
        self._timed_out   = threading.Event()
        self._cancelled   = threading.Event()
        self._thread:     Optional[threading.Thread] = None
        self._started_at: Optional[float]            = None

    def start(self) -> None:
        """Start the timeout countdown."""
        self._started_at = time.monotonic()
        self._thread = threading.Thread(
            target  = self._run,
            daemon  = True,
            name    = f"timeout-{id(self)}",
        )
        self._thread.start()

    def stop(self) -> None:
        """Cancel the timeout (operation completed before deadline)."""
        self._cancelled.set()
        if self._thread:
            self._thread.join(timeout=0.1)

    def is_timed_out(self) -> bool:
        return self._timed_out.is_set()

    def elapsed_s(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.monotonic() - self._started_at

    def _run(self) -> None:
        fired = self._cancelled.wait(timeout=self._timeout_s)
        if not fired:
            self._timed_out.set()
            if self._on_timeout:
                try:
                    self._on_timeout()
                except Exception:
                    pass
