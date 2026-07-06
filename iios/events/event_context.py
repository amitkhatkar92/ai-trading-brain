"""
iios/events/event_context.py
================================
Thread-local event execution context for tracing, correlation, and ambient access.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .event_metadata import Event

__all__ = [
    "EventContext",
    "EventSpan",
    "current_event",
    "push_event",
    "pop_event",
    "event_scope",
    "get_event_context",
]

_local = threading.local()


def _stack() -> list[Event]:
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


def _spans() -> list["EventSpan"]:
    if not hasattr(_local, "spans"):
        _local.spans = []
    return _local.spans


def current_event() -> Optional[Event]:
    """Return the innermost active event on the current thread."""
    stack = _stack()
    return stack[-1] if stack else None


def push_event(event: Event) -> None:
    _stack().append(event)


def pop_event() -> Optional[Event]:
    stack = _stack()
    return stack.pop() if stack else None


@contextmanager
def event_scope(event: Event) -> Generator[Event, None, None]:
    """Make *event* the current event for the duration of the block."""
    push_event(event)
    try:
        yield event
    finally:
        pop_event()


@dataclass
class EventSpan:
    """Records duration of a single event handler execution."""
    handler_name: str
    event_type: str
    event_id: str
    started_at: float = field(default_factory=time.monotonic)
    finished_at: Optional[float] = None
    error: Optional[str] = None
    duration_ms: float = 0.0

    def finish(self, error: Optional[str] = None) -> None:
        self.finished_at = time.monotonic()
        self.duration_ms = (self.finished_at - self.started_at) * 1000
        self.error = error


class EventContext:
    """Ambient context for event execution — tracks spans and metrics."""

    def __init__(self) -> None:
        self._spans: list[EventSpan] = []
        self._lock = threading.Lock()
        self._total_dispatched = 0
        self._total_failed = 0

    @contextmanager
    def span(self, handler_name: str, event: Event) -> Generator[EventSpan, None, None]:
        s = EventSpan(
            handler_name=handler_name,
            event_type=event.event_type,
            event_id=event.event_id,
        )
        with self._lock:
            self._spans.append(s)
        try:
            yield s
            s.finish()
        except Exception as exc:
            s.finish(error=str(exc))
            with self._lock:
                self._total_failed += 1
            raise
        finally:
            with self._lock:
                self._total_dispatched += 1

    def spans(self, limit: int = 100) -> list[EventSpan]:
        with self._lock:
            return list(self._spans[-limit:])

    def stats(self) -> dict[str, Any]:
        with self._lock:
            recent = self._spans[-100:]
        durations = [s.duration_ms for s in recent if s.finished_at is not None]
        avg = sum(durations) / len(durations) if durations else 0.0
        return {
            "total_dispatched": self._total_dispatched,
            "total_failed": self._total_failed,
            "avg_handler_ms": avg,
            "recent_spans": len(recent),
        }

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
            self._total_dispatched = 0
            self._total_failed = 0


_global_ctx: Optional[EventContext] = None
_ctx_lock = threading.Lock()


def get_event_context() -> EventContext:
    global _global_ctx
    with _ctx_lock:
        if _global_ctx is None:
            _global_ctx = EventContext()
        return _global_ctx
