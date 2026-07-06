"""
iios/monitoring/trace_manager.py
==================================
Distributed tracing for IIOS request lifecycles.

Supports:
  - Trace creation with a unique trace_id
  - Child span creation (parent-child relationships)
  - Automatic timing of spans via context manager
  - Thread-local active span propagation
  - In-memory trace store with retention

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .monitoring_models import TraceContext, TraceSpan
from .monitoring_constants import (
    DEFAULT_TRACE_RETENTION_SECONDS,
    MAX_TRACE_SPANS,
    TraceStatus,
)

__all__ = [
    "TraceManager",
    "get_trace_manager",
    "current_trace",
    "current_span",
]

_thread_local = threading.local()
_instance_lock = threading.Lock()
_instance: Optional["TraceManager"] = None


def current_trace() -> Optional[TraceContext]:
    """Return the active ``TraceContext`` for the current thread."""
    return getattr(_thread_local, "trace", None)


def current_span() -> Optional[TraceSpan]:
    """Return the active ``TraceSpan`` for the current thread."""
    return getattr(_thread_local, "span", None)


class TraceManager:
    """Manages distributed traces across IIOS subsystems.

    Usage::

        tm = get_trace_manager()
        with tm.trace("cycle.full") as trace:
            with tm.span("GlobalIntelligence.fetch", layer="GlobalIntelligence"):
                ...
            with tm.span("MarketIntelligence.scan", layer="MarketIntelligence"):
                ...
        print(trace.duration_ms)
    """

    def __init__(
        self,
        retention_seconds: int = DEFAULT_TRACE_RETENTION_SECONDS,
        max_spans: int = MAX_TRACE_SPANS,
    ) -> None:
        self._lock = threading.Lock()
        self._traces: deque[TraceContext] = deque(maxlen=1000)
        self._active: dict[str, TraceContext] = {}   # trace_id → context
        self._retention = retention_seconds
        self._max_spans = max_spans
        self._trace_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @contextmanager
    def trace(
        self,
        operation: str,
        trace_id: Optional[str] = None,
        **metadata: Any,
    ) -> Generator[TraceContext, None, None]:
        """Create and activate a trace for the duration of the block.

        Args:
            operation:  Descriptive name for the traced operation.
            trace_id:   Optional explicit trace ID (auto-generated if None).
            **metadata: Arbitrary metadata stored on the trace.

        Yields:
            ``TraceContext`` with a unique ``trace_id``.
        """
        ctx = TraceContext(
            operation=operation,
            metadata=metadata,
        )
        if trace_id:
            ctx.trace_id = trace_id

        prev_trace = getattr(_thread_local, "trace", None)
        _thread_local.trace = ctx

        with self._lock:
            self._active[ctx.trace_id] = ctx
            self._trace_count += 1

        error: Optional[str] = None
        try:
            yield ctx
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ctx.finish(error)
            with self._lock:
                self._active.pop(ctx.trace_id, None)
                self._traces.append(ctx)

            if prev_trace is not None:
                _thread_local.trace = prev_trace
            else:
                if hasattr(_thread_local, "trace"):
                    del _thread_local.trace

    @contextmanager
    def span(
        self,
        operation: str,
        component: str = "",
        layer: str = "",
        parent_span_id: Optional[str] = None,
        **tags: str,
    ) -> Generator[TraceSpan, None, None]:
        """Create a child span within the active trace.

        If no trace is active, this is a no-op (span is created but
        not attached to any trace).

        Args:
            operation:     Span operation name.
            component:     IIOS component.
            layer:         IIOS layer.
            parent_span_id: Explicit parent. Defaults to current active span.
            **tags:        String tags attached to the span.
        """
        trace = current_trace()
        prev_span = current_span()

        # Determine parent
        p_id = parent_span_id or (prev_span.span_id if prev_span else None)

        span = TraceSpan(
            operation=operation,
            trace_id=trace.trace_id if trace else "no-trace",
            parent_span_id=p_id,
            component=component,
            layer=layer,
            tags=dict(tags),
        )

        _thread_local.span = span

        error: Optional[str] = None
        try:
            yield span
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            span.finish(error)
            if trace and len(trace.spans) < self._max_spans:
                trace.spans.append(span)
            # Restore previous span
            if prev_span is not None:
                _thread_local.span = prev_span
            else:
                if hasattr(_thread_local, "span"):
                    del _thread_local.span

    def create_trace(self, operation: str, **metadata: Any) -> TraceContext:
        """Create a trace manually (without context manager)."""
        ctx = TraceContext(operation=operation, metadata=metadata)
        with self._lock:
            self._active[ctx.trace_id] = ctx
            self._trace_count += 1
        return ctx

    def finish_trace(self, trace: TraceContext, error: Optional[str] = None) -> None:
        """Finish a manually created trace."""
        trace.finish(error)
        with self._lock:
            self._active.pop(trace.trace_id, None)
            self._traces.append(trace)

    def create_span(
        self,
        operation: str,
        trace_id: str = "",
        parent_span_id: Optional[str] = None,
        component: str = "",
        layer: str = "",
    ) -> TraceSpan:
        """Create a span manually."""
        return TraceSpan(
            operation=operation,
            trace_id=trace_id or "no-trace",
            parent_span_id=parent_span_id,
            component=component,
            layer=layer,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent_traces(self, n: int = 20) -> list[TraceContext]:
        """Return up to *n* most recent completed traces."""
        with self._lock:
            return list(reversed(list(self._traces)))[:n]

    def active_traces(self) -> list[TraceContext]:
        """Return all currently running traces."""
        with self._lock:
            return list(self._active.values())

    def find_trace(self, trace_id: str) -> Optional[TraceContext]:
        """Find a trace by ID (searches both active and recent)."""
        with self._lock:
            if trace_id in self._active:
                return self._active[trace_id]
            for t in reversed(list(self._traces)):
                if t.trace_id == trace_id:
                    return t
        return None

    def slow_traces(self, threshold_ms: float = 1000.0, n: int = 20) -> list[TraceContext]:
        """Return traces where total duration exceeded *threshold_ms*."""
        with self._lock:
            traces = [
                t for t in self._traces
                if t.duration_ms is not None and t.duration_ms >= threshold_ms
            ]
        return sorted(traces, key=lambda t: t.duration_ms or 0, reverse=True)[:n]

    @property
    def trace_count(self) -> int:
        return self._trace_count

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


def get_trace_manager() -> TraceManager:
    """Return (or create) the global ``TraceManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = TraceManager()
        return _instance


def _reset_trace_manager() -> None:
    global _instance
    with _instance_lock:
        _instance = None
