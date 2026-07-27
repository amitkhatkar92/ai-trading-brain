"""
observability.py -- iios.ai.foundation.observability
======================================================
Structured logging and observability utilities for the AI Platform.

Provides:
* CorrelationContext -- correlation/request/session ID tracking
* StructuredLogger   -- structured log entries
* ExecutionTimer     -- high-resolution timing context manager

No external monitoring integration.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import contextlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, Optional

from iios.common.logging.logging_manager import get_logger


# ---------------------------------------------------------------------------
# Correlation context
# ---------------------------------------------------------------------------

@dataclass
class CorrelationContext:
    """
    Carries correlation identifiers through one AI operation.

    Attach to every structured log entry for end-to-end traceability.

    Fields
    ------
    trace_id :    Top-level distributed trace ID (usually from the caller).
    request_id :  AI request ID.
    session_id :  AI session ID.
    module_id :   Current AI module.
    span_id :     Local span ID within this operation.
    """
    trace_id:   str
    request_id: str
    session_id: str
    module_id:  str
    span_id:    str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @classmethod
    def create(
        cls,
        module_id:  str,
        session_id: str,
        request_id: str = "",
        trace_id:   str = "",
    ) -> "CorrelationContext":
        return cls(
            trace_id   = trace_id   or str(uuid.uuid4()),
            request_id = request_id or str(uuid.uuid4()),
            session_id = session_id,
            module_id  = module_id,
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "trace_id":   self.trace_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "module_id":  self.module_id,
            "span_id":    self.span_id,
        }

    def child_span(self) -> "CorrelationContext":
        """Create a child span with a new span_id."""
        return CorrelationContext(
            trace_id   = self.trace_id,
            request_id = self.request_id,
            session_id = self.session_id,
            module_id  = self.module_id,
        )


# ---------------------------------------------------------------------------
# Structured log entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StructuredLogEntry:
    """An immutable structured log record."""
    level:          str
    message:        str
    correlation:    CorrelationContext
    timestamp:      float
    duration_ms:    Optional[float]
    provider_id:    str
    extra:          Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level":       self.level,
            "message":     self.message,
            "timestamp":   self.timestamp,
            "duration_ms": self.duration_ms,
            "provider_id": self.provider_id,
            **self.correlation.to_dict(),
            **self.extra,
        }


class StructuredLogger:
    """
    Structured logger that enriches log entries with correlation context.

    Wraps the standard ``iios.common.logging`` logger.

    Parameters
    ----------
    module_name : Python module name (passed to ``get_logger``).
    """

    def __init__(self, module_name: str) -> None:
        self._log    = get_logger(module_name)
        self._module = module_name

    def info(
        self,
        message:     str,
        correlation: Optional[CorrelationContext] = None,
        **extra: Any,
    ) -> None:
        prefix = self._prefix(correlation)
        self._log.info(f"{prefix}{message}")

    def debug(
        self,
        message:     str,
        correlation: Optional[CorrelationContext] = None,
        **extra: Any,
    ) -> None:
        prefix = self._prefix(correlation)
        self._log.debug(f"{prefix}{message}")

    def warning(
        self,
        message:     str,
        correlation: Optional[CorrelationContext] = None,
        **extra: Any,
    ) -> None:
        prefix = self._prefix(correlation)
        self._log.warning(f"{prefix}{message}")

    def error(
        self,
        message:     str,
        correlation: Optional[CorrelationContext] = None,
        **extra: Any,
    ) -> None:
        prefix = self._prefix(correlation)
        self._log.error(f"{prefix}{message}")

    def _prefix(self, ctx: Optional[CorrelationContext]) -> str:
        if ctx is None:
            return ""
        return (
            f"[trace={ctx.trace_id[:8]} "
            f"req={ctx.request_id[:8]} "
            f"ses={ctx.session_id[:8]}] "
        )


# ---------------------------------------------------------------------------
# Execution timer
# ---------------------------------------------------------------------------

@dataclass
class TimingResult:
    """Result produced by :class:`ExecutionTimer`."""
    name:       str
    elapsed_ms: float
    succeeded:  bool
    error:      str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":       self.name,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "succeeded":  self.succeeded,
            "error":      self.error,
        }


class ExecutionTimer:
    """
    Context manager for high-resolution timing.

    Usage::

        timer = ExecutionTimer("provider.complete")
        with timer.measure() as t:
            response = provider.complete(request)
        print(t.elapsed_ms)
    """

    def __init__(self, name: str) -> None:
        self._name  = name
        self._result: Optional[TimingResult] = None

    @property
    def result(self) -> Optional[TimingResult]:
        return self._result

    @contextlib.contextmanager
    def measure(self) -> Generator["TimingResult", None, None]:
        """Yield a :class:`TimingResult` that is populated on exit."""
        result = TimingResult(name=self._name, elapsed_ms=0.0, succeeded=False)
        self._result = result
        start = time.perf_counter()
        try:
            yield result
            result.succeeded = True
        except Exception as exc:
            result.succeeded = False
            result.error     = str(exc)
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            # Update the dataclass in place (not frozen)
            result.elapsed_ms = elapsed
